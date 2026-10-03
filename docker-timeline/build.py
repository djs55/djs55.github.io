#!/usr/bin/env python3
"""Build the Docker timeline page.

The content lives in timeline-source.html (plain markup, one terminal-card
per year). This script only changes the presentation, so edit the content
there and re-run:

    python3 build.py

That writes index.html: the zigzag layout with a boot sequence. The boot
style defaults to x11 (BOOT_STYLE below); ?boot=<style> in the URL replays it
in another style.

An <article> can override the automatic theme tags with
data-tags="networking storage" (see TAGS below for the names).
"""
import base64
import html
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "timeline-source.html"
LIVE = HERE / "index.html"

# ---------------------------------------------------------------- content


def strip_tags(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


LINK_KINDS = [
    ("pr", r"github\.com/[^/]+/[^/]+/pull/"),
    ("issue", r"github\.com/[^/]+/[^/]+/issues/"),
    ("release", r"release-notes|previous-versions"),
    ("code", r"github\.com/"),
    ("talk", r"youtube\.com|/slides/"),
    ("award", r"award"),
    ("paper", r"\.pdf$|doi\.org|cacm\.acm\.org|icfp25"),
    ("news", r"press-release|appleinsider|cst\.cam\.ac\.uk/news|support\.apple\.com|/notes/"),
    ("post", r"docker\.com/blog|dave\.recoil\.org|docs\.docker\.com"),
]

KIND_LABEL = {
    "pr": "pull request", "issue": "issue comment", "release": "release notes",
    "code": "code", "talk": "talk", "award": "award", "paper": "paper",
    "news": "news", "post": "article", "link": "link",
}

# (id, label, regex over title + body text)
TAGS = [
    ("networking", "networking", r"network|vpnkit|\bdns\b|\btcp\b|prox(y|ies)|socks|port forward|named pipe|localhost|socket|cve"),
    ("storage", "storage", r"\bdisk|qcow|\btrim\b|discard|compaction|storage"),
    ("files", "file sharing", r"file sharing|file-sharing|fuse|filesharing|mutagen|virtiofs|shared folders|file change"),
    ("vms", "VMs &amp; platforms", r"apple silicon|\bm1\b|\bvmm\b|hypervisor|microvm|virtualization|kubernetes|irmin|alpha builds|resource saver|memory|clock"),
    ("enterprise", "enterprise", r"registry access|business|policy|socks|customer|restricted networks|corporate"),
    ("writing", "papers &amp; talks", None),
]
TAG_LABEL = {t[0]: t[1] for t in TAGS}


def link_kind(href):
    for kind, pat in LINK_KINDS:
        if re.search(pat, href):
            return kind
    return "link"


def parse_article(a):
    m = re.match(r'<article([^>]*)>(.*)</article>', a, re.S)
    attrs, inner = m.group(1), m.group(2)
    h3 = re.search(r"<h3>(.*?)</h3>", inner, re.S).group(1)
    date_m = re.search(r'<span class="date">(.*?):?</span>', h3, re.S)
    date = strip_tags(date_m.group(1)).rstrip(":") if date_m else ""
    title = re.sub(r'<span class="date">.*?</span>\s*', "", h3, flags=re.S).strip()
    links_m = re.search(r'<p class="links">(.*?)</p>', inner, re.S)
    links = []
    if links_m:
        for href, text in re.findall(r'<a href="([^"]+)"[^>]*>(.*?)</a>', links_m.group(1), re.S):
            links.append({"href": href, "text": strip_tags(text).strip("[]"), "kind": link_kind(href)})
    body = re.sub(r'<p class="links">.*?</p>', "", inner, flags=re.S)
    body = re.sub(r"<h3>.*?</h3>", "", body, flags=re.S).strip()
    paras = re.findall(r"<p>.*?</p>", body, re.S)

    tm = re.search(r'data-tags="([^"]*)"', attrs)
    if tm:
        tags = tm.group(1).split()
    else:
        text = (strip_tags(title) + " " + strip_tags(body)).lower()
        tags = [tid for tid, _, pat in TAGS if pat and re.search(pat, text)]
        kinds = {l["kind"] for l in links}
        if kinds & {"paper", "talk", "award"} or re.search(r"blog post|deep dive|my .*post", " ".join(l["text"] for l in links)):
            tags.append("writing")
        if not tags:
            tags = ["vms"]
    return {"date": date, "title": title, "paras": paras, "links": links, "tags": tags}


def load():
    src = SRC.read_text()
    intro = re.search(r'<p class="prompt-line">.*?</p>\s*(.*?)\s*<ul class="years"', src, re.S).group(1)
    region = src.split('id="timeline">', 1)[1].split("<script>", 1)[0]
    years = []
    for chunk in region.split('<div class="terminal-card" id="y')[1:]:
        year = chunk[:4]
        header = re.search(r"<header>(.*?)</header>", chunk, re.S).group(1)
        tag_m = re.search(r'<span class="tagline">(?:&mdash;|—)?\s*(.*?)</span>', header, re.S)
        tagline = tag_m.group(1).strip() if tag_m else ""
        arts = [parse_article(a) for a in re.findall(r"<article[^>]*>.*?</article>", chunk, re.S)]
        years.append({"year": year, "tagline": tagline, "articles": arts})
    return {"intro": intro, "years": years}



# ---------------------------------------------------------------- shared bits

ICONS = """
<svg width="0" height="0" style="position:absolute" aria-hidden="true">
  <defs>
    <symbol id="i-pr" viewBox="0 0 16 16"><circle cx="4" cy="3.5" r="1.7"/><circle cx="4" cy="12.5" r="1.7"/><circle cx="12" cy="12.5" r="1.7"/><path d="M4 5.2v5.6M12 10.8V6.5a2 2 0 0 0-2-2H7M8.8 2.8 7 4.5l1.8 1.7"/></symbol>
    <symbol id="i-issue" viewBox="0 0 16 16"><circle cx="8" cy="8" r="6"/><circle cx="8" cy="8" r="1.2"/></symbol>
    <symbol id="i-code" viewBox="0 0 16 16"><path d="M5.5 4 2 8l3.5 4M10.5 4 14 8l-3.5 4"/></symbol>
    <symbol id="i-post" viewBox="0 0 16 16"><path d="M3 1.8h6.5l3.5 3.5v8.9H3zM9.5 1.8v3.5H13M5.5 8.3h5M5.5 11h5"/></symbol>
    <symbol id="i-paper" viewBox="0 0 16 16"><path d="M1.8 3h4.5A1.7 1.7 0 0 1 8 4.7V13.5a1.5 1.5 0 0 0-1.5-1.5H1.8zM14.2 3H9.7A1.7 1.7 0 0 0 8 4.7V13.5A1.5 1.5 0 0 1 9.5 12h4.7z"/></symbol>
    <symbol id="i-talk" viewBox="0 0 16 16"><rect x="1.5" y="3" width="13" height="10" rx="2"/><path d="M6.5 5.8v4.4L10.3 8z"/></symbol>
    <symbol id="i-award" viewBox="0 0 16 16"><path d="M8 1.6l1.9 3.9 4.3.6-3.1 3 .7 4.3L8 11.4l-3.8 2 .7-4.3-3.1-3 4.3-.6z"/></symbol>
    <symbol id="i-release" viewBox="0 0 16 16"><path d="M1.8 2.2h5.6l6.8 6.8-5.2 5.2-7.2-6.8z"/><circle cx="4.9" cy="5.3" r="1"/></symbol>
    <symbol id="i-news" viewBox="0 0 16 16"><rect x="1.8" y="2.8" width="12.4" height="10.4" rx="1"/><path d="M4.5 6h7M4.5 8.5h7M4.5 11h4"/></symbol>
    <symbol id="i-link" viewBox="0 0 16 16"><path d="M7 9a3 3 0 0 0 4.2 0l2.3-2.3a3 3 0 0 0-4.2-4.2L8.5 3.3M9 7a3 3 0 0 0-4.2 0L2.5 9.3a3 3 0 0 0 4.2 4.2l.8-.8"/></symbol>
  </defs>
</svg>"""

COMMON_CSS = """
.lk { display: inline-flex; align-items: center; gap: 4px; margin-right: 0.9em; white-space: nowrap; }
.lk svg { width: 14px; height: 14px; flex: none; fill: none; stroke: currentColor; stroke-width: 1.4; stroke-linecap: round; stroke-linejoin: round; }
.links { color: var(--secondary-color); font-size: 0.93em; line-height: 1.7em; }
.tag { display: inline-block; font-size: 0.78em; line-height: 1.5; padding: 0 6px; margin: 0 4px 2px 0;
       border: 1px solid currentColor; border-radius: 3px; color: var(--secondary-color); white-space: nowrap; vertical-align: 1px; }
.terminal-menu li::after { content: none; }
"""

def head(title, extra_css, theme_color="#fff", color_scheme="light"):
    return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>{title}</title>
    <meta name="description" content="Things Dave Scott has worked on at Docker, from 2026 back to 2015.">
    <meta name="author" content="Dave Scott">
    <meta name="twitter:title" content="{title}">
    <meta name="twitter:description" content="Things Dave Scott has worked on at Docker, from 2026 back to 2015.">
    <meta property="og:site_name" content="Dave Scott">
    <meta property="og:type" content="object">
    <meta property="og:title" content="{title}">
    <meta property="og:description" content="Things Dave Scott has worked on at Docker, from 2026 back to 2015.">
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
    <link rel="icon" href="/favicon.ico">
    <meta name="theme-color" content="{theme_color}">
    <meta name="color-scheme" content="{color_scheme}">
    <link rel="stylesheet" href="https://unpkg.com/terminal.css@0.7.4/dist/terminal.min.css" />
    <script>document.documentElement.classList.add('js');</script>
    <style>{COMMON_CSS}{extra_css}</style>
  </head>
"""


NAV = """
    <div class="container">
      <div class="terminal-nav">
        <header class="terminal-logo">
          <div class="logo terminal-prompt"><a href="/" class="no-style">Dave Scott</a></div>
        </header>
      <nav class="terminal-menu">
        <ul vocab="https://schema.org/" typeof="BreadcrumbList">
          <li><a href="/" class="menu-item"><span>Home</span></a><meta property="position"></li>
          <li property="itemListElement" typeof="ListItem"><a href="/blog.html" property="item" typeof="WebPage" class="menu-item"><span property="name">Blog</span></a><meta property="position" content="1"></li>
          <li property="itemListElement" typeof="ListItem"><a href="/research.html" property="item" typeof="WebPage" class="menu-item"><span property="name">Research</span></a><meta property="position" content="2"></li>
          %EXTRA%
        </ul>
      </nav>
    </div>
"""


def nav(extra=""):
    return NAV.replace("%EXTRA%", extra)


def links_html(links):
    if not links:
        return ""
    out = []
    for l in links:
        out.append(
            f'<a class="lk lk-{l["kind"]}" href="{l["href"]}" title="{KIND_LABEL[l["kind"]]}">'
            f'<svg aria-hidden="true"><use href="#i-{l["kind"]}"/></svg>{html.escape(l["text"])}</a>'
        )
    return '<p class="links">' + "".join(out) + "</p>"


def tags_html(tags):
    return "".join(f'<span class="tag tag-{t}">{TAG_LABEL[t]}</span>' for t in tags)


def year_links(data):
    return "".join(f'<li><a href="#y{y["year"]}">{y["year"]}</a></li>' for y in data["years"])


def filters_html():
    btns = ['<button type="button" class="chip active" data-tag="all">all</button>']
    btns += [f'<button type="button" class="chip" data-tag="{t}">{l}</button>' for t, l, _ in TAGS]
    return '<div class="filters" role="group" aria-label="Filter by theme">' + "".join(btns) + "</div>"


# Reveal-on-scroll, progress line and current-year highlighting, shared by all variants.
REVEAL_JS = """
function setupReveal(opts) {
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var cards = Array.prototype.slice.call(document.querySelectorAll(opts.cards));
  var yearLinks = {};
  document.querySelectorAll('.years a').forEach(function (a) { yearLinks[a.getAttribute('href').slice(1)] = a; });
  function reveal(c) { if (!c.classList.contains('seen')) { c.classList.add('seen'); if (opts.onReveal) opts.onReveal(c, reduce); } }
  if ('IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (e) { if (e.isIntersecting) { reveal(e.target); io.unobserve(e.target); } });
    }, { rootMargin: '0px 0px -12% 0px' });
    cards.forEach(function (c) { io.observe(c); });
  } else { cards.forEach(reveal); }
  Object.keys(yearLinks).forEach(function (id) {
    yearLinks[id].addEventListener('click', function () { var c = document.getElementById(id); if (c) reveal(c); });
  });
  var timeline = document.querySelector(opts.timeline), ticking = false;
  function update() {
    ticking = false;
    var r = timeline.getBoundingClientRect(), mid = window.innerHeight * 0.6;
    var h = Math.max(0, Math.min(r.height, mid - r.top));
    if (opts.onProgress) opts.onProgress(h, r.height);
    var current = null;
    cards.forEach(function (c) { if (c.offsetParent !== null && c.getBoundingClientRect().top < mid) current = c.id; });
    Object.keys(yearLinks).forEach(function (id) { yearLinks[id].classList.toggle('active', id === current); });
    if (opts.onYear) opts.onYear(current);
  }
  window.addEventListener('scroll', function () { if (!ticking) { ticking = true; requestAnimationFrame(update); } }, { passive: true });
  window.addEventListener('resize', update);
  update();
  return { update: update, reveal: reveal, reduce: reduce };
}

