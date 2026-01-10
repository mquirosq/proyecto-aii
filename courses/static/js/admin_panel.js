document.addEventListener('DOMContentLoaded', function(){
  // Animar barras de progreso desde 0 hasta el valor objetivo
  function animateProgress(el, target){
    var duration = 900;
    var start = 0;
    var startTime = null;

    function step(timestamp){
      if (!startTime) startTime = timestamp;
      var progress = Math.min((timestamp - startTime) / duration, 1);
      var current = Math.round(start + (target - start) * progress);
      el.value = current;
      if (progress < 1) window.requestAnimationFrame(step);
    }
    window.requestAnimationFrame(step);
  }

  document.querySelectorAll('.platform-progress').forEach(function(p){
    var target = Number(p.dataset.target) || 0;
    setTimeout(function(){ animateProgress(p, target); }, 120);
  });

  // Modal explain
  var modal = document.getElementById('explainModal');
  var modalTitle = document.getElementById('modalTitle');
  var modalPercent = document.getElementById('modalPercent');
  var modalClose = document.getElementById('modalClose');

  function showModal(platformName, courses, total){
    modalTitle.textContent = 'Participación — ' + platformName;
    var pct = total>0 ? (courses/total*100) : 0;
    modalPercent.textContent = 'Participación: ' + pct.toFixed(2) + ' % (' + courses + ' / ' + total + ')';
    modal.setAttribute('aria-hidden','false');
  }

  document.querySelectorAll('.info-btn').forEach(function(btn){
    btn.addEventListener('click', function(e){
      var platform = btn.dataset.platform || btn.getAttribute('data-platform');
      var card = btn.closest('.platform-card');
      var prog = card ? card.querySelector('.platform-progress') : null;
      var courses = prog ? Number(prog.dataset.target) : 0;
      var total = prog ? Number(prog.dataset.total) : 0;
      showModal(platform, courses, total);
    });
  });

  modalClose.addEventListener('click', function(){ modal.setAttribute('aria-hidden','true'); });
  modal.addEventListener('click', function(e){ if(e.target===modal) modal.setAttribute('aria-hidden','true'); });
});
