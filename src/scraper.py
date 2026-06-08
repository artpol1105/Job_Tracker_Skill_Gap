import requests
from bs4 import BeautifulSoup
import urllib.parse
import re
import time
from datetime import datetime

from src.database import SessionLocal, Vacancy, Skill


class DjinniScraper:
    def __init__(self, keyword):
        self.encoded_keyword = urllib.parse.quote(keyword)
        self.base_url = f"https://djinni.co/jobs/?all_keywords={self.encoded_keyword}&search_type=basic-search"

        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Referer": "https://djinni.co/"
        }

        self.target_skills = [
            "python", "r", "scala", "java", "pandas", "numpy", "spark", "kafka",
            "sql", "postgresql", "mysql", "oracle", "mongodb", "nosql",
            "aws", "gcp", "azure", "bigquery", "snowflake", "redshift", "clickhouse",
            "power bi", "tableau", "looker", "qlik", "metabase", "superset", "excel",
            "dbt", "airflow", "etl", "dwh",
            "git", "docker", "github", "gitlab", "linux", "bash", "api",
            "machine learning", "a/b testing", "statistics", "nlp"
        ]

        self.db = SessionLocal()

    def get_job_description(self, job_url):
        response = requests.get(job_url, headers=self.headers)
        if response.status_code != 200:
            return "Failed to fetch description"

        soup = BeautifulSoup(response.text, 'html.parser')
        description_blocks = soup.find_all('div', class_='profile-page-section')
        if not description_blocks:
            description_blocks = soup.find_all('div', class_='mb-4')

        full_text = [block.get_text(separator=' ', strip=True) for block in description_blocks]
        return " \n".join(full_text)

    def extract_skills(self, text):
        found_skills = []
        text_lower = text.lower()

        for skill in self.target_skills:
            pattern = r'\b' + re.escape(skill) + r'\b'
            if re.search(pattern, text_lower):
                found_skills.append(
                    skill.title() if skill not in ["sql", "aws", "gcp", "etl", "dbt"] else skill.upper())

        return found_skills

    def fetch_jobs(self):
        print(f"Searching for jobs with keyword: '{urllib.parse.unquote(self.encoded_keyword)}'...\n")

        response = requests.get(self.base_url, headers=self.headers)
        if response.status_code != 200:
            print(f"Access error! Status code: {response.status_code}")
            return

        soup = BeautifulSoup(response.text, 'html.parser')
        job_links = soup.find_all('a', href=re.compile(r'^/jobs/\d+-'))

        unique_links = []
        seen_hrefs = set()
        for link in job_links:
            href = link.get('href')
            if href not in seen_hrefs:
                seen_hrefs.add(href)
                unique_links.append(link)

        print(f"Found {len(unique_links)} jobs. Processing and saving to database...\n")

        for index, link in enumerate(unique_links, start=1):
            title = " ".join(link.stripped_strings) or "No Title"
            full_url = "https://djinni.co" + link.get('href')

            job_id_match = re.search(r'/jobs/(\d+)-', full_url)
            job_id = job_id_match.group(1) if job_id_match else full_url

            existing_job = self.db.query(Vacancy).filter(Vacancy.id == job_id).first()
            if existing_job:
                print(f"[{index}] Already in DB: {title}")
                continue

            print(f"[{index}] New job! Fetching and saving: {title}...")
            description = self.get_job_description(full_url)
            extracted_skills = self.extract_skills(description)

            new_vacancy = Vacancy(
                id=job_id,
                platform="Djinni",
                title=title,
                description=description,
                parsed_at=datetime.now()
            )

            for skill_name in extracted_skills:
                skill_obj = self.db.query(Skill).filter(Skill.name == skill_name).first()
                if not skill_obj:
                    skill_obj = Skill(name=skill_name)
                    self.db.add(skill_obj)

                new_vacancy.skills.append(skill_obj)

            self.db.add(new_vacancy)
            self.db.commit()

            print(f"Saved! Skills: {', '.join(extracted_skills) if extracted_skills else 'None'}\n")
            time.sleep(1.5)

        print("All jobs processed successfully!")
        self.db.close()


if __name__ == "__main__":
    scraper = DjinniScraper("Data Analyst")
    scraper.fetch_jobs()