function setupFilters(onChange) {
  var chips = document.querySelectorAll('.chip');
  chips.forEach(function (chip) {
    chip.addEventListener('click', function () {
      var tag = chip.getAttribute('data-tag');
      chips.forEach(function (c) { c.classList.toggle('active', c === chip); c.setAttribute('aria-pressed', c === chip); });
      document.querySelectorAll('[data-tags]').forEach(function (a) {
        var show = tag === 'all' || a.getAttribute('data-tags').split(' ').indexOf(tag) >= 0;
        a.classList.toggle('filtered', !show);
      });
      document.querySelectorAll('[data-year]').forEach(function (y) {
        y.classList.toggle('filtered', y.querySelectorAll('[data-tags]:not(.filtered)').length === 0);
      });
      if (onChange) onChange(tag);
    });
  });
}

function store(key, val) {
  try { if (val === undefined) return localStorage.getItem(key); localStorage.setItem(key, val); } catch (e) { return null; }
}
"""

# ---------------------------------------------------------------- A: zigzag


A_CSS = """
:root[data-theme="dark"] {
  --background-color: #16181b; --font-color: #e6e6e6; --invert-font-color: #16181b;
  --primary-color: #4fb3f6; --secondary-color: #9aa0a6; --code-bg-color: #262a30; --block-background-color: #16181b;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --background-color: #16181b; --font-color: #e6e6e6; --invert-font-color: #16181b;
    --primary-color: #4fb3f6; --secondary-color: #9aa0a6; --code-bg-color: #262a30; --block-background-color: #16181b;
  }
}
body { background: var(--background-color); transition: background-color .3s ease, color .3s ease; }
.theme-toggle { background: none; border: 1px solid var(--secondary-color); color: var(--secondary-color);
  font: inherit; padding: 0 8px; cursor: pointer; border-radius: 3px; }
