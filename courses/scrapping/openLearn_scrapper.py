from .base_scrapper import BaseScraper
from urllib import request
from bs4 import BeautifulSoup
import re
from .utils import extract_keywords, map_category

BASE_URL = "https://www.open.edu"

END_FILTERS_CATEGORY_URL = "all-content?filter=date/grid/all/freecourses/all/all/all/all"

class openLearnScraper(BaseScraper):
    def fetch(self):
        url = "https://www.open.edu/openlearn/subject-information"
        response = request.urlopen(url)
        return response.read().decode('utf-8')

    def parse(self, html):
        soup = BeautifulSoup(html, "html.parser")
        courses = []

        category_elements = soup.find_all("div", class_="subject-item")
        categories = {}
        for cat in category_elements:
            name = cat.find("h2", class_="subject-heading").get_text().strip()
            url = cat.find("a", href=True).get('href')
            final_url = BASE_URL + url + "/" + END_FILTERS_CATEGORY_URL
            categories[name] = final_url

        for category in categories:
            url = categories[category]
            print(f"Scraping category: {url}")
            self.extract_category_course_info(url, courses, category)
        return courses
    
    def extract_category_course_info(self, url, courses, category):
        response = request.urlopen(url)
        html = response.read().decode('utf-8')
        soup = BeautifulSoup(html, "html.parser")

        max_pages = soup.find('span', class_='current-of-total')
        if max_pages:
            try:
                max_pages = int(max_pages.get_text().strip().split()[-1])
            except:
                max_pages = 1
        else:
            max_pages = 1
        
        for page in range(0, max_pages ):
            print(f"  Scraping page {page + 1} of {max_pages} for category {category}")
            paged_url = f"{url}&page={page}"
            print(f"    Paged URL: {paged_url}")
            response = request.urlopen(paged_url)
            page_html = response.read().decode('utf-8')
            page_soup = BeautifulSoup(page_html, "html.parser")
            page_courses = page_soup.find_all('div', class_='ser-grid-item')

            for course in page_courses:
                course_url = course.find('a', href=True).get('href')
                # make course URL absolute when needed
                if course_url and not course_url.startswith('http'):
                    course_url = BASE_URL + course_url
                print(f"  Scraping course: {course_url}")
                
                level_element = course.find('span', attrs={"data-level": True})
                level = level_element.get('data-level') if level_element else None

                duration_element = course.find('div', class_='hours')
                duration = duration_element.get_text().strip() if duration_element else None

                # The page shows courses that are not of the current category
                # To reduce duplicates, skip those not matching the category
                course_category = course.find('p', class_='subject-name').get_text().strip()
                if course_category.lower() != category.lower():
                    continue

                print(f"    Level: {level}, Duration: {duration}")
                print(f"    URL: {course_url}")
                print("")

                course_page = request.urlopen(course_url)
                course_html = course_page.read().decode('utf-8')
                course_soup = BeautifulSoup(course_html, "html.parser")

                h1 = course_soup.find("h1", property="schema:name")
                title = h1.get_text(strip=True) if h1 else None

                print(f"    Title: {title}")
                
                rating_element = course_soup.find('span', class_='average-value')
                rating = rating_element.get_text().strip() if rating_element else None

                description_all = course_soup.find('div', class_='openlearn-enrol-intro')
                if description_all:
                    paragraphs = description_all.find_all('p')
                else:
                    summary_div = course_soup.find('div', id='summary_content')
                    paragraphs = summary_div.find_all('p') if summary_div else []
                    description_all = course_soup.find('div', id='summary_content').find_all('p')
                description = " ".join([p.get_text(strip=True) for p in paragraphs]) if paragraphs else None
                
                instructor = None

                courses.append({
                    "title": title,
                    "description": description,
                    "platform": "OpenLearn",
                    "level": level,
                    "duration": duration,
                    "instructor": instructor,
                    "rating": rating,
                    "url": course_url,
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

            # total hours
            m = re.search(r'(\d+(?:\.\d+)?)\s*(?:hours|hrs?)', s)
            if m:
                return int(round(float(m.group(1))))
            return None

        for course in data:
            # Clean title/description/instructor
            if course.get("title"):
                course["title"] = course["title"].strip()
            if course.get("description"):
                course["description"] = course["description"].strip()
            if course.get("instructor"):
                course["instructor"] = course["instructor"].strip()

            # Normalize level
            lvl = course.get("level")
            if lvl == "1":
                course["level"] = "Beginner"
            elif lvl == "2":
                course["level"] = "Intermediate"
            elif lvl == "3":
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

        return data
    

if __name__ == "__main__":
    scraper = openLearnScraper()
    courses = scraper.run()
    print(f"Total courses scraped: {len(courses)}")