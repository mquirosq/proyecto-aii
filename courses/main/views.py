from django.shortcuts import render
from django.contrib import messages
from .models import Course, Category
from .populateDB import populate_database
from .populateDB import open_whoosh
from whoosh.qparser import MultifieldParser
from whoosh import scoring
from whoosh.qparser import OrGroup

# Create your views here.
def home(request):
    categories = Category.objects.all()
    return render(request, 'main/home.html', {'categories': categories})

def all_courses(request):
    courses = Course.objects.all()
    return render(request, 'main/all_courses.html', {'courses': courses})

def populate_with_data(request):
    if request.method == 'POST':
        selected_scrapers = request.POST.getlist('scrapers')
        if not selected_scrapers:
            messages.error(request, 'Selecciona al menos un scraper antes de ejecutar.')
            return render(request, 'main/populate.html')

        populate_database(selected_scrapers)
        return render(request, 'main/populate_done.html', {'scrapers': selected_scrapers, 'total_courses': Course.objects.count()}  )

    return render(request, 'main/populate.html')

def course_detail(request, course_id):
    try:
        course = Course.objects.get(id=course_id)
    except Course.DoesNotExist:
        messages.error(request, 'El curso solicitado no existe.')
        return render(request, 'main/course_not_found.html')

    return render(request, 'main/course_detail.html', {'course': course})

def about(request):
    return render(request, 'main/about.html')

def search(request):
    query = request.GET.get('q', '').strip()
    results = []
    total_courses = Course.objects.count()

    if query:
        ix = open_whoosh()
        try:
            with ix.searcher(weighting=scoring.BM25F()) as searcher:
                parser = MultifieldParser(['title', 'description', 'keywords'], ix.schema, group=OrGroup)
                qobj = parser.parse(query)
                hits = searcher.search(qobj, limit=50)
                for hit in hits:
                    url = hit.get('url')
                    course_obj = Course.objects.filter(url=url).first()
                    if course_obj:
                        results.append({'course': course_obj, 'score': getattr(hit, 'score', None)})
        except Exception:
            results = []

    return render(request, 'main/search_results.html', {'query': query, 'results': results, 'total_courses': total_courses})