.theme-toggle:hover { color: var(--primary-color); border-color: var(--primary-color); }
.lede { max-width: 46em; }

.filters { display: flex; flex-wrap: wrap; gap: 8px; margin: 20px 0 8px; }
.chip { font: inherit; font-size: .9em; cursor: pointer; padding: 2px 10px; border-radius: 999px;
  border: 1px solid var(--secondary-color); background: transparent; color: var(--font-color); transition: all .2s ease; }
.chip:hover { border-color: var(--primary-color); color: var(--primary-color); }
.chip.active { background: var(--primary-color); border-color: var(--primary-color); color: var(--invert-font-color); }
.years { display: flex; flex-wrap: wrap; gap: 4px 14px; list-style: none; padding: 0; margin: 12px 0 30px; }
.years li { margin: 0; padding: 0; } .years li::after { content: none; }
.years a.active { background: var(--primary-color); color: var(--invert-font-color); }

.zz { position: relative; padding: 10px 0 40px; }
.zz-line { position: absolute; left: 50%; top: 0; bottom: 0; width: 2px; margin-left: -1px; background: var(--secondary-color); opacity: .5; }
.zz-fill { position: absolute; left: 50%; top: 0; width: 2px; margin-left: -1px; height: 0; background: var(--primary-color); }
.zz-year { position: relative; display: flex; margin: 0 0 34px; scroll-margin-top: 20px; pointer-events: none; }
.zz-card, .zz-node { pointer-events: auto; }
.zz-year.left { justify-content: flex-start; } .zz-year.right { justify-content: flex-end; }
.zz-node { position: absolute; left: 50%; top: 14px; transform: translateX(-50%); z-index: 3;
  background: var(--background-color); border: 2px solid var(--secondary-color); color: var(--secondary-color);
  font-weight: bold; padding: 2px 10px; border-radius: 999px; transition: all .4s ease; }
