import time
import schedule
from src.scraper import DjinniScraper
from src.bot import send_new_vacancies


def job():
    print(f"\n[{time.strftime('%H:%M:%S')}] Автоматичний пошук вакансій")
    try:
        scraper = DjinniScraper(keyword="Data Analyst",exp_level="no_exp&exp_level=1y")
        scraper.fetch_jobs()

        print(f"[{time.strftime('%H:%M:%S')}] Перевіряю базу на нові вакансії")
        send_new_vacancies()

    except Exception as e:
        print(f"Помилка під час виконання: {e}")


schedule.every(30).minutes.do(job)

if __name__ == "__main__":
    print("Планувальник запущено. Робимо перший пошук")
    job()

    while True:
        schedule.run_pending()
        time.sleep(1)