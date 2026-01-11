import nltk
from nltk.corpus import stopwords
from nltk import data

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


def extract_keywords(title, description, top_n=20):
    text = f"{title} {description}" if description else title
    text = clean_text(text)
    tokens = [w for w in text.split() if w not in STOPWORDS and len(w) > 2]
    
    from collections import Counter
    counts = Counter(tokens)
    return [w for w, _ in counts.most_common(top_n)]



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