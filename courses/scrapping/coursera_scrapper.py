from .base_scrapper import BaseScraper
from urllib import request
import urllib.error
from bs4 import BeautifulSoup
import re
import time
import socket
from .utils import extract_keywords, map_category

BASE_URL = "https://www.coursera.org"

HOURS_PER_WEEK = 10 # Estimated hours per week in Coursera for duration normalization

# Coursera sometimes blocks requests if they are too frequent.
DEFAULT_TIMEOUT = 10
MAX_RETRIES = 3
RETRY_BACKOFF = 1.5
MAX_COURSES_PER_CATEGORY = 80

class CourseraScraper(BaseScraper):
    def fetch(self):
        url = "https://www.coursera.org/courses?query=data%20science"
        return self.fetch_url(url)

    def fetch_url(self, url):
        """Fetch a URL with retries, timeout and polite delay. Returns decoded HTML or None."""
        headers = {"User-Agent": "Mozilla/5.0 (compatible; Scraper/1.0; +https://example.com)"}
        req = request.Request(url, headers=headers)
        backoff = RETRY_BACKOFF
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = request.urlopen(req, timeout=DEFAULT_TIMEOUT)
                try:
                    return resp.read().decode('utf-8')
                except Exception:
                    return resp.read().decode(errors='ignore')
            except (urllib.error.HTTPError, urllib.error.URLError, socket.timeout):
                if attempt == MAX_RETRIES:
                    return None
                time.sleep(backoff)
                backoff *= RETRY_BACKOFF
            except Exception:
                return None

    def parse(self, html):
        soup = BeautifulSoup(html, "html.parser")
        courses = []

        # Collect browse links (categories), only '/browse/segment' or '/browse/segment/subsegment'
        pattern = re.compile(r"^/browse/[^/?]+(?:/[^/?]+)?(?:\\?.*)?$")
        categories_urls = set()
        for a in soup.find_all("a", href=pattern):
            path = a['href'].split('?')[0]
            categories_urls.add(path)

        for category_url in categories_urls:
            category = category_url.rstrip('/').split('/')[-1]
            print(f"Scraping category: {category}")
            full_url = BASE_URL + category_url
            self.extract_category_course_info(full_url, courses, category)
        return courses
    
    def extract_category_course_info(self, url, courses, category):
        html = self.fetch_url(url)
        if not html:
            return
        soup = BeautifulSoup(html, "html.parser")

        course_links = set()
        for a in soup.find_all("a", href=re.compile(
            r"^/(learn|specializations|professional-certificates)/")):
            href = a.get("href")
            if not href:
                continue

            full_url = BASE_URL + href

            if "/degrees/" in full_url:
                continue                # Skip degree programs
            
            course_links.add(full_url)
            if len(course_links) >= MAX_COURSES_PER_CATEGORY:
                break

        for url in course_links:
            print(f"  Scraping course: {url}")
            course_html = self.fetch_url(url)
            if not course_html:
                continue
            course_soup = BeautifulSoup(course_html, "html.parser")
            time.sleep(0.2)

            h1 = course_soup.find("h1")
            title = h1.get_text(strip=True) if h1 else None
            
            meta = course_soup.find("meta", attrs={"name": "description"})
            meta_content = meta["content"].strip() if meta and meta.get("content") else None

            instructor = None
            description = meta_content

            if meta_content:
                text = re.match(r'^\s*Offered by\s+(.+?)(?:[.:–—\-]\s*|\s{2,}|$)(.*)$', meta_content, re.I)
                if text:
                    instructor = text.group(1).strip()
                    rest = text.group(2).strip()
                    description = rest if rest else None # Descriptions in coursera are limited by js rendering

            rating_element = course_soup.find('div', attrs={'aria-label': re.compile(r'estrell(a|as)?|star', re.I)})
            rating = rating_element.get_text().strip() if rating_element else None

            level = None
            duration = None
            for text in course_soup.stripped_strings:
                t = text.strip()
                parts = [p.strip() for p in t.split('·')] if '·' in t else [t]
                for part in parts:
                    low = part.lower()
                    if not level and any(x in low for x in ["beginner", "intermediate", "advanced"]):
                        # Accept the part as `level` only if it contains at most 3 words - to avoid appearances in the description
                        words = part.strip().split()
                        if len(words) <= 3:
                            level = ' '.join(words)
                    if not duration and re.search(r"\d+\s*(?:-|to)\s*\d+\s*(months?|weeks?|hours?)", low):
                        duration = part.replace('to complete', '').strip()
                    if not duration and re.search(r"\d+\s*(months?|weeks?|hours?)", low):
                        duration = re.sub(r'at\s*\d+\s*hours\s*a\s*week', '', part, flags=re.I).strip()

            courses.append({
                "title": title,
                "description": description,
                "platform": "Coursera",
                "level": level,
                "duration": duration,
                "instructor": instructor,
                "rating": rating,
                "url": url,
                "category": category,
                "keywords": extract_keywords(title, description) if description else extract_keywords(title, ""),
                "last_scraped": self.get_current_datetime()
            })

    
    def normalize(self, data):
        # Helper to parse duration text into hours
        def parse_duration_text(txt):
            if not txt:
                return None
            s = txt.lower().strip()

            # months
            m = re.search(r'(\d+(?:\.\d+)?)\s*months?', s)
            if m:
                return int(round(float(m.group(1)) * 4 * HOURS_PER_WEEK))

            # weeks
            m = re.search(r'(\d+(?:\.\d+)?)\s*weeks?', s)
            if m:
                return int(round(float(m.group(1)) * HOURS_PER_WEEK))
            
            # total hours
            m = re.search(r'(\d+(?:\.\d+)?)\s*(?:hours|hrs?)', s)
            if m:
                return int(round(float(m.group(1))))
            return None

        for course in data:
            # Clean title/description
            if course.get("title"):
                course["title"] = course["title"].strip()
            if course.get("description"):
                course["description"] = course["description"].strip()

            # Normalize level
            lvl = course.get("level")
            lvl = lvl.lower() if lvl else None
            if lvl is None:
                course["level"] = None
            elif "beginner" in lvl:
                course["level"] = "Beginner"
            elif "intermediate" in lvl:
                course["level"] = "Intermediate"
            elif "advanced" in lvl:
                course["level"] = "Advanced"
            else:
                course["level"] = None

            # Normalize rating to float when possible
            rt = course.get("rating")
            if rt:
                try:
                    course["rating"] = float(rt)
                except:
                    course["rating"] = None

            dur = course.get("duration")
            course["duration"] = parse_duration_text(str(dur)) if dur else None

            # Clean negative duration or rating
            duration = course["duration"]
            if duration is not None and duration < 0:
                duration = None
            rating = course["rating"]
            if rating is not None and rating < 0:
                rating = None

            # Normalize category names
            cat = course.get("category")
            if cat:
                course["category"] = cat.replace("_", " ").replace("-", " ").title()
                course["category"] = course["category"].strip()
                course["category"] = course["category"].replace(" & ", " and ")
                course["category"] = map_category(course["category"])

            print(f"Normalized course category: {course.get('category')}")

        return data
    

if __name__ == "__main__":
    scraper = CourseraScraper()
    courses = scraper.run()
    print(f"Total courses scraped: {len(courses)}")