.zz-year.seen .zz-node { background: var(--primary-color); border-color: var(--primary-color); color: var(--invert-font-color); }
.zz-card { width: calc(50% - 56px); position: relative; background: var(--background-color); }
.zz-card::after { content: ""; position: absolute; top: 25px; width: 40px; height: 2px; background: var(--secondary-color); opacity: .5; }
.zz-year.left .zz-card::after { right: -42px; } .zz-year.right .zz-card::after { left: -42px; }
.zz-card > header { text-align: left; padding-left: 10px; transition: background-color .4s ease; }
.zz-year.seen .zz-card > header { background: var(--font-color); color: var(--background-color); }
.zz-card article { margin-bottom: 18px; transition: opacity .3s ease; }
.zz-card article:last-child { margin-bottom: 0; }
.zz-card h3 { font-size: var(--global-font-size); margin: 0 0 4px; padding: 0; }
.zz-card h3 .date { color: var(--secondary-color); font-weight: normal; }
.zz-card p { margin-bottom: .4em; }
.meta { margin: 0 0 4px; }
.filtered { display: none !important; }

@media (prefers-reduced-motion: no-preference) {
  .js .zz-card { opacity: 0; transition: opacity .6s ease, transform .6s cubic-bezier(.2,.7,.2,1); }
  .js .zz-year.left .zz-card { transform: translateX(-40px); }
  .js .zz-year.right .zz-card { transform: translateX(40px); }
  .js .zz-year.seen .zz-card { opacity: 1; transform: none; }
  .zz-year.seen .zz-node { animation: pop .5s ease; }
  @keyframes pop { 50% { transform: translateX(-50%) scale(1.18); } }
  .zz-fill { transition: height .15s linear; }
}

