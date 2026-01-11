from .recommender_content import course_features
from .recommender_colab import build_prefs, calculateSimilarItems
import shelve
from .models import Course

SHELVE_FILE = "precomputed_recommender_system_courses.db"

def precalculate_data():
    """Precompute course features and collaborative similarity matrix, store in shelve."""
    with shelve.open(SHELVE_FILE) as db:
        # --- Course features ---
        features_dict = {}
        print("Calculando features de cursos...")
        for course in Course.objects.all():
            features_dict[course.id] = course_features(course)
        db['course_features'] = features_dict
        print("Features de cursos guardadas en shelve.")

        # --- Collaborative similarity matrix ---
        print("Calculando matriz de similitud colaborativa...")
        prefs = build_prefs()
        db['item_sim'] = calculateSimilarItems(prefs)
        print("Matriz de similitud guardada en shelve.")