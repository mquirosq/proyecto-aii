document.addEventListener('DOMContentLoaded', function() {
    var el = document.getElementById('course-detail');
    if (!el) return;
    var url = el.dataset.markViewedUrl;
    if (!url) return;

    function getCookie(name) {
        const v = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
        return v ? v.pop() : '';
    }

    var csrftoken = getCookie('csrftoken');
    if (!csrftoken) return;

    fetch(url, {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrftoken,
            'Accept': 'text/html'
        },
        credentials: 'same-origin'
    }).catch(function(){ /* ignore errors */ });
});
