from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import login
from .forms import SignUpForm
from .models import Course, Category, Platform, Instructor, UserCourse
from django.db.models import Count, Avg, Q, Case, When
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .populateDB import populate_database
from .populateDB import open_whoosh
from whoosh.qparser import MultifieldParser
from whoosh.qparser import OrGroup
from .recommender_content import recommend_courses, recommend_for_anonymous


# Create your views here.
def home(request):
    categories = Category.objects.all()
    recommended_courses = []
    if request.user.is_authenticated:
        recommended_courses = recommend_courses(request.user, limit=6)
    else:
        recommended_courses = recommend_for_anonymous(limit=6)
    
    return render(request, 'main/home.html', {'categories': categories, 'recommended_courses': recommended_courses})

def all_courses(request):
    base_qs = Course.objects.select_related('platform', 'instructor').all()
    
    # Get values
    query = request.GET.get('q', '').strip()
    platform_id = request.GET.get('platform', '').strip()
    category_id = request.GET.get('category', '').strip()
    level = request.GET.get('level', '').strip()
    instructor_id = request.GET.get('instructor', '').strip()
    duration = request.GET.get('duration', '').strip()
    rating = request.GET.get('rating', '').strip()
    order = request.GET.get('order', '').strip()
    
    # Whoosh search
    used_whoosh = False
    urls_order = []
    score_map = {}
    qs = base_qs

    if query:
        ix = open_whoosh()
        if ix:
            try:
                with ix.searcher() as searcher:
                    field_weights = {
                        'title': 2.0,
                        'keywords': 1.5,
                        'description': 1.0,
                    }
                    parser = MultifieldParser(['title', 'description', 'keywords'], schema=ix.schema, group=OrGroup, fieldboosts=field_weights)
                    qobj = parser.parse(query)
                    hits = searcher.search(qobj, limit=100)
                    urls_order = [hit['url'] for hit in hits]
                    score_map = {hit['url']: getattr(hit, 'score', None) for hit in hits}
                    used_whoosh = True
                    if urls_order:
                        qs = qs.filter(url__in=urls_order)
                    else:
                        qs = Course.objects.none()
            except Exception as e:
                print(f"Whoosh search error: {e}")
                qs = base_qs.filter(Q(title__icontains=query) | Q(description__icontains=query))
        else:
            qs = base_qs.filter(Q(title__icontains=query) | Q(description__icontains=query))

    # Filters
    if platform_id and platform_id.isdigit():
        qs = qs.filter(platform__id=int(platform_id))
    if category_id:
        if category_id == 'none':
            qs = qs.filter(category__isnull=True)
        elif category_id.isdigit():
            qs = qs.filter(category__id=int(category_id))
    if level:
        qs = qs.filter(level=level)
    if instructor_id:
        if instructor_id == 'none':
            qs = qs.filter(instructor__isnull=True)
        elif instructor_id.isdigit():
            qs = qs.filter(instructor__id=int(instructor_id))
    
    # Range maps for duration and rating
    duration_map = {
        '<5': Q(duration__lt=5),
        '5-10': Q(duration__gte=5, duration__lte=10),
        '10-50': Q(duration__gt=10, duration__lte=50),
        '>50': Q(duration__gt=50),
    }
    rating_map = {
        '<3': Q(rating__lt=3),
        '3-4': Q(rating__gte=3, rating__lt=4),
        '4-4.5': Q(rating__gte=4, rating__lt=4.5),
        '>4.5': Q(rating__gte=4.5),
    }
    if duration in duration_map:
        qs = qs.filter(duration_map[duration])
    if rating in rating_map:
        qs = qs.filter(rating_map[rating])

    # Ordering
    allowed_orders = {
        'title', '-title', 'duration', '-duration', 'rating', '-rating',
        'platform__name', '-platform__name', 'instructor__name', '-instructor__name'
    }
    if order in allowed_orders:
        qs = qs.order_by(order)
    elif query and used_whoosh and urls_order:
        whens = [When(url=u, then=pos) for pos, u in enumerate(urls_order)]
        qs = qs.annotate(search_order=Case(*whens)).order_by('search_order')

    # Pagination
    paginator = Paginator(qs, 10)
    page = request.GET.get('page', 1)
    try:
        courses_page = paginator.page(page)
    except (PageNotAnInteger, EmptyPage):
        courses_page = paginator.page(1)

    # Attach Whoosh score
    for c in courses_page.object_list:
        setattr(c, 'search_score', score_map.get(c.url))

    # Attach user feedback flags if authenticated
    if request.user.is_authenticated:
        for c in courses_page.object_list:
            uc = UserCourse.objects.filter(user=request.user, course=c).first()
            setattr(c, 'is_liked', bool(uc and uc.liked))
            setattr(c, 'is_disliked', bool(uc and uc.disliked))
    else:
        for c in courses_page.object_list:
            setattr(c, 'is_liked', False)
            setattr(c, 'is_disliked', False)

    context = {
        'courses': courses_page,
        'paginator': paginator,
        'platforms': Platform.objects.all(),
        'categories': Category.objects.all(),
        'levels': [lvl[0] for lvl in Course.LEVEL_CHOICES],
        'instructors': Instructor.objects.all(),
        'orders': [
            ('', 'Por defecto'), ('title', 'Título ↑'), ('-title', 'Título ↓'),
            ('duration', 'Duración ↑'), ('-duration', 'Duración ↓'),
            ('rating', 'Puntuación ↑'), ('-rating', 'Puntuación ↓'),
            ('platform__name', 'Plataforma ↑'), ('-platform__name', 'Plataforma ↓'),
            ('instructor__name', 'Instructor ↑'), ('-instructor__name', 'Instructor ↓')
        ],
        'ratings': [('', 'Cualquiera'), ('<3', 'Menos de 3'), ('3-4', '3.0 - 3.9'),
                    ('4-4.5', '4.0 - 4.4'), ('>4.5', '4.5 o más')],
        'selected_platform': platform_id,
        'selected_category': category_id,
        'selected_level': level,
        'selected_instructor': instructor_id,
        'selected_duration': duration,
        'selected_rating': rating,
        'selected_order': order,
        'query': query,
    }

    return render(request, 'main/all_courses.html', context)

