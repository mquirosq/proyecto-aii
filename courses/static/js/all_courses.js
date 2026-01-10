document.addEventListener('DOMContentLoaded', function () {
    var orderSelect = document.getElementById('order-select');
    if (orderSelect) orderSelect.addEventListener('change', function () { if (this.form) this.form.submit(); });

    document.addEventListener('click', function (e) {
        var btn = e.target.closest && e.target.closest('.ajax-feedback-btn');
        if (!btn) return;
        e.preventDefault();
        var form = btn.closest('form.ajax-feedback');
        if (form) sendFeedback(form, btn);
    });
});

function sendFeedback(form, btn) {
    var button = btn || form.querySelector('.ajax-feedback-btn');
    if (button) button.disabled = true;

    var fd = new FormData(form);
    fd.append('ajax', '1');

    fetch(form.action, { method: 'POST', body: fd, credentials: 'same-origin' })
        .then(function (resp) {
            if (!resp.ok) return resp.text().then(function (t) { throw new Error('Server error ' + resp.status + ': ' + t); });
            return resp.json();
        })
        .then(function (data) {
            var card = form.closest('.card') || document;
            var likeBtn = card.querySelector('form[data-action="like"] .ajax-feedback-btn');
            var dislikeBtn = card.querySelector('form[data-action="dislike"] .ajax-feedback-btn');

            if (likeBtn) {
                likeBtn.classList.toggle('btn-success', !!data.liked);
                likeBtn.classList.toggle('btn-outline-secondary', !data.liked);
                likeBtn.setAttribute('aria-pressed', !!data.liked);
            }
            if (dislikeBtn) {
                dislikeBtn.classList.toggle('btn-danger', !!data.disliked);
                dislikeBtn.classList.toggle('btn-outline-secondary', !data.disliked);
                dislikeBtn.setAttribute('aria-pressed', !!data.disliked);
            }
        })
        .catch(function (err) { console.error('Feedback failed:', err); })
        .finally(function () { if (button) button.disabled = false; });
}

window.handleFeedback = function(button){
    try{
        if(!button) return false;
        var form = button.closest && button.closest('form.ajax-feedback');
        if(!form) return false;
        sendFeedback(form, button);
        return false;
    }catch(e){ console.error(e); return false; }
};