@media (max-width: 760px) {
  .zz-line, .zz-fill { left: 14px; }
  .zz-year, .zz-year.left, .zz-year.right { justify-content: flex-end; padding-top: 40px; }
  .zz-node { left: 14px; top: 0; transform: none; }
  @keyframes pop { 50% { transform: scale(1.12); } }
  .zz-card { width: calc(100% - 34px); }
  .zz-card::after { display: none; }
  .js .zz-year.left .zz-card, .js .zz-year.right .zz-card { transform: translateY(24px); }
  .js .zz-year.seen .zz-card { transform: none; }
}
"""

A_JS = """
(function () {
  var root = document.documentElement, btn = document.getElementById('theme');
  var modes = ['auto', 'light', 'dark'];
  function apply(m) { if (m === 'auto') root.removeAttribute('data-theme'); else root.setAttribute('data-theme', m); btn.textContent = 'theme: ' + m; }
  var mode = store('timeline-theme') || 'auto'; apply(mode);
  btn.addEventListener('click', function () { mode = modes[(modes.indexOf(mode) + 1) % 3]; store('timeline-theme', mode); apply(mode); });
  var fill = document.getElementById('fill');
  var r = setupReveal({ cards: '.zz-year', timeline: '#timeline', onProgress: function (h) { fill.style.height = h + 'px'; } });
  // Pull each card up alongside the previous one, so the two columns interleave.
  var zz = document.getElementById('timeline');
  function pack() {
    var secs = Array.prototype.slice.call(document.querySelectorAll('.zz-year:not(.filtered)'));
    secs.forEach(function (s, i) {
      s.style.marginTop = '';
      s.classList.toggle('left', i % 2 === 0); s.classList.toggle('right', i % 2 === 1);
    });
    zz.style.paddingBottom = '';
    if (window.innerWidth <= 760) return;
    var bottom = { left: -1e9, right: -1e9 }, prevTop = -1e9, maxBottom = 0;
    secs.forEach(function (s) {
      var side = s.classList.contains('left') ? 'left' : 'right';
      var want = Math.max(prevTop + 120, bottom[side] + 34, 0);
      s.style.marginTop = (want - s.offsetTop) + 'px';
      prevTop = s.offsetTop; bottom[side] = prevTop + s.offsetHeight;
      maxBottom = Math.max(maxBottom, bottom[side]);
    });
    var last = secs[secs.length - 1];
    if (last) zz.style.paddingBottom = (40 + maxBottom - (last.offsetTop + last.offsetHeight)) + 'px';
    r.update();
  }
  pack();
  window.addEventListener('resize', pack);
  if (document.fonts) document.fonts.ready.then(pack);
  setupFilters(function () { pack(); document.querySelectorAll('.zz-year').forEach(r.reveal); r.update(); });
})();
"""


def render_a(d, boot=False, title="Dave Scott: Docker timeline (zigzag)"):
    out = [head(title, (BOOT_CSS if boot else "") + A_CSS), '  <body class="terminal">', ICONS, *([boot_html()] if boot else []),
           nav('<li><button type="button" class="theme-toggle" id="theme">theme: auto</button></li>'),
           '    <div class="container">',
           f'      <div class="lede">{d["intro"]}</div>', "      " + filters_html(),
           f'      <ul class="years">{year_links(d)}</ul>',
           '      <div class="zz" id="timeline"><div class="zz-line"></div><div class="zz-fill" id="fill"></div>']
    for i, y in enumerate(d["years"]):
        side = "left" if i % 2 == 0 else "right"
        out.append(f'      <section class="zz-year {side}" id="y{y["year"]}" data-year="{y["year"]}">')
        out.append(f'        <div class="zz-node">{y["year"]}</div>')
        out.append(f'        <div class="zz-card terminal-card"><header>{y["tagline"]}</header><div>')
        for a in y["articles"]:
            date = f'<span class="date">{a["date"]}:</span> ' if a["date"] else ""
            out.append(f'          <article data-tags="{" ".join(a["tags"])}"><h3>{date}{a["title"]}</h3>'
                       f'<p class="meta">{tags_html(a["tags"])}</p>{"".join(a["paras"])}{links_html(a["links"])}</article>')
        out.append("        </div></div>\n      </section>")
    out += ["      </div>", "    </div>", f"    <script>{REVEAL_JS}{BOOT_JS if boot else ''}{A_JS}{'runBoot();' if boot else ''}</script>", "  </body>", "</html>"]
    return "\n".join(out)


# ---------------------------------------------------------------- boot sequence 

# The boot ends in a video mode switch, in one of three styles:
#   x11     Linux text console (Terminus), then startx: blank, X root weave and cursor, then the page
#   dos     VGA text and C:\>win: blank while the monitor resyncs, then the page
#   aliens  green phosphor, then the picture loses vertical hold and rolls
# ?boot=<style> in the URL picks a style (and replays the boot).
BOOT_STYLE = "x11"


def boot_html(style=BOOT_STYLE):
    return (f'    <div id="boot" data-style="{style}" aria-hidden="true"><pre></pre>'
            '<span class="skip">click or press any key to skip</span><span class="noise"></span>'
            '<svg class="xcursor" viewBox="0 0 16 16"><path d="M2 2 14 14M14 2 2 14" stroke="#fff" stroke-width="5"/>'
            '<path d="M2 2 14 14M14 2 2 14" stroke="#000" stroke-width="2.4"/></svg></div>')


# The x11 console font, embedded so the page stays a single file (see scripts/make-boot-font.py).
BOOT_FONT = base64.b64encode((HERE / "fonts" / "boot-console.woff2").read_bytes()).decode()

# Colours default to green phosphor; a page can override the --boot-* variables.
BOOT_CSS = """
/* Boot Console: an ASCII subset of Terminus (TTF) 4.49.3, (c) 2010 Dimitar Toshkov Zhekov,
   (c) 2011-2023 Tilman Blumenbach. SIL Open Font License 1.1 (https://openfontlicense.org),
   renamed as its Reserved Font Name terms require. */
