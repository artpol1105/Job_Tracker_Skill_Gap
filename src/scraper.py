import requests
from bs4 import BeautifulSoup
import urllib.parse
import re
import time
from datetime import datetime, timedelta
from src.database import SessionLocal, Vacancy, Skill


class DjinniScraper:
    def __init__(self, keyword, exp_level="1y"):
        self.encoded_keyword = urllib.parse.quote(keyword)
        self.exp_level = exp_level
        self.base_url = f"https://djinni.co/jobs/?all_keywords={self.encoded_keyword}&search_type=basic-search&exp_level={self.exp_level}"
        self.items_per_page = 15

        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://djinni.co/"
        }

        self.target_skills = [
            "python", "pandas", "numpy", "sql", "postgresql", "mysql", "oracle", "mongodb", "nosql",
            "aws", "gcp", "azure", "bigquery", "snowflake", "redshift", "clickhouse",
            "power bi", "tableau", "looker", "qlik", "metabase", "superset", "excel",
            "dbt", "airflow", "etl", "dwh",
            "git", "docker", "github", "gitlab", "linux", "bash", "api",
            "machine learning", "a/b testing", "statistics", "nlp"
        ]
        self.db = SessionLocal()

    def parse_djinni_date(self, date_text):
        if not date_text:
            return None
        date_text = date_text.lower()
        now = datetime.now()

        if "сьогодні" in date_text: return now
        if "вчора" in date_text: return now - timedelta(days=1)

        months = {
            "січня": 1, "лютого": 2, "березня": 3, "квітня": 4, "травня": 5, "червня": 6,
            "липня": 7, "серпня": 8, "вересня": 9, "жовтня": 10, "листопада": 11, "грудня": 12
        }
        for month_name, month_num in months.items():
            if month_name in date_text:
                day_match = re.search(r'\d+', date_text)
                if day_match:
                    try:
                        return now.replace(month=month_num, day=int(day_match.group()))
                    except ValueError:
                        pass
        return None

    def clean_title(self, title_text, company_name):
        cleaned = re.sub(r'(Швидко Відповідає|Тільки відгуки|Відгуки)', '', title_text, flags=re.IGNORECASE)
        cleaned = cleaned.replace('$', '')
        if company_name and company_name in cleaned:
            cleaned = cleaned.replace(company_name, '')
        cleaned = re.sub(r'(?:від|до)?\s*\d+\s*(?:[-—]\s*\d+)?', '', cleaned, flags=re.IGNORECASE)
        return cleaned.strip(' -/,|')

    def fetch_job_details(self, job_url):
        response = requests.get(job_url, headers=self.headers)
        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.text, 'html.parser')

        h1 = soup.find('h1')
        raw_title = h1.get_text(separator=' ', strip=True) if h1 else "Unknown Title"

        company_elem = soup.select_one('a.text-secondary.fw-medium[href*="/jobs/company-"]')
        if not company_elem:
            company_elem = soup.select_one('a[href*="/jobs/company-"]')

        company = company_elem.get_text(strip=True) if company_elem else None

        salary_span = soup.select_one('span.text-success.text-nowrap')
        if not salary_span:
            salary_span = soup.select_one('span.text-success')

        salary = None
        if salary_span:
            raw_salary = salary_span.get_text(separator=' ', strip=True)
            salary = re.sub(r'(?i)скопійовано( посилання)?', '', raw_salary).strip()

        posted_at = None
        page_text = soup.get_text(separator=' ', strip=True)
        date_match = re.search(r'Опубліковано\s+([а-яА-Яa-zA-Z0-9іІїЇєЄ]+(?:\s+[а-яА-Яa-zA-ZіІїЇєЄ]+)?)', page_text,
                               re.IGNORECASE)
        if date_match:
            posted_at = self.parse_djinni_date(date_match.group(1))

        for nav in soup.find_all(['nav', 'header']):
            nav.extract()
        desc_blocks = soup.find_all('div', class_='profile-page-section') or soup.find_all('div', class_='mb-4')
        joined_desc = " \n".join([block.get_text(separator=' ', strip=True) for block in desc_blocks])
        joined_desc = joined_desc.replace("Djinni Кандидати Вакансії Зарплати Увійти Зареєструватись", "").strip()

        return {
            "title_raw": raw_title,
            "company": company,
            "salary": salary,
            "posted_at": posted_at,
            "description": joined_desc
        }

    def extract_skills(self, text):
        found_skills = []
        for skill in self.target_skills:
            if re.search(r'\b' + re.escape(skill) + r'\b', text.lower()):
                found_skills.append(
                    skill.title() if skill not in ["sql", "aws", "gcp", "etl", "dbt", "dwh", "api"] else skill.upper())
        return found_skills

    def fetch_jobs(self):
        print(f"Searching for '{urllib.parse.unquote(self.encoded_keyword)}' | Experience: {self.exp_level}\n")
        page = 1
        total_saved = 0
        previous_page_hrefs = set()

        while True:
            print(f"Scraping page {page}...")
            response = requests.get(f"{self.base_url}&page={page}", headers=self.headers)
            if response.status_code != 200:
                break

            soup = BeautifulSoup(response.text, 'html.parser')
            job_links = soup.find_all('a', href=re.compile(r'^/jobs/\d+-'))
            if not job_links:
                break

            current_page_hrefs = {link.get('href') for link in job_links}
            if current_page_hrefs == previous_page_hrefs:
                break
            previous_page_hrefs = current_page_hrefs

            unique_links = []
            seen = set()
            for link in job_links:
                if link.get('href') not in seen:
                    seen.add(link.get('href'))
                    unique_links.append(link)

            for link in unique_links:
                full_url = "https://djinni.co" + link.get('href')
                job_id = re.search(r'/jobs/(\d+)-', full_url).group(1)

                if self.db.query(Vacancy).filter(Vacancy.id == job_id).first():
                    print(f"  Already in DB: ID {job_id}")
                    continue

                print(f"  Parsing details for ID {job_id}...")
                details = self.fetch_job_details(full_url)
                if not details:
                    continue

                clean_title = self.clean_title(details['title_raw'], details['company'])

                new_vacancy = Vacancy(
                    id=job_id,
                    platform="Djinni",
                    title=clean_title,
                    company=details['company'],
                    salary=details['salary'],
                    description=details['description'],
                    posted_at=details['posted_at'],
                    parsed_at=datetime.now()
                )

                self.db.add(new_vacancy)

                for skill_name in self.extract_skills(details['description']):
                    skill_obj = self.db.query(Skill).filter(Skill.name == skill_name).first()
                    if not skill_obj:
                        skill_obj = Skill(name=skill_name)
                        self.db.add(skill_obj)
                    new_vacancy.skills.append(skill_obj)

                self.db.commit()
                total_saved += 1

                print(f"    Saved: {clean_title} | Company: {details['company']} | Salary: {details['salary']}")
                time.sleep(1.5)

            if len(unique_links) < self.items_per_page:
                print(f"\nFound less than {self.items_per_page} jobs. Pagination finished.")
                break
            page += 1

        print(f"Scraping complete! Total new jobs saved: {total_saved}")
        self.db.close()


if __name__ == "__main__":
    scraper = DjinniScraper(keyword="Data Analyst", exp_level="1y")
    scraper.fetch_jobs()