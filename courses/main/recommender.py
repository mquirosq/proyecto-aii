from .models import Course, UserCourse
from .recommender_content import recommend_content_courses
from .recommender_colab import recommend_collaborative
from django.db.models import Sum

def recommend_for_anonymous(limit=10):
    """Recommend top-rated and most viewed courses for anonymous users."""
    qs = (
        Course.objects
        .annotate(total_views=Sum('usercourse__viewed'))
        .order_by('-rating', '-total_views')[:limit]
    )

    recs = []
    for c in qs:
        rating_score = float(getattr(c, 'rating', 0) or 0)
        views_score = float(getattr(c, 'total_views', 0) or 0)
        # Simple combined score: rating (0-5) plus a scaled views component
        score = rating_score + (views_score / 100.0)
        recs.append({'course': c, 'score': score})

    return recs

def normalize_scores(score_list):
    """Normalize a list of (object, score) tuples to a 0-1 range."""
    if not score_list:
        return []

    scores = [s for _, s in score_list]
    min_score = min(scores)
    max_score = max(scores)

    if max_score == min_score:
        return [(obj, 1.0) for obj, _ in score_list]

    normalized = [(obj, (s - min_score) / (max_score - min_score)) for obj, s in score_list]
    return normalized

def hybrid_weights():
    """
    Determine the weights for content-based and collaborative filtering based on the number of users.
    More users (with some course interaction) -> more collaborative weight.
    """
    n_users = UserCourse.objects.values('user').distinct().count()

    if n_users < 10:
        return 0.8, 0.2   # content, collaborative
    elif n_users < 50:
        return 0.6, 0.4
    else:
        return 0.4, 0.6
    
def recommend_hybrid(user, limit=10):
    """Combine content-based and collaborative filtering recommendations."""

    interactions_count = UserCourse.objects.filter(user=user).count()

    if interactions_count < 3: # Cold start - we need more data from the user
        results =recommend_for_anonymous(limit=limit + 3)
        results = [r for r in results if r['course'].id not in 
                   UserCourse.objects.filter(user=user).values_list('course_id', flat=True)]
        return results[:limit]

    content_recs = recommend_content_courses(user, limit=limit*2)
    collab_recs = recommend_collaborative(user, limit=limit*2)

    # Normalizar
    content_recs = normalize_scores([(r['course'], r['score']) for r in content_recs])
    collab_recs = normalize_scores([(r['course'], r['score']) for r in collab_recs])


    w_content, w_collab = hybrid_weights()

    scores = {}

    for course, score in content_recs:
        scores.setdefault(course.id, 0)
        scores[course.id] += w_content * score

    for course, score in collab_recs:
        scores.setdefault(course.id, 0)
        scores[course.id] += w_collab * score

    # Ordenar y obtener cursos
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    courses = Course.objects.in_bulk([cid for cid, _ in ranked[:limit]])

    return [{'course': courses[cid], 'score': score} for cid, score in ranked[:limit] if cid in courses]


