import os
from whoosh import index
from whoosh.fields import Schema, TEXT, ID, NUMERIC, KEYWORD, DATETIME
from scrapping import coursera_scrapper, edx_scrapper, openLearn_scrapper
from .models import Course, Platform, Category, Instructor
from django.utils import timezone

DB_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "courses.db"))
WHOOSH_INDEX_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "whoosh_index"))

# ------------------ DB (Django) ------------------

def save_courses_dB(courses):
    for course in courses:
        # --- Platform ---
        platform_name = course.get("platform") or "Unknown"
        platform_obj, _ = Platform.objects.get_or_create(
            name=platform_name
        )

        # --- Category ---
        category_name = course.get("category") or "General"
        category_obj, _ = Category.objects.get_or_create(name=category_name)

        # --- Instructor ---
        instructor_name = course.get("instructor")
        instructor_obj = None
        if instructor_name:
            instructor_obj, _ = Instructor.objects.get_or_create(name=instructor_name)

        # --- Course ---
        last_scraped = course.get("last_scraped") or timezone.now()
        Course.objects.update_or_create(
            url=course.get("url"),
            defaults={
                "title": course.get("title") or "",
                "description": course.get("description") or "",
                "platform": platform_obj,
                "level": course.get("level") or "",
                "duration": course.get("duration") or None,
                "instructor": instructor_obj,
                "rating": course.get("rating") or None,
                "category": category_obj,
                "last_scraped": last_scraped,
            }
        )


# ------------------ WHOOSH ------------------

def init_whoosh(index_dir=WHOOSH_INDEX_DIR):
    # Create index directory if it doesn't exist
    if not os.path.exists(index_dir):
        os.mkdir(index_dir)
    
    # Define schema
    schema = Schema(
        url=ID(stored=True, unique=True),
        title=TEXT(stored=True),
        description=TEXT(stored=True),
        category=TEXT(stored=False, phrase=False),
        level = KEYWORD(lowercase=True, stored=False),
        platform=KEYWORD(lowercase=True, stored=False),
        instructor=KEYWORD(lowercase=True, stored=False),
        duration=NUMERIC(stored=False, numtype=int, signed=False),
        rating=NUMERIC(stored=False, numtype=float),
        last_scraped=DATETIME(stored=False),
        keywords=KEYWORD(commas=True, stored=True)
    )
    # Create or open index
    if not index.exists_in(index_dir):
        ix = index.create_in(index_dir, schema)
    else:
        ix = index.open_dir(index_dir)
    return ix

def open_whoosh(index_dir=WHOOSH_INDEX_DIR):
    if not os.path.exists(index_dir):
        os.mkdir(index_dir)
    if index.exists_in(index_dir):
        return index.open_dir(index_dir)
    else:
        return init_whoosh(index_dir)


def index_courses(courses, ix):
    writer = ix.writer()

    for course in courses:
        # Extract string values from FK objects
        platform_name = course.platform.name if hasattr(course, "platform") and course.platform else ""
        category_name = course.category.name if hasattr(course, "category") and course.category else ""
        instructor_name = course.instructor.name if hasattr(course, "instructor") and course.instructor else ""

        writer.update_document(
            url=course["url"],
            title=course["title"] or "",
            description=course["description"] or "",
            platform=platform_name,
            level=course["level"] or "",
            category=category_name,
            instructor=instructor_name,
            duration=course["duration"] or None,
            rating=course["rating"] or None,
            last_scraped=course["last_scraped"],
            keywords=",".join(course["keywords"] or [])
        )

    writer.commit()

# ------------------ MAIN PIPELINE ------------------

def run_scrapers(scrapers=None):

    if scrapers is None:
        scrapers = ["coursera", "edx", "openlearn"]
    
    all_courses = []

    # Coursera
    if 'coursera' in scrapers:
        print("Scraping Coursera...")
        coursera = coursera_scrapper.CourseraScraper()
        coursera_courses = coursera.run()
        all_courses.extend(coursera_courses)

    # edX
    if 'edx' in scrapers:
        print("Scraping edX...")
        edx = edx_scrapper.EdxScraper()
        edx_courses = edx.run()
        all_courses.extend(edx_courses)

    # OpenLearn
    if 'openlearn' in scrapers:
        print("Scraping OpenLearn...")
        openlearn = openLearn_scrapper.openLearnScraper()
        openlearn_courses = openlearn.run()
        all_courses.extend(openlearn_courses)

    print(f"Total courses scraped: {len(all_courses)}")

    # Normalization already done in scrapers

    # Save to DB
    save_courses_dB(all_courses)
    print("Courses saved to database.")

    # Index to Whoosh
    open_ix = open_whoosh()
    index_courses(all_courses, open_ix)
    print("Courses indexed in Whoosh.")

    # Return scraped courses for the caller to save/index
    return all_courses

def populate_database(selected_scrapers=None):
    init_whoosh()
    run_scrapers(selected_scrapers)