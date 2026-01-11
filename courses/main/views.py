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
from .recommender import recommend_hybrid, recommend_for_anonymous
from .recommender_utils import precalculate_data
from whoosh.query import Term, And, NumericRange, Or
from scrapping.utils import extract_keywords
from datetime import datetime, timedelta

# Create your views here.
def home(request):
    categories = Category.objects.all()
    recommended_courses = []
    if request.user.is_authenticated:
        recommended_courses = recommend_hybrid(request.user, limit=6)
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
                    score_map = {hit['url']: hit.score for hit in hits}
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

@user_passes_test(lambda u: u.is_staff)
def load_recommender_data(request):
    if not request.user.is_staff:
        messages.error(request, 'No tienes permiso para acceder a esta página.')
        return redirect('home')

    if request.method == 'POST':
        precalculate_data()
        messages.success(request, 'Datos del sistema de recomendación cargados correctamente.')
        return redirect('admin_panel')

    return render(request, 'main/load_recommender_confirm.html')

def generate_match_reasons_details(base_course, candidate):
    """Return textual reasons explaining similarity for course details."""
    
    reasons = []
    
    if base_course.instructor and candidate.instructor and base_course.instructor.id == candidate.instructor.id:
        reasons.append('mismo instructor')
    
    if base_course.platform and candidate.platform and base_course.platform.id == candidate.platform.id:
        reasons.append('misma plataforma')
    
    if getattr(base_course, 'category_id', None) and getattr(candidate, 'category_id', None) and base_course.category_id == candidate.category_id:
        reasons.append('misma categoría')
    
    if getattr(base_course, 'level', None) and getattr(candidate, 'level', None) and base_course.level == candidate.level:
        reasons.append('mismo nivel')
    
    if getattr(base_course, 'duration', None) and getattr(candidate, 'duration', None):
        diff = abs(float(candidate.duration) - float(base_course.duration))
        if diff == 0:
            reasons.append('duración idéntica')
        elif diff <= 5:
            reasons.append('duración similar')
    
    if getattr(base_course, 'rating', None) and getattr(candidate, 'rating', None):
        rating_diff = abs(float(candidate.rating) - float(base_course.rating))
        if rating_diff <= 0.5:
            reasons.append('puntuación similar')

    base_course.keywords = extract_keywords(base_course.title, base_course.description)
    candidate.keywords = extract_keywords(candidate.title, candidate.description)

    if getattr(base_course, 'keywords', None) and getattr(candidate, 'keywords', None):
        base_keywords = set(kw.strip().lower() for kw in (base_course.keywords or '') if kw.strip())
        candidate_keywords = set(kw.strip().lower() for kw in (candidate.keywords or '') if kw.strip())
        common_keywords = base_keywords.intersection(candidate_keywords)
        
        if common_keywords:
            reasons.append(f'palabras clave en común (' + ', '.join(sorted(common_keywords)) + ')')

    return ', '.join(reasons) if reasons else ''

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

    similar_courses = similar_courses_given_course(course)

    next_courses = next_steps_given_course(course)

    return render(request, 'main/course_detail.html', {
        'course': course,
        'similar_courses': similar_courses,
        'next_courses': next_courses
    })

# Note the minscore from Whoosh may eliminate results that are slightly similar as they are not deemed relevant enough.

