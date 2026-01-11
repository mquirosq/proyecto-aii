from .models import UserCourse, Course
from collections import Counter
from scrapping.utils import extract_keywords
from collections import defaultdict
import math
from django.utils import timezone
from django.db.models import Q
import shelve

SHELVE_FILE = "precomputed_recommender_system_courses.db"

# Weights for different features
FEATURE_WEIGHTS = {
    "cat": 2.5,
    "level": 2.0,  
    "plat": 1.5,   
    "instr": 1.2,   
    "dur": 1.0,     
    "kw": 0.6,      
}

def load_precomputed_data():
    """Load precomputed data from shelve."""
    with shelve.open(SHELVE_FILE) as db:
        course_features_dict = db.get('course_features', {})
        item_sim = db.get('item_sim', {})
    return course_features_dict, item_sim


def get_user_feedback(user):
    liked = UserCourse.objects.filter(user=user, liked=True).select_related('course')
    disliked = UserCourse.objects.filter(user=user, disliked=True).select_related('course')
    viewed = UserCourse.objects.filter(user=user, viewed__gt=0).select_related('course')
    return liked, disliked, viewed


def course_features(course):
    features = []

    # Basic features
    if course.category:
        features.append(f"cat:{course.category.name}")

    if course.platform:
        features.append(f"plat:{course.platform.name}")

    if course.level:
        features.append(f"level:{course.level}")

    if course.instructor:
        features.append(f"instr:{course.instructor.name}")
    
    if course.duration is None:
        dur_feat = None
    elif course.duration < 5:
         dur_feat = "dur:short"
    elif course.duration <= 20:
        dur_feat = "dur:medium"
    else:
        dur_feat = "dur:long"
    
    if dur_feat:
        features.append(dur_feat)

    # Keywords
    for kw in extract_keywords(course.title, course.description or ""):
        features.append(f"kw:{kw}")

    return features


def build_user_profile(user):
    profile = defaultdict(float)

    # Try to use precomputed course features (fallback to computing on the fly)
    course_features_dict, _ = load_precomputed_data()

    interactions = UserCourse.objects.filter(user=user)

    for uc in interactions:
        decay = time_decay(uc.timestamp) # More recent interactions have higher weight

        weight = 0.0

        if uc.liked:
            weight += 4.0 # high positive weight

        if uc.disliked:
            weight -= 5.0 # high negative weight

        if uc.viewed > 0:
            weight += math.sqrt(uc.viewed) # increasing but moderate positive weight
        
        weight *= decay

        if weight == 0:
            continue

        # Prefer precomputed features keyed by course id (int or str), else compute
        feats = course_features_dict.get(uc.course_id) or course_features_dict.get(str(uc.course_id))
        if feats is None:
            feats = course_features(uc.course)

        for feat in feats:
            kind = feat.split(":", 1)[0]
            feat_weight = FEATURE_WEIGHTS.get(kind, 1.0)
            profile[feat] += weight * feat_weight


    return normalize_profile(profile)

def normalize_profile(profile):
    """Normalize profile vector to unit length."""
    norm = math.sqrt(sum(v * v for v in profile.values()))
    if norm == 0:
        return profile
    return {k: v / norm for k, v in profile.items()}


def time_decay(timestamp, half_life_days=30):
    """Calculate a decay factor based on the age of the interaction. At half_life_days, the weight is halved."""
    now = timezone.now()
    days = (now - timestamp).days
    return math.exp(-days / half_life_days)


def similarity(user_profile, course_features):
    """Similarity as ponderated sum of feature weights. Scalar product."""
    if not course_features:
        return 0.0
    score = sum(user_profile.get(f, 0.0) for f in course_features)
    return score / len(course_features)

def recommend_content_courses(user, limit=10):
    # Load precomputed course features to avoid recomputing per candidate
    course_features_dict, _ = load_precomputed_data()

    user_profile = build_user_profile(user)

    # Only consider courses the user explicitly liked or disliked as "interacted"
    interacted = set(
        UserCourse.objects
        .filter(user=user)
        .filter(Q(liked=True) | Q(disliked=True))
        .values_list('course_id', flat=True)
    )

    recommendations = []

    for course in Course.objects.exclude(id__in=interacted):
        feats = course_features_dict.get(course.id) or course_features_dict.get(str(course.id))
        if feats is None:
            feats = course_features(course)

        score = similarity(user_profile, feats)
        if score > 0:
            recommendations.append((course, score))

    recommendations.sort(key=lambda x: x[1], reverse=True)
    top = recommendations[:limit]

    # Return list of dicts with course and score so templates can show the score
    return [{'course': c, 'score': s} for c, s in top]