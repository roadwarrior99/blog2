/**
 * slideshow.js — reusable auto-advancing image slideshow.
 *
 * Usage: add class="slideshow" to any wrapper element that contains:
 *   .ss-wrap   — the visible viewport (clips the slides)
 *   .ss-slide  — one per image (first has opacity:1, rest opacity:0)
 *   .ss-bar    — the progress bar fill element
 *   .ss-dots   — empty container; dots are built at runtime
 *   [data-ss-dir="-1"] / [data-ss-dir="1"] — prev/next buttons
 *
 * Optional attribute on the wrapper:
 *   data-interval="4000"  — auto-advance interval in ms (default 4000)
 *
 * Multiple slideshows on one page are fully independent.
 */
(function () {
  function initSlideshow(root) {
    var interval = parseInt(root.getAttribute('data-interval') || '4000', 10);
    var wrap   = root.querySelector('.ss-wrap');
    var slides = root.querySelectorAll('.ss-slide');
    var bar    = root.querySelector('.ss-bar');
    var dotsEl = root.querySelector('.ss-dots');
    var cur = 0, timer = null;

    if (!slides.length || !bar || !dotsEl) return;

    // Build navigation dots
    slides.forEach(function (_, i) {
      var d = document.createElement('div');
      d.style.cssText = 'width:8px;height:8px;border-radius:50%;cursor:pointer;background:'
                      + (i === 0 ? '#aaa' : '#444') + ';';
      d.addEventListener('click', function () { go(i); });
      dotsEl.appendChild(d);
    });

    function getDots() { return dotsEl.querySelectorAll('div'); }

    function go(n) {
      slides[cur].style.opacity = '0';
      getDots()[cur].style.background = '#444';
      cur = (n + slides.length) % slides.length;
      slides[cur].style.opacity = '1';
      getDots()[cur].style.background = '#aaa';
      resetBar();
    }

    function resetBar() {
      clearTimeout(timer);
      bar.style.transition = 'none';
      bar.style.width = '0%';
      bar.offsetWidth; // force reflow so the transition restart is visible
      bar.style.transition = 'width ' + interval + 'ms linear';
      bar.style.width = '100%';
      timer = setTimeout(function () { go(cur + 1); }, interval);
    }

    // Wire up prev/next buttons inside this slideshow
    root.querySelectorAll('[data-ss-dir]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        go(cur + parseInt(btn.getAttribute('data-ss-dir'), 10));
      });
    });

    // Pause on hover
    if (wrap) {
      wrap.addEventListener('mouseenter', function () {
        clearTimeout(timer);
        bar.style.transition = 'none';
      });
      wrap.addEventListener('mouseleave', resetBar);
    }

    // Keyboard navigation (arrow keys work when any slideshow is on the page;
    // if there are multiple, all advance together — acceptable trade-off)
    document.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowLeft')  go(cur - 1);
      if (e.key === 'ArrowRight') go(cur + 1);
    });

    resetBar();
  }

  function initAll() {
    document.querySelectorAll('.slideshow').forEach(initSlideshow);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAll);
  } else {
    initAll();
  }
})();

// Photo gallery driver for posts that embed the alb-* id pattern.
// Exposes window.albNav(dir) called by onclick attributes in post bodies.
(function () {
  var albSlides, albCur = 0, albTimer = null;
  var ALB_INTERVAL = 4000;

  function albInit() {
    var wrap = document.getElementById('alb-wrap');
    if (!wrap) return;

    albSlides = wrap.querySelectorAll('.alb-slide');
    if (!albSlides.length) return;

    var dotsEl = document.getElementById('alb-dots');
    if (dotsEl) {
      Array.prototype.forEach.call(albSlides, function (_, i) {
        var d = document.createElement('div');
        d.style.cssText = 'width:8px;height:8px;border-radius:50%;cursor:pointer;background:'
                        + (i === 0 ? '#aaa' : '#444') + ';';
        d.addEventListener('click', function () { albGo(i); });
        dotsEl.appendChild(d);
      });
    }

    albResetBar();
  }

  function albGo(n) {
    var dotsEl = document.getElementById('alb-dots');
    var dots = dotsEl ? dotsEl.querySelectorAll('div') : [];
    albSlides[albCur].style.opacity = '0';
    if (dots[albCur]) dots[albCur].style.background = '#444';
    albCur = (n + albSlides.length) % albSlides.length;
    albSlides[albCur].style.opacity = '1';
    if (dots[albCur]) dots[albCur].style.background = '#aaa';
    albResetBar();
  }

  function albResetBar() {
    var bar = document.getElementById('alb-bar');
    if (!bar) return;
    clearTimeout(albTimer);
    bar.style.transition = 'none';
    bar.style.width = '0%';
    bar.offsetWidth; // force reflow so transition restarts visibly
    bar.style.transition = 'width ' + ALB_INTERVAL + 'ms linear';
    bar.style.width = '100%';
    albTimer = setTimeout(function () { albGo(albCur + 1); }, ALB_INTERVAL);
  }

  window.albNav = function (dir) { albGo(albCur + dir); };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', albInit);
  } else {
    albInit();
  }
})();
