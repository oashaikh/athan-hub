// Arrow-key navigation for Home Assistant on the LG TV. The Magic Remote's arrows,
// and the webostv.button arrows on the dashboard's TV page, arrive here as keydown
// events; Home Assistant's own cards already act on Enter (OK) once focused.
// Loaded on every device but only active on webOS. Chromium 68: no ?. or ??.
(function () {
  if (!/Web0S|webOS/i.test(navigator.userAgent)) return;
  var KEYS = { 37: [-1, 0], 38: [0, -1], 39: [1, 0], 40: [0, 1] };
  var SELECTOR = "a[href], button, input, select, textarea, [role=button], [role=switch], [role=tab], [tabindex]:not([tabindex='-1'])";

  var ring = document.createElement("div");
  ring.style.cssText = "position:fixed;pointer-events:none;z-index:99999;border:4px solid #ffd54f;" +
    "border-radius:14px;box-shadow:0 0 0 4px rgba(0,0,0,.45);transition:all .12s;display:none";
  document.documentElement.appendChild(ring);

  function deepActive() {
    var el = document.activeElement;
    while (el && el.shadowRoot && el.shadowRoot.activeElement) el = el.shadowRoot.activeElement;
    return el;
  }

  function contains(outer, el) {
    for (; el; el = el.parentNode || el.host) if (el === outer) return true;
    return false;
  }

  function topAt(x, y) {
    var el = document.elementFromPoint(x, y);
    while (el && el.shadowRoot) {
      var inner = el.shadowRoot.elementFromPoint(x, y);
      if (!inner || inner === el) break;
      el = inner;
    }
    return el;
  }

  // Every focusable control across shadow roots that is on screen and not covered (by a dialog).
  function candidates() {
    var out = [];
    var w = innerWidth, h = innerHeight;
    (function walk(root) {
      var all = root.querySelectorAll("*");
      for (var i = 0; i < all.length; i++) {
        var el = all[i];
        if (el.matches(SELECTOR) && !el.disabled) {
          var r = el.getBoundingClientRect();
          if (r.width > 4 && r.height > 4 && r.bottom > 0 && r.right > 0 && r.top < h && r.left < w) {
            var hit = topAt(Math.min(Math.max(r.left + r.width / 2, 1), w - 1), Math.min(Math.max(r.top + r.height / 2, 1), h - 1));
            if (hit && (contains(el, hit) || contains(hit, el))) out.push({ el: el, r: r });
          }
        }
        if (el.shadowRoot) walk(el.shadowRoot);
      }
    })(document);
    // Keep the outermost of nested matches (a card and the button inside it count once).
    return out.filter(function (c) {
      return !out.some(function (o) { return o !== c && contains(o.el, c.el) && o.el.matches("[role=button], button, a[href]"); });
    });
  }

  function show(el) {
    var r = el.getBoundingClientRect();
    ring.style.display = "block";
    ring.style.left = r.left - 6 + "px"; ring.style.top = r.top - 6 + "px";
    ring.style.width = r.width + 4 + "px"; ring.style.height = r.height + 4 + "px";
  }

  function move(dx, dy) {
    var list = candidates();
    if (!list.length) return;
    var cur = deepActive();
    var from = null;
    for (var i = 0; i < list.length; i++) if (contains(list[i].el, cur)) from = list[i];
    var best = null, bestScore = Infinity;
    if (!from) {
      list.forEach(function (c) { var s = c.r.top * 3 + c.r.left; if (s < bestScore) { bestScore = s; best = c; } });
    } else {
      var fx = from.r.left + from.r.width / 2, fy = from.r.top + from.r.height / 2;
      list.forEach(function (c) {
        if (c === from) return;
        var cx = c.r.left + c.r.width / 2, cy = c.r.top + c.r.height / 2;
        var along = (cx - fx) * dx + (cy - fy) * dy;
        if (along <= 1) return;
        var across = Math.abs((cx - fx) * dy) + Math.abs((cy - fy) * dx);
        var s = along + across * 2;
        if (s < bestScore) { bestScore = s; best = c; }
      });
    }
    if (!best) return;
    best.el.focus();
    if (best.el.scrollIntoView) best.el.scrollIntoView({ block: "nearest", inline: "nearest" });
    setTimeout(function () { show(best.el); }, 60);
  }

  addEventListener("keydown", function (e) {
    var dir = KEYS[e.keyCode];
    var t = deepActive();
    if (dir && !(t && /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName) && dir[0])) {
      e.preventDefault();
      e.stopPropagation();
      move(dir[0], dir[1]);
    } else if (e.keyCode === 461) { // Back: close a dialog or go back a page
      e.preventDefault();
      history.back();
    }
  }, true);
  addEventListener("scroll", function () { var t = deepActive(); if (t && t !== document.body) show(t); }, true);
  addEventListener("mousemove", function () { ring.style.display = "none"; }); // the pointer took over
})();
