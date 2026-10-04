/* Site-wide theme cycler: auto -> light -> dark.
   Include synchronously in <head> (after theme.css) so the stored
   preference is applied before first paint. Click handling is
   delegated, so the button can appear anywhere in the page. */
(function () {
  var root = document.documentElement;
  var modes = ['auto', 'light', 'dark'];
  function store(val) {
    try {
      if (val === undefined) return localStorage.getItem('theme') || localStorage.getItem('timeline-theme');
      localStorage.setItem('theme', val);
    } catch (e) { return null; }
  }
  var mode = store() || 'auto';
  if (modes.indexOf(mode) < 0) mode = 'auto';
  apply(mode);
  document.addEventListener('DOMContentLoaded', function () { apply(mode); });
  function apply(m) {
    if (m === 'auto') root.removeAttribute('data-theme');
    else root.setAttribute('data-theme', m);
    var btn = document.getElementById('theme');
    if (btn) btn.textContent = 'theme: ' + m;
  }
  document.addEventListener('click', function (e) {
    var btn = e.target && e.target.closest ? e.target.closest('.theme-toggle') : null;
    if (!btn) return;
    mode = modes[(modes.indexOf(mode) + 1) % 3];
    store(mode);
    apply(mode);
  });
}());