@font-face { font-family: "Boot Console"; font-display: block;
  src: url(data:font/woff2;base64,%BOOT_FONT%) format("woff2"); }
#boot { --boot-bg: #0a0f0b; --boot-fg: #b8ffc9; --boot-dim: #4f8a5e; --boot-glow: rgba(57,255,106,.45);
  position: fixed; inset: 0; z-index: 9500; background: var(--boot-bg); padding: 30px 24px; overflow: hidden; cursor: pointer; }
#boot::after { content: ""; position: absolute; inset: 0; pointer-events: none;
  background: repeating-linear-gradient(to bottom, transparent 0 2px, rgba(0,0,0,.22) 3px); }
#boot pre { background: none; border: 0; margin: 0; padding: 0; color: var(--boot-fg); white-space: pre-wrap;
  font-size: 14px; line-height: 1.5; text-shadow: 0 0 6px var(--boot-glow); }
#boot .cursor { display: inline-block; width: .6em; height: 1.1em; vertical-align: text-bottom; background: var(--boot-fg);
  box-shadow: 0 0 8px var(--boot-glow); animation: boot-blink 1.1s steps(1) infinite; }
@keyframes boot-blink { 50% { opacity: 0; } }
#boot .skip { position: absolute; bottom: 20px; right: 24px; color: var(--boot-dim); }
#boot .noise, #boot .xcursor { display: none; }

/* VGA text mode: grey on black, underscore cursor, no glow */
#boot.dos { --boot-bg: #000; --boot-fg: #aaa; --boot-dim: #555; --boot-glow: transparent; }
#boot.dos pre { font-size: 16px; line-height: 1.3; }
#boot.dos .cursor, #boot.x11 .cursor { height: .18em; vertical-align: baseline; box-shadow: none; animation-duration: .5s; }

