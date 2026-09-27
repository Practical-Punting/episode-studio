// Practical Punting video-card animation engine
// ppInit(spec[, extra]) is called by each card page. Controls exposed on window:
//   ppDuration      total animation length in ms
//   ppPlay() / ppPause() / ppRestart()
//   ppSeek(ms)      pause and jump every animation to absolute time ms (frame-accurate)
//   ppTime()        the timeline position the page is currently showing, in ms
//   ppPaint()       re-run every driver against the current timeline position
//   ?paused=1       load holding the first frame (t=0)
//
// ───────────────────────────────────────────────────────────────────────────────
// 🔴 THE SEEK-VERSUS-PLAY TRAP — read this before you add a Count, Fill or Travel.
//
// render_card.py does NOT play a card. It calls ppSeek(t) and screenshots, t by t.
// So anything animated by requestAnimationFrame, setTimeout, setInterval or
// Date.now() looks perfect in a browser and renders WRONG — seeking does not
// advance a wall clock, so every captured frame shows a stuck or arbitrary value.
//
// The rule: A VALUE ON SCREEN MUST BE A FUNCTION OF THE TIMELINE, NEVER OF A CLOCK.
// Drivers below read their position from a real WAAPI animation's own currentTime,
// which ppSeek sets. The rAF loop in ppPlay is only a REPAINT PUMP for live
// preview; it supplies no time of its own. That is why sought frames and played
// frames agree by construction rather than by luck.
// ───────────────────────────────────────────────────────────────────────────────
(function(){
  var anims = [];      // every animation, incl. driver clocks: seek/play/pause/restart act on all
  var drivers = [];    // fn(tMs) — called after every ppSeek, and each frame during ppPlay
  var rafId = null;

  function clamp01(x){ return x < 0 ? 0 : (x > 1 ? 1 : x); }

  // A driver's CLOCK: a real animation carrying this driver's own delay/duration/
  // easing. Its eased position is read back as a number, so the easing curve comes
  // for free and the value is pinned to the same timeline as every other element.
  function makeClock(opts){
    var el = document.createElement('span');
    el.setAttribute('aria-hidden', 'true');
    el.style.cssText = 'position:absolute;left:-9999px;top:0;width:0;height:0;' +
                       'overflow:hidden;pointer-events:none;visibility:hidden';
    document.body.appendChild(el);
    var a = el.animate([{opacity:0},{opacity:1}], Object.assign({fill:'both'}, opts));
    return {anim: a, read: function(){
      return clamp01(parseFloat(getComputedStyle(el).opacity) || 0);
    }};
  }

  // COUNT — a number climbing to its value, driven off the timeline.
  //
  // TWO MODES, ONE CLOCK:
  //   smooth — {from, to}: interpolates, and inherits the entry's easing for free,
  //            because the eased position is READ BACK off a real animation.
  //   ledger — {from, stops:[...]}: TICKS through the given cumulative values, one
  //            per segment of the clock. A points ledger must only ever show a total
  //            the ledger actually reaches; a smooth slide would put numbers on
  //            screen that are not the sum of the rows showing beside them.
  function makeCount(entry, target){
    var c     = entry.count;
    var opts  = entry.opts || {};
    var from  = +c.from || 0;
    var dec   = c.decimals == null ? 0 : +c.decimals;
    var pre   = c.prefix == null ? '' : String(c.prefix);
    var suf   = c.suffix == null ? '' : String(c.suffix);
    var sign  = !!c.sign;            // force a leading + on positives (points ledgers)
    var stops = c.stops || null;
    var to    = stops ? +stops[stops.length - 1] : (+c.to || 0);
    var clock = makeClock(opts);
    var delay = +opts.delay || 0;
    var dur   = +opts.duration || 0;
    var seg   = stops ? (c.segment != null ? +c.segment : dur / stops.length) : 0;

    function value(){
      if (!stops) return from + (to - from) * clock.read();
      // Stepped: read ABSOLUTE time off the clock, so which stop we are on is a
      // plain fact about the timeline and not a guess from an eased progress.
      var t = clock.anim.currentTime;
      if (t === null || t === undefined) t = 0;
      var idx = Math.floor((t - delay) / (seg || 1));
      if (idx < 0) return from;
      return +stops[idx < stops.length ? idx : stops.length - 1];
    }
    return {
      anim: clock.anim,
      paint: function(){
        var v = value();
        var s = v.toFixed(dec);
        if (sign && v >= 0) s = '+' + s;
        target.textContent = pre + s + suf;
      }
    };
  }

  window.ppInit = function(spec, extra){
    function boot(){
      spec.forEach(function(s){
        var el = document.querySelector(s.sel);
        if (!el) return;
        if (s.count){
          var d = makeCount(s, el);
          anims.push(d.anim);
          drivers.push(d.paint);
        } else {
          anims.push(el.animate(s.kf, Object.assign({fill:'both'}, s.opts)));
        }
      });
      if (extra && extra.drivers) extra.drivers.forEach(function(fn){ drivers.push(fn); });
      window.ppDuration = spec.reduce(function(m,s){ return Math.max(m,(s.opts.delay||0)+s.opts.duration); },0);
      // THE SPEC ITSELF, so a gate can measure the BUILD rather than infer it.
      // ppDuration includes the LOGO, which lands after the card is made, so it
      // is not the build time and card_check must not use it as one.
      window.ppSpec = spec;
      window.ppBuildMs = spec.reduce(function(m,s){
        if ((s.sel||'').indexOf('#logo') >= 0) return m;
        return Math.max(m,(s.opts.delay||0)+s.opts.duration); },0);
      // Paint once at boot so a driven value is never blank before the first seek.
      paint();
      if (new URLSearchParams(location.search).has('paused')) window.ppSeek(0);
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
  };

  function paint(){
    var t = window.ppTime();
    for (var i = 0; i < drivers.length; i++) drivers[i](t);
  }
  function tick(){ paint(); rafId = requestAnimationFrame(tick); }
  function startPump(){ if (rafId == null){ paint(); rafId = requestAnimationFrame(tick); } }
  function stopPump(){ if (rafId != null){ cancelAnimationFrame(rafId); rafId = null; } }

  window.ppTime  = function(){ return anims.length ? (anims[0].currentTime || 0) : 0; };
  window.ppPaint = paint;
  window.ppSeek  = function(ms){ stopPump(); anims.forEach(function(a){ a.pause(); a.currentTime = ms; }); paint(); };
  window.ppPlay  = function(){ anims.forEach(function(a){ a.play(); }); startPump(); };
  window.ppPause = function(){ anims.forEach(function(a){ a.pause(); }); stopPump(); paint(); };
  window.ppRestart = function(){ anims.forEach(function(a){ a.currentTime = 0; a.play(); }); startPump(); };
})();
