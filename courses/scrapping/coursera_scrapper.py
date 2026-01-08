from base_scrapper import BaseScraper
import urllib
from urllib import request
from bs4 import BeautifulSoup
import re

BASE_URL = "https://www.coursera.org"

HORAS_POR_SEMANA = 10

class CourseraScraper(BaseScraper):
    def fetch(self):
        url = "https://www.coursera.org/courses?query=data%20science"
        response = request.urlopen(url)
        return response.read().decode('utf-8')

    def parse(self, html):
        soup = BeautifulSoup(html, "html.parser")
        courses = []

        categories_urls = [a.get('href') for a in soup.find('div', {'data-testid': "category-pills-group"}).find_all('a')]

        for category_url in categories_urls:
            category = category_url.split('/')[-1]
            print(f"Scraping category: {category}")
            full_url = BASE_URL + category_url
            self.extract_category_course_info(full_url, courses, category)
        return courses
    
    def extract_category_course_info(self, url, courses, category):
        response = request.urlopen(url)
        html = response.read().decode('utf-8')
        soup = BeautifulSoup(html, "html.parser")

        course_cards = soup.find_all('div', {'data-testid': "product-card-cds"})

        for card in course_cards:
            url = BASE_URL + card.find('a', href=True).get('href')
            if "degree" in url:
                continue  # Skip degree programs

            course_page = request.urlopen(url)
            course_html = course_page.read().decode('utf-8')
            course_soup = BeautifulSoup(course_html, "html.parser")

            title = course_soup.find('h1', {'data-e2e': "hero-title"}).get_text().strip()
            
            description = course_soup.find('div', {'data-testid': "cml-viewer"}).get_text().strip()
            
            rating_element = course_soup.find('div', attrs={'aria-label': re.compile(r'estrell(a|as)?|star', re.I)})
            rating = rating_element.get_text().strip() if rating_element else None

            level_element = course_soup.find('div', string=re.compile(r'level', re.I), class_="css-fk6qfz")
            level = level_element.get_text().replace('level', '').strip() if level_element else None

            duration_element = course_soup.find('div', string=re.compile(r'to complete', re.I), class_="css-fk6qfz")
            duration = duration_element.get_text().replace(' to complete', '').strip() if duration_element else None

            # Secondary duration location
            if duration is None:
                duration_element = course_soup.find('div', string=re.compile(r'10\s*hours', re.I))
                duration = duration_element.get_text().replace("at 10 hours a week", "").strip() if duration_element else None

            instructor = course_soup.find('h3', string=re.compile(r'Offered by', re.I)).parent.find_next_sibling('div').find('span', class_="css-6ecy9b").get_text().strip()

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
                return int(round(float(m.group(1)) * 4 * HORAS_POR_SEMANA))

            # weeks
            m = re.search(r'(\d+(?:\.\d+)?)\s*weeks?', s)
            if m:
                return int(round(float(m.group(1)) * HORAS_POR_SEMANA))
            
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
            if lvl:
                course["level"] = lvl.strip().capitalize()

            # Normalize rating to float when possible
            rt = course.get("rating")
            if rt:
                try:
                    course["rating"] = float(rt)
                except:
                    course["rating"] = None

            dur = course.get("duration")
            course["duration"] = parse_duration_text(str(dur)) if dur else None

        return data
    

if __name__ == "__main__":
    scraper = CourseraScraper()
    courses = scraper.run()
    print(f"Total courses scraped: {len(courses)}")