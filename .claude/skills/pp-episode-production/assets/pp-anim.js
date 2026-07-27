// Practical Punting video-card animation engine
// ppInit(spec) is called by each card page. Controls exposed on window:
//   ppDuration      total animation length in ms
//   ppPlay() / ppPause() / ppRestart()
//   ppSeek(ms)      pause and jump every animation to absolute time ms (frame-accurate)
//   ?paused=1       load holding the first frame (t=0)
(function(){
  var anims = [];
  window.ppInit = function(spec){
    function boot(){
      spec.forEach(function(s){
        var el = document.querySelector(s.sel);
        if (el) anims.push(el.animate(s.kf, Object.assign({fill:'both'}, s.opts)));
      });
      window.ppDuration = spec.reduce(function(m,s){ return Math.max(m,(s.opts.delay||0)+s.opts.duration); },0);
      if (new URLSearchParams(location.search).has('paused')) window.ppSeek(0);
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
  };
  window.ppSeek = function(ms){ anims.forEach(function(a){ a.pause(); a.currentTime = ms; }); };
  window.ppPlay = function(){ anims.forEach(function(a){ a.play(); }); };
  window.ppPause = function(){ anims.forEach(function(a){ a.pause(); }); };
  window.ppRestart = function(){ anims.forEach(function(a){ a.currentTime = 0; a.play(); }); };
})();