/* Linux text console: VGA grey on black in Terminus, no CRT effects, systemd's green OK */
#boot.x11 { --boot-bg: #000; --boot-fg: #aaa; --boot-dim: #555; --boot-glow: transparent; }
#boot.x11::after { display: none; }
#boot.x11 pre { font-family: "Boot Console", var(--mono-font-stack); font-size: 16px; line-height: 1; }
#boot.x11 .ok { color: #55ff55; }
#boot.x11 .skip { font-family: "Boot Console", var(--mono-font-stack); font-size: 16px; }

/* the mode switch: the monitor loses sync and shows nothing */
#boot.blank { background: #000; cursor: none; }
#boot.blank > *, #boot.blank::after { visibility: hidden; }

/* X root window: the grey weave, with the X cursor in the middle */
#boot.xroot { background-color: #000; cursor: none;
  background-image: repeating-conic-gradient(#000 0 25%, #fff 0 50%); background-size: 2px 2px; }
#boot.xroot > * { visibility: hidden; }
#boot.xroot > .xcursor { visibility: visible; display: block; position: absolute; left: 50%; top: 50%;
  width: 16px; height: 16px; margin: -8px 0 0 -8px; }

/* losing vertical hold: the picture rolls, with a blanking bar and static */
#boot.roll { cursor: none; animation: roll-flicker .09s steps(2) infinite; }
#boot.roll pre { animation: roll .3s linear infinite; }
#boot pre.ghost { position: absolute; left: 24px; right: 24px; top: calc(100vh + 30px); }
#boot.roll .skip { visibility: hidden; }
@keyframes roll { from { transform: translateY(0); } to { transform: translateY(-100vh); } }
#boot.roll::before { content: ""; position: absolute; left: 0; right: 0; height: 12vh; z-index: 2;
  background: #000; box-shadow: 0 0 24px 10px #000; animation: roll-bar .3s linear infinite; }
@keyframes roll-bar { from { top: 100%; } to { top: -12vh; } }
#boot.roll .noise { display: block; position: absolute; inset: 0; opacity: .14; z-index: 3;
  background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='160' height='160'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='.95' numOctaves='2' stitchTiles='stitch'/></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>");
  animation: roll-noise .12s steps(3) infinite; }
@keyframes roll-noise { 0% { background-position: 0 0; } 100% { background-position: 97px 53px; } }
@keyframes roll-flicker { 50% { filter: brightness(1.35); } }

