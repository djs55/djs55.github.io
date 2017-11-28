---
layout: post
title:  "Docker for Mac: reducing disk space"
date:   2017-11-27 08:56:56 -0600
categories: jekyll update
---

[Docker for Mac](https://www.docker.com/docker-mac) is a desktop app which allows building, testing and
running Dockerized apps on the Mac. Linux container images run inside a VM using a custom hypervisor called
[hyperkit](https://github.com/moby/hyperkit) -- part of the
[Moby open-source project](https://mobyproject.org). The VM boots from an
.iso and has a
single writable disk image stored on the Mac's filesystem in the
`~/Library/Containers/com.docker.docker/Data/com.docker.driver.amd64-linux`
directory. The filename is either
`Docker.qcow2` or `Docker.raw`, depending on the format.
Over time this file can grow and become large. This post explains
- what's in the `Docker.raw` (or `Docker.qcow2`);
- why it grows (often unexpectedly); and
- how to shrink it again.

# What's in the Docker.raw (or Docker.qcow)?

If a container creates or writes to a file then the effect depends on the path, for example:

- If the path is on a `tmpfs` filesystem, the file is created in memory..
- If the path is on a volume mapped from the host or from a remote server (via e.g. `docker run -v` or
  `docker run --mount`) then the `open`/`read`/`write`/... calls are forwarded and the file is accessed
  remotely.
- If the path is none of the above, then the operation is performed by the `overlay` filesystem, on
  top of an `ext4` filesystem on top of the partition `/dev/sda1`.
  The device `/dev/sda` is a (virtual)
[AHCI](https://en.wikipedia.org/wiki/Advanced_Host_Controller_Interface) device, whose code is in the
[hyperkit ahci-hd driver](https://github.com/moby/hyperkit/blob/81fa6279fcb17e8435f3cec0978e9aa3af02e63b/src/lib/pci_ahci.c).
The hyperkit command-line has an entry
`-s 4,ahci-hd,/.../Docker.raw`
which configures hyperkit to emulate an AHCI disk device such that when the VM writes to sector `x` on the device,
the data will be written to byte offset `x * 512` in the file `Docker.raw` where `512` is the
hard-coded sector size of the virtual disk device.

So the `Docker.raw` (or `Docker.qcow2`) contain image and container data, written by the Linux
`ext4` and `overlay` filesystems.

# Why does the file keep growing?

If Docker is used regularly, the size of the `Docker.raw` (or `Docker.qcow2`) can keep growing,
even when files are deleted.

To demonstrate the effect, first check the *current* size of the file on the host: 
{% highlight raw %}
$ cd ~/Library/Containers/com.docker.docker/Data/com.docker.driver.amd64-linux/
$ ls -s Docker.raw
9964528 Docker.raw
{% endhighlight %}
Note the use of `-s` which displays the number of filesystem blocks actually used by the file. The
number of blocks used is not necessarily the same as the file "size", as the file can be
[sparse](https://en.wikipedia.org/wiki/Sparse_file).

Next start a container in a separate terminal and create a 1GiB file in it:
{% highlight raw %}
$ docker run -it alpine sh
# and then inside the container:
/ # dd if=/dev/zero of=1GiB bs=1048576 count=1024
1024+0 records in
1024+0 records out
/ # sync
{% endhighlight %}

Back on the host check the file size again:
{% highlight raw %}
$ ls -s Docker.raw 
12061704 Docker.raw
{% endhighlight %}

Note the increase in size from `9964528` to `12061704`, where the increase of `2097176` `512`-byte sectors
is approximately 1GiB, as expected. If you switch back to the `alpine` container terminal and delete the file:
{% highlight raw %}
/ # rm -f 1GiB
/ # sync
{% endhighlight %}

then check the file on the host:
{% highlight raw %}
$ ls -s Docker.raw 
12059672 Docker.raw
{% endhighlight %}

The file has not got any smaller! Whatever has happened to the file inside the VM, the host doesn't seem to
know about it.

Next if you re-create the "same" `1GiB` file in the container again and then check the size again you will see:
{% highlight raw %}
$ ls -s Docker.raw 
14109456 Docker.raw
{% endhighlight %}

It's got even bigger! It seems that if you create and destroy files in a loop, the size of the `Docker.raw`
(or `Docker.qcow2`) will increase up to the upper limit (currently set to 64 GiB), even if the filesystem
inside the VM is relatively empty.

The explanation for this odd behaviour lies with how filesystems typically manage blocks. When a file is
to be created or extended, the filesystem will find a free block and add it to the file. When a file is
removed, the blocks become "free" from the filesystem's point of view, but no-one tells the disk device.
Making matters worse, the newly-freed blocks might not be re-used straight away -- it's completely
up to the filesystem's block allocation algorithm. For example, the algorithm might be designed to
favour allocating blocks contiguously for a file: recently-freed blocks are unlikely to be in the
ideal place for the file being extended.

Since the block allocator in practice tends to favour unused blocks, the result is that the `Docker.raw`
(or `Docker.qcow2`) will constantly accumulate new blocks, many of which contain stale data.
The file on the host gets larger and larger, even though the filesystem inside the VM
still reports plenty of free space.

# Aside: SSD drives have a similar problem

SSD drives suffer from the same phenomenon. SSDs are only able to erase data in large blocks (where the
"erase block" size is different from the exposed sector size) and the erase operation is quite slow. The
drive firmware runs a garbage collector, keeping track of which blocks are free and where user data
is stored. To modify a sector, the firmware will allocate a fresh block and, to avoid the device filling
up with almost-empty blocks containing only one sector, will consider moving some existing data into it.

If the filesystem writing to the SSD tends to favour writing to unused blocks, then creating and removing
files will cause the SSD to fill up (from the point of view of the firmware) with stale data (from the point
of view of the filesystem). Eventually the performance of the SSD will fall as the firmware has to spend
more and more time compacting the stale data before it can free enough space for new data.

# TRIM

A [TRIM](https://en.wikipedia.org/wiki/Trim_(computing)) command (or a `DISCARD` or `UNMAP`) allows a
filesystem to signal to a disk that a range of sectors contain stale data and they can be forgotten.
This allows:

- an SSD drive to erase and reuse the space, rather than spend time shuffling it around; and
- Docker for Mac to deallocate the blocks in the host filesystem, shrinking the file.

So how do we make this work?

# Automatic TRIM in Docker for Mac

In Docker for Mac 17.11 there is a [containerd](https://containerd.io) "task"
called `trim-after-delete` listening for Docker image deletion events. It can be seen via the
`ctr` command:
{% highlight raw %}
$ docker run --rm -it --privileged --pid=host walkerlee/nsenter -t 1 -m -u -i -n ctr t ls
TASK                    PID     STATUS    
vsudd                   1741    RUNNING
acpid                   871     RUNNING
diagnose                913     RUNNING
docker-ce               958     RUNNING
host-timesync-daemon    1046    RUNNING
ntpd                    1109    RUNNING
trim-after-delete       1339    RUNNING
vpnkit-forwarder        1550    RUNNING
{% endhighlight %}

When an image deletion event is received, the process waits for a few seconds (in case other images are being
deleted, for example as part of a
[docker system prune](https://docs.docker.com/engine/reference/commandline/system_prune/)
) and then runs `fstrim` on the filesystem.

Returning to the example in the previous section, if you delete the 1 GiB file inside the `alpine` container
{% highlight raw %}
/ # rm -f 1GiB
{% endhighlight %}
then run `fstrim` manually from a terminal in the host:
{% highlight raw %}
$ docker run --rm -it --privileged --pid=host walkerlee/nsenter -t 1 -m -u -i -n fstrim /var/lib/docker
{% endhighlight %}
then check the file size:
{% highlight raw %}
$ ls -s Docker.raw 
9965016 Docker.raw
{% endhighlight %}
The file is back to (approximately) it's original size -- the space has finally been freed!

# The code

There are two separate implementations of TRIM in Docker for Mac: one for `Docker.qcow2` and one for `Docker.raw`.
On High Sierra running on an SSD, the default filesystem is
[APFS](https://en.wikipedia.org/wiki/Apple_File_System)
and we use `Docker.raw` by default. This is because APFS supports
an API for deallocating blocks from inside a file, while HFS+ does not. On older versions of macOS and
on non-SSD hardware we default to `Docker.qcow2` which implements block deallocation in userspace which is more complicated and generally slower.
Note that Apple hope to add support to APFS for fusion and traditional spinning disks in
[some future update](https://www.apple.com/newsroom/2017/09/macos-high-sierra-now-available-as-a-free-update/)
-- once this happens we will switch to `Docker.raw` on those systems as well.

Support for adding TRIM to `hyperkit` for `Docker.raw` was added in
[PR 158](https://github.com/moby/hyperkit/pull/158).
When the `Docker.raw` file is opened it calls
[fcntl(F_PUNCHHOLE)](https://github.com/moby/hyperkit/blob/81fa6279fcb17e8435f3cec0978e9aa3af02e63b/src/lib/block_if.c#L712)
on a zero-length region at the start of the file to probe whether the filesystem supports block deallocation.
On HFS+ this will fail and we will disable TRIM, but on APFS (and possibly future filesystems) this
succeeds and so we enable TRIM.
To let Linux running in the VM know that we support TRIM we set [some bits](https://github.com/moby/hyperkit/blob/81fa6279fcb17e8435f3cec0978e9aa3af02e63b/src/lib/pci_ahci.c#L993)
in the AHCI hardware identification message, specifically:
- `ATA_SUPPORT_RZAT`: we guarantee to Read-Zero-After-TRIM (RZAT)
- `ATA_SUPPORT_DRAT`: we guarantee Deterministic-Read-After-TRIM (DRAT) (i.e. the result of reading after TRIM won't change)
- `ATA_SUPPORT_DSM_TRIM`: we support the `TRIM` command

Once enabled the Linux kernel will send us TRIM commands which we implement with
[fcntl(F_PUNCHOLE)](https://github.com/moby/hyperkit/blob/81fa6279fcb17e8435f3cec0978e9aa3af02e63b/src/lib/block_if.c#L250)
with the caveat that the sector size in the VM is currently 512, while the sector size on the host can
be different (it's probably 4096) which means we have to be careful with alignment.

The support for TRIM in `Docker.qcow2` is via the
[Mirage](https://mirage.io/)
[qcow2](https://github.com/mirage/ocaml-qcow/) library.
This library contains its own
[block garbage collector](https://github.com/mirage/ocaml-qcow/blob/master/doc/TRIM.md)
which manages a free list of TRIM'ed blocks within the
file and then performs background compaction and erasure (similar to the firmware on an SSD).
The GC must run concurrently and with lower priority than reads and writes from the VM, otherwise
Linux will timeout and attempt to reset the AHCI controller (which unfortunately isn't implemented fully).

The
[qcow2 format](https://people.gnome.org/~markmc/qcow-image-format.html)
includes both data blocks and metadata blocks, where the metadata blocks contain references to other blocks.
When performing a compaction of the file, care must be taken to flush copies of blocks to stable storage
before updating references to them, otherwise the writes could be permuted leading to the reference update
being persisted but not the data copy -- corrupting the file.
Since
flushes are very slow (taking maybe 10ms), block copies are done in large batches to spread the cost.
If the VM writes to one of the blocks being copied, then that block copy must be cancelled and retried later.
All of this means that the code is much more complicated and much slower than the `Docker.raw` version;
presumably the implementation of `fcntl(F_PUNCHHOLE)` in the macOS kernel
operates only on the filesystem metadata and doesn't involve any data copying!

# Status in Docker for Mac releases

As of 2017-11-28 the latest Docker for Mac edge version is `17.11.0-ce-mac40 (20561)` -- automatic TRIM
on image delete is
enabled by default on both `Docker.raw` and `Docker.qcow2` files (although the `Docker.raw` implementation
is faster).

If you feel Docker for Mac is taking up too much space, first check how many images and
containers you have with

- `docker image ls -a`
- `docker ps -a`

and consider deleting some of those images or containers, perhaps by running a
[docker system prune](https://docs.docker.com/engine/reference/commandline/system_prune/)):
```
$ docker system prune
WARNING! This will remove:
        - all stopped containers
        - all networks not used by at least one container
        - all dangling images
        - all build cache
Are you sure you want to continue? [y/N] y
Deleted Containers:
a5ecfabb1f495bc38060f3bd41b211aa3e142973641f4338020b0c1e91b5a96e
bf0703e736291a07a5ec676f15a69b310de8f4ee0dd09c955b239f3eae9a4111
c43097d993331b4a69324df82031de83a9a2c085284049d21dafa761bf9dd35f
6c36c476df16266b35ff7a3871e88fe38305db3f792485e47ce83d38f74ddeea
8ed3490b9822f207da7399e298397631846c85101d30ff9e240b28c06443a9d9
97c51fbf4b0692f5834d2dfed90ba3348b937bd005bf51c2161eab7439fc73e2
a8597872d173681c2ded54104087708bfb40dfa744a7e7a29681aeeccd9d7e90
8cd482219a378ac24f32259e8a5694d57547c2dbf7eed121cbb1166e36c37979
85b9759852fe8859c466e63028b7195ef6ec2930fa3d22eadd086e13d3c1f379
990a7cea94c39ac1511c140f5084655d510e55ce437f48a72d570e3ac3f5f0cb
098fc1997e1237e586fe0fb2442cc1e8b5abdb269e53cd5d230fee96270dffab
278680445afffa66e165b698141cb38de54badc52ea1c7bdc2a758760637c779
6192e0ce5920ccd9fbbaa97b10e79f6f33e786dc8f6d68381a836bb4834a013c
bf73db371ac024294f64e96300cb1d5a797b3deb6aa13412ab21130a7ebae366

Total reclaimed space: 2.147GB
```
The automatic TRIM on delete should kick in shortly after the images are deleted and free the space
on the host. Take care to measure the space usage with `ls -s` to see the actual number of
blocks allocated by the files.

If you want to trigger a TRIM manually in other cases, then run
```sh
docker run --rm -it --privileged --pid=host walkerlee/nsenter -t 1 -m -u -i -n fstrim /var/lib/docker
```

To try all this for yourself, get the latest edge version of Docker for Mac from the
[Docker Store](https://download.docker.com/mac/edge/Docker.dmg).
Let me know how you get on in the `docker-for-mac` channel of the
[Docker community slack](https://community.docker.com/registrations/groups/4316).
If you hit a bug, file an issue on
[docker/for-mac on GitHub](https://github.com/docker/for-mac).