@user_passes_test(lambda u: u.is_staff)
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
    # Attach user feedback flags for template
    if request.user.is_authenticated:
        uc = UserCourse.objects.filter(user=request.user, course=course).first()
        setattr(course, 'is_liked', bool(uc and uc.liked))
        setattr(course, 'is_disliked', bool(uc and uc.disliked))
    else:
        setattr(course, 'is_liked', False)
        setattr(course, 'is_disliked', False)

    return render(request, 'main/course_detail.html', {'course': course})

def about(request):
    return render(request, 'main/about.html')


@login_required
@user_passes_test(lambda u: u.is_staff)
def admin_panel(request):
    total_courses = Course.objects.count()
    total_categories = Category.objects.count()
    total_users = 0
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        total_users = User.objects.count()
    except Exception:
        total_users = 0

    # Stats per platform
    platform_stats = Platform.objects.annotate(
        course_count=Count('course'),
        avg_rating=Avg('course__rating'),
        avg_duration=Avg('course__duration')
    ).order_by('-course_count')

    return render(request, 'main/admin_panel.html', {
        'total_courses': total_courses,
        'total_categories': total_categories,
        'total_users': total_users,
        'platform_stats': platform_stats,
    })


def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return render(request, 'main/populate_done.html', {'scrapers': [], 'total_courses': Course.objects.count()}) if user.is_staff else render(request, 'main/home.html', {'categories': Category.objects.all()})
    else:
        form = SignUpForm()

    return render(request, 'registration/signup.html', {'form': form})

from django.http import JsonResponse

@login_required
def toggle_feedback(request, course_id, action):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'auth'}, status=403)

    uc, _ = UserCourse.objects.get_or_create(
        user=request.user,
        course_id=course_id
    )

    if action == 'like':
        uc.liked = not uc.liked
        if uc.liked:
            uc.disliked = False
    elif action == 'dislike':
        uc.disliked = not uc.disliked
        if uc.disliked:
            uc.liked = False

    uc.save()

    # If this is an AJAX request, return JSON so the client can update UI without full reload
    is_ajax = (
        request.headers.get('x-requested-with') == 'XMLHttpRequest'
        or request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'
        or request.POST.get('ajax') == '1'
        or ('application/json' in (request.headers.get('Accept') or ''))
    )
    if is_ajax:
        return JsonResponse({'liked': uc.liked, 'disliked': uc.disliked})

    # For standard requests, redirect back
    return redirect(request.META.get('HTTP_REFERER', '/'))

@login_required
def mark_course_viewed(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    user_course, __ = UserCourse.objects.get_or_create(user=request.user, course=course)
    user_course.viewed = user_course.viewed + 1
    user_course.save()
    return redirect(request.META.get('HTTP_REFERER', '/'))

