import nltk
from nltk.corpus import stopwords
from nltk import data
from collections import Counter
import math
import re
from collections import Counter, defaultdict
from main.models import Course

# STOPWORDS -----------------

# Download stopwords from NLTK
try:
    data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords', quiet=True)

STOPWORDS = set(stopwords.words('english'))

# Add common words specific to online courses that are not relevant to content of courses
STOPWORDS.update({"course", "learn", "program", "certification", "certificate", "online", 
                  "introduction", "specialization", "professional", "development", "fundamentals", 
                  "basics", "free", "enroll", "foundational", "career", "beginner", "advanced", 
                  "intermediate", "study", "module", "topic", "topics", "week", "weeks", "duration",
                  "available", "upcoming", "upskill", "path", "skills", "skill", "level", "including",
                  "knowledge", "understanding", "ability", "abilities", "concepts", "intended", "audience",
                  "build", "building", "practical", "theory", "hands-on", "hands", "projects", "project",
                  "work", "works", "real-world", "real", "world", "case", "cases", "case studies", "study",
                  "basic", "part", "parts", "introduction", "intros", "intro", "become", "enroll", "free"})


def clean_text(text):
    """
    Clean text to extract keywords:
    - Convert to lowercase
    - Remove punctuation
    """
    import re
    text = text.lower()
    text = re.sub(r"[^a-z\s]", " ", text)
    return text


# Extract keywords using TF-IDF

def tokenize(text):
    text = clean_text(text)
    return [w for w in text.split() if w not in STOPWORDS and len(w) > 2]

def compute_idf():
    """
    Compute IDF of documents in db.
    """
    courses = Course.objects.all()
    texts = []
    for item in courses:
        texts.append(f"{item.title or ''} {item.description or ''}")

    N = len(texts) if texts else 1
    df = defaultdict(int)

    for text in texts:
        for term in set(tokenize(text)):
            df[term] += 1

    idf = {
        term: math.log(N / (1 + freq))
        for term, freq in df.items()
    }
    return idf

def extract_keywords(title, description, idf, top_n=10):
    text = f"{title} {description}" if description else title
    tokens = tokenize(text)

    tf = Counter(tokens)
    scores = {
        term: tf[term] * idf.get(term, 0)
        for term in tf
    }

    return [
        term for term, _ in
        sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_n]
    ]


# CATEGORY MAPPING -----------------
def map_category(category):
    """
    Map various category names to a standard set.
    """
    category_mapping = {
        # Possible exptension
        # Won't map anything for now
    }
    
    cat_lower = category.lower() if category else ""
    return category_mapping.get(cat_lower, category.title() if category else None)