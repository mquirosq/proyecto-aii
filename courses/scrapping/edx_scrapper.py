from .base_scrapper import BaseScraper
from urllib import request
from bs4 import BeautifulSoup
import os
import ssl
from .utils import extract_keywords, map_category

BASE_URL = "https://www.edx.org"
BASE_LIST_URL = "https://www.edx.org/search?tab=course&page="
PAGES = 42  # Total pages to scrape (estimated, as edX does not provide total count directly)

class EdxScraper(BaseScraper):
    def fetch(self):
        url = BASE_LIST_URL + "1"
        print(f"Fetching URL: {url}")
        html = self.fetch_url(url)
        return html if html is not None else ''

    def fetch_url(self, url):
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        }

        req = request.Request(url, headers=headers)
        try:
            resp = request.urlopen(req, timeout=20)
            data = resp.read()
            try:
                return data.decode('utf-8')
            except Exception:
                return data.decode('latin-1')
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None

    def parse(self, html):
        courses = []

        total_pages = PAGES
        print(f"Detected total pages: {total_pages}")

        for page in range(1, total_pages + 1):
            print(f"Scraping page: {page} of {total_pages}")
            full_url = BASE_LIST_URL + str(page)
            self.extract_page_course_info(full_url, courses)
        return courses
    
    def extract_page_course_info(self, url, courses):
        html = self.fetch_url(url)
        if not html:
            return
        soup = BeautifulSoup(html, "html.parser")

        course_links = {a for a in soup.find_all('a', href=True) if a['href'].startswith('/learn/')}

        for link in course_links:
            href = link.get('href')
            course_url = BASE_URL + href
            print(f"Scraping course: {course_url}")

            course_html = self.fetch_url(course_url)
            if not course_html:
                print(f"Failed to fetch course page: {course_url}")
                continue
            course_soup = BeautifulSoup(course_html, "html.parser")
            # edx returns a page with minimal info as most content is loaded via JS
            # We will try to extract what we can from the static HTML

            # --- TITLE and INSTRUCTOR
            title = None
            instructor = None

            h1 = course_soup.find("h1")
            if h1 and h1.get_text(strip=True):
                title = h1.get_text(strip=True)
            else:
                meta_title = course_soup.find("meta", property="og:title")
                if meta_title and meta_title.get("content"):
                    title = meta_title["content"].replace("| edX", "").strip()

            # Extract instructor from title if possible (ex. "MITx: Supply Chain Technology and Systems")
            instructor = None
            if title and ":" in title:
                left = title.split(":", 1)[0].strip()
                # Remove trailing 'X' if present (common in edX organization names)
                if len(left) > 1 and left[-1].lower() == 'x':
                    instructor = left[:-1].strip()
                else:
                    instructor = left

            # --- DESCRIPTION (from meta tag)
            meta = course_soup.find("meta", attrs={"name": "description"})
            description = meta["content"].strip() if meta else None

            # --- CATEGORY (from URL)
            category = None
            parts = course_url.split("/")
            if len(parts) > 4:
                category = parts[4]

            courses.append({
                "title": title,
                "description": description,
                "platform": "edX",
                "level": None, # Level info not consistently available (due to js rendering)
                "duration": None, # Duration info not consistently available (due to js rendering)
                "instructor": instructor,
                "rating": None, # There is no rating info
                "url": course_url,
                "category": category,
                "keywords": extract_keywords(title, description) if description else extract_keywords(title, ""),
                "last_scraped": self.get_current_datetime()
            })
    
    def normalize(self, data):
        for course in data:
            if course.get("title"):
                course["title"] = course["title"].strip()
            if course.get("description"):
                course["description"] = course["description"].strip()
            if course.get("instructor"):
                course["instructor"] = course["instructor"].strip()

            # Normalize category names
            cat = course.get("category")
            if cat:
                course["category"] = cat.replace("_", " ").replace("-", " ").title()
                course["category"] = course["category"].strip()
                course["category"] = course["category"].replace(" & ", " and ")
                course["category"] = map_category(course["category"])
        
        return data
    

if __name__ == "__main__":
        
    if (not os.environ.get('PYTHONHTTPSVERIFY', '') and
        getattr(ssl, '_create_unverified_context', None)):
        ssl._create_default_https_context = ssl._create_unverified_context 

    scraper = EdxScraper()
    courses = scraper.run()
    print(f"Total courses scraped: {len(courses)}")