def similar_courses_given_course(course):
    """
    Return a list of similar courses to the given course using Whoosh search.
    Get courses with similar level, category, instructor, platform, duration of +- 5 hours,
    similar keywords, rating of +- 0.5.
    """
    ix = open_whoosh()
    similar_courses = Course.objects.none()
    if ix:
        try:
            with ix.searcher() as searcher:
                query_parts = []

                # Duration ±5
                if getattr(course, 'duration', None) is not None:
                    dur = float(course.duration)
                    query_parts.append(NumericRange('duration', dur - 5, dur + 5, boost=2.5))

                # Rating ±0.5
                if getattr(course, 'rating', None) is not None:
                    r = float(course.rating)
                    query_parts.append(NumericRange('rating', r - 0.5, r + 0.5, boost=1))

                # Level
                if getattr(course, 'level', None):
                    query_parts.append(Term('level', course.level.lower(), boost=2.0))

                # Instructor name
                instr_name = None
                if getattr(course, 'instructor', None):
                    instr_name = getattr(course.instructor, 'name', None) or str(course.instructor)
                if instr_name:
                    query_parts.append(Term('instructor', instr_name.lower(), boost=2.0))

                # Platform name
                platform_name = None
                if getattr(course, 'platform', None):
                    platform_name = getattr(course.platform, 'name', None) or str(course.platform)
                if platform_name:
                    query_parts.append(Term('platform', platform_name.lower(), boost=1))

                # Category name
                cat_name = None
                if getattr(course, 'category', None):
                    cat_name = getattr(course.category, 'name', None) or str(course.category)
                if cat_name:
                    query_parts.append(Term('category', cat_name.lower(), boost=5.0))

                # Keywords
                keywords = extract_keywords(course.title, course.description)
                keyword_boost = 5.0
                keyword_terms = [Term('keywords', kw.strip().lower(), boost=keyword_boost) for kw in keywords if kw.strip()]
                
                # Build final query
                final_query = None
                all_parts = []
                if query_parts:
                    all_parts.extend(query_parts)
                if keyword_terms:
                    all_parts.extend(keyword_terms)
                if all_parts:
                    final_query = Or(all_parts)

                if final_query is None:
                    similar_courses = Course.objects.none()
                else:
                    results = searcher.search(final_query, limit=4)

                    similar_list = []
                    seen = set()
                    for hit in results:
                        url = hit.get('url')
                        if not url or url in seen:
                            continue
                        seen.add(url)
                        c = Course.objects.filter(url=url).first()
                        if not c:
                            continue
                        if c.id == course.id:
                            continue

                        setattr(c, 'match_reasons', generate_match_reasons_details(course, c))
                        similar_list.append(c)

                    # attach global rank (1 = best)
                    for idx, c in enumerate(similar_list, start=1):
                        try:
                            setattr(c, 'rank', idx)
                        except Exception:
                            pass

                    similar_courses = similar_list
        except Exception as e:
            print(f"Whoosh similar courses error: {e}")
            similar_courses = Course.objects.none()

    return similar_courses

def next_steps_given_course(course):
    """ 
    Using Whoosh, obtain courses that share keywords and category but are of higher level.
    And that have been scrapped in the last 30 days.
    """

    ix = open_whoosh()
    next_courses = Course.objects.none()

    with ix.searcher() as searcher:
        query_parts = []

        # Category name
        cat_name = None
        if getattr(course, 'category', None):
            cat_name = getattr(course.category, 'name', None) or str(course.category)
        if cat_name:
            query_parts.append(Term('category', cat_name.lower()))

        # Keywords
        keywords = extract_keywords(course.title, course.description)
        keyword_boost = 2.0 / len(keywords) if keywords else 1.0
        keyword_terms = [Term('keywords', kw.strip().lower(), boost=keyword_boost) for kw in keywords if kw.strip()]

        # Level higher than current course
        level_order = {'beginner': 1, 'intermediate': 2, 'advanced': 3}
        current_level_value = level_order.get((course.level or '').lower(), 0)
        higher_levels = [lvl for lvl, val in level_order.items() if val > current_level_value]
        level_terms = [Term('level', lvl) for lvl in higher_levels]

        # Last scraped in the last 30 days
        thirty_days_ago = datetime.now() - timedelta(days=30)
        query_parts.append(NumericRange('last_scraped', thirty_days_ago.timestamp(), None))

        # Build final query
        final_query = None
        all_parts = []
        if query_parts:
            all_parts.extend(And(query_parts))
        if keyword_terms:
            all_parts.append(Or(keyword_terms))
        if level_terms:
            all_parts.append(Or(level_terms))
        
        if all_parts:
            final_query = And(all_parts)

        if final_query is None:
            next_courses = Course.objects.none()
        else:
            results = searcher.search(final_query, limit=3)

            next_list = []
            seen = set()
            for hit in results:
                url_c = hit.get('url')
                if not url_c or url_c in seen:
                    continue
                seen.add(url_c)
                c = Course.objects.filter(url=url_c).first()
                if not c:
                    continue
                if c.id == course.id:
                    continue
                next_list.append(c)

            next_courses = next_list
    return next_courses

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

