document.addEventListener('DOMContentLoaded', function(){
  const form = document.getElementById('populateForm');
  const runBtn = document.getElementById('runButton');
  const waiting = document.getElementById('waitingMessage');
  if(!form || !runBtn || !waiting) return;

  form.addEventListener('submit', function(e){
    try{
      // Submission proceeds; server will validate selection and show messages.
      runBtn.disabled = true;
      runBtn.classList.add('disabled');
      runBtn.textContent = 'Ejecutando...';
      // Don't disable checkboxes before submit: disabled inputs are not sent in the POST.
      // Keep the button disabled to prevent double-submits.
      waiting.style.display = 'block';
      document.body.style.cursor = 'wait'; // optional
    }catch(err){
      console.error(err);
    }
  });
});
