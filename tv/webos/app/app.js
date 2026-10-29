// ES5 only: webOS 5 runs an old Chromium (about 68). No arrows, async or ?.
(function () {
  var cfg = {};
  var key;
  var defaults = window.ATHAN_TV_CONFIG || {};
  for (key in defaults) { cfg[key] = defaults[key]; }

  // Overrides: launch params (ares-launch -p) first, then the query string.
  var sys = window.webOSSystem || window.PalmSystem;
  try {
    var lp = sys && sys.launchParams ? JSON.parse(sys.launchParams) : {};
    for (key in lp) { if (lp[key]) { cfg[key] = lp[key]; } }
  } catch (e) {}
  location.search.replace(/[?&]([^=&]+)=([^&]*)/g, function (m, k, v) {
    cfg[decodeURIComponent(k)] = decodeURIComponent(v);
  });

  var origin = (String(cfg.url).match(/^https?:\/\/[^\/?#]+/) || [""])[0];
  var retryMs = (Number(cfg.retrySeconds) || 15) * 1000;
  var status = document.getElementById("status");
  var frame = null;
  var timer = null;

  // Keeps the app resident if webOS offers it. The screen saver is a TV setting.
  try { if (sys && sys.keepAlive) { sys.keepAlive(true); } } catch (e) {}

  function setStatus(text, hint) {
    status.innerHTML = "";
    status.appendChild(document.createTextNode(text));
    if (hint) {
      var small = document.createElement("small");
      small.appendChild(document.createTextNode(hint));
      status.appendChild(small);
    }
    status.style.display = "block";
  }

  function showError() {
    setStatus("Can't reach Home Assistant at " + origin + ", retrying",
      "Trying again every " + retryMs / 1000 + " seconds. Press Back to retry now.");
    clearTimeout(timer);
    timer = setTimeout(start, retryMs);
  }

  // A no-cors fetch resolves (opaque) when the host answers and rejects when
  // it is unreachable, so Home Assistant needs no CORS headers for this.
  function ping(ok, fail) {
    var done = false;
    var t = setTimeout(function () { if (!done) { done = true; fail(); } }, 5000);
    function finish(cb) {
      return function () { if (!done) { done = true; clearTimeout(t); cb(); } };
    }
    fetch(origin + "/manifest.json?_=" + new Date().getTime(), { mode: "no-cors", cache: "no-store" })
      .then(finish(ok), finish(fail));
  }

  function show() {
    if (cfg.mode === "iframe") {
      status.style.display = "none";
      if (!frame) {
        frame = document.createElement("iframe");
        document.body.appendChild(frame);
      }
      frame.src = cfg.url;
    } else {
      location.replace(cfg.url);
    }
  }

  function start() {
    clearTimeout(timer);
    if (!origin) {
      setStatus("No dashboard URL configured", "Set url in config.js and rebuild.");
      return;
    }
    ping(show, showError);
  }

  // Back (461) would otherwise leave the app; retry or reload instead.
  document.addEventListener("keydown", function (e) {
    if (e.keyCode === 461) {
      e.preventDefault();
      start();
    }
  });

  start();
})();