/* the picture locking on after a resync */
html.boot-sync body { animation: boot-sync .28s steps(4) 1; }
@keyframes boot-sync {
  0% { transform: translateX(7px); filter: brightness(1.4); }
  25% { transform: translateX(-4px); filter: brightness(1.15); }
  50% { transform: translateX(2px); }
  100% { transform: none; filter: none; }
}
""".replace("%BOOT_FONT%", BOOT_FONT)

# Plays once per browser session per page; ?boot or ?boot=<style> replays it.
BOOT_JS = r"""
function runBoot() {
  var boot = document.getElementById('boot');
  if (!boot) return;
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var m = location.search.match(/[?&]boot(?:=(\w+))?/);
  var STYLES = {
    x11: {
      exit: [['blank', 350], ['xroot', 650]], sync: false, delay: 60,
      lines: [
        '[    0.000000] Linux version 6.12.0-linuxkit (root@moby) #1 SMP PREEMPT_DYNAMIC',
        '[    0.081234] virtio_blk virtio1: [vda] qcow2, thin-provisioned 64.0 GiB',
        '[    0.204511] virtio_net virtio0 eth0: vpnkit: ethernet frames <-> host sockets',
        '[  OK  ] Started irmin.service - VM configuration watcher.',
        '[  OK  ] Started vpnkit-dns.service - DNS forwarding via host resolver.',
        '[  OK  ] Mounted Users.mount - grpcfuse share /Users.',
        '[  OK  ] Started docker.service - Docker Application Container Engine.',
        '[  OK  ] Reached target resource-saver.target - Pause VM when idle.',
        '',
        ['moby login: ', 'djs55'],
        ['djs55@moby:~$ ', 'git log --author=djs55 --since=2015 > timeline'],
        ['djs55@moby:~$ ', 'startx ./timeline'],
        '',
        'X.Org X Server 1.21.1.8',
        'X Protocol Version 11, Revision 0',
        '(==) Log file: "/home/djs55/.local/share/xorg/Xorg.0.log"'
      ]
    },
    dos: {
      exit: [['blank', 600]], sync: true, delay: 60,
      lines: [
        'Starting MS-DOS...',
        '',
        'HIMEM is testing extended memory...done.',
        '',
        ['C:\\>', 'hyperv /start linuxkit'],
        ['C:\\>', 'vpnkit /ethernet /dns'],
        ['C:\\>', 'grpcfuse /share C:\\USERS'],
        ['C:\\>', 'git log --author=djs55 --since=2015'],
        ['C:\\>', 'win']
      ]
    },
    aliens: {
      exit: [['roll', 800], ['blank', 140]], sync: true,
      lines: [
        '[    0.000000] hyperkit: starting LinuxKit VM, 2 vCPUs',
        '[    0.081234] virtio-blk: qcow2 disk attached (thin-provisioned, 64 GiB)',
        '[    0.112090] irmin: watching VM configuration',
        '[    0.204511] vpnkit: ethernet frames <-> host sockets',
        '[    0.231877] vpnkit: DNS forwarding via host resolver',
        '[    0.415001] grpcfuse: sharing /Users',
        '[    0.733420] dockerd: API listening on /var/run/docker.sock',
        '[    0.901337] resource-saver: will pause VM when idle',
        '',
        '$ git log --author=djs55 --since=2015'
      ]
    }
  };
  var name = (m && m[1]) || boot.getAttribute('data-style');
  var style = STYLES[name] || STYLES.x11;
  if (!STYLES[name]) name = 'x11';
  var key = 'timeline-booted:' + location.pathname, seen = null;
  try { seen = sessionStorage.getItem(key); } catch (e) {}
  if (m) seen = null;
  if (reduce || seen) { boot.remove(); return; }
  try { sessionStorage.setItem(key, '1'); } catch (e) {}

  boot.className = name;
  var pre = boot.querySelector('pre'), cur = document.createElement('span'), i = 0, finished = false;
  cur.className = 'cursor';
  function finish() {
    if (finished) return; finished = true;
    var phases = style.exit.slice();
    (function step() {
      var p = phases.shift();
      if (p) {
        if (p[0] === 'roll') { var ghost = pre.cloneNode(true); ghost.classList.add('ghost'); boot.appendChild(ghost); }
        boot.className = name + ' ' + p[0]; setTimeout(step, p[1]); return;
      }
      boot.remove();
      if (style.sync) {
        document.documentElement.classList.add('boot-sync');
        setTimeout(function () { document.documentElement.classList.remove('boot-sync'); }, 320);
      }
    })();
  }
  function html(t) {
    t = t.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    return t.replace('[  OK  ]', '[<span class="ok">  OK  </span>]');
  }
  // commands are typed a character at a time after their prompt
  function type(text, done) {
    var j = 0;
    pre.appendChild(cur);
    (function tick() {
      if (finished) return;
      if (j < text.length) { cur.insertAdjacentText('beforebegin', text[j++]); setTimeout(tick, 10 + Math.random() * 14); }
      else setTimeout(function () { cur.remove(); done(); }, 90);
    })();
  }
  (function next() {
    if (finished) return;
    if (i >= style.lines.length) { finish(); return; }
    var line = style.lines[i++], last = i === style.lines.length, d = style.delay || 110;
    function after() {
      if (last) pre.appendChild(cur); else pre.insertAdjacentText('beforeend', '\n');
      var wait = last ? 450 : !line ? 40 : /^\[\s+\d/.test(line) ? d * 0.5 : d + Math.random() * d;
      setTimeout(next, wait);
    }
    if (Array.isArray(line)) { pre.insertAdjacentHTML('beforeend', html(line[0])); type(line[1], after); }
    else { pre.insertAdjacentHTML('beforeend', html(line)); after(); }
  })();
  boot.addEventListener('click', finish);
  document.addEventListener('keydown', finish, { once: true });
}
"""



def main():
    d = load()
    LIVE.write_text(render_a(d, boot=True, title="Dave Scott: Docker timeline"))
    n = sum(len(y["articles"]) for y in d["years"])
    print(f"built {LIVE.name} from {len(d['years'])} years, {n} entries")
    for y in d["years"]:
        for a in y["articles"]:
            print(f'  {y["year"]}  {strip_tags(a["title"])[:58]:58}  {" ".join(a["tags"])}')


if __name__ == "__main__":
    main()
