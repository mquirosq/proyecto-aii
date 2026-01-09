from django.shortcuts import render
from django.contrib import messages
from .models import Course
from .populateDB import populate_database

# Create your views here.
def home(request):
    return render(request, 'main/home.html')

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
        messages.success(request, 'Scrapers ejecutados. Revisa la salida en la consola.')
        return render(request, 'main/populate_done.html')

    return render(request, 'main/populate.html')