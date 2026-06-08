from sqlalchemy import func
from src.database import SessionLocal, Vacancy, Skill


def run_skill_gap_radar(my_skills):
    db = SessionLocal()

    my_skills_upper = [s.upper() for s in my_skills]

    total_vacancies = db.query(Vacancy).count()
    if total_vacancies == 0:
        print("Database is empty. Run the scraper first.")
        db.close()
        return

    print(f"Analyzing {total_vacancies} vacancies from database...\n")

    top_skills = (
        db.query(Skill.name, func.count(Skill.id).label('count'))
        .join(Skill.vacancies)
        .group_by(Skill.id)
        .order_by(func.count(Skill.id).desc())
        .all()
    )

    print("YOUR STRENGTHS (Skills matching the market):")
    for skill_name, count in top_skills:
        if skill_name.upper() in my_skills_upper:
            percentage = round((count / total_vacancies) * 100)
            print(f"  - {skill_name}: required in {percentage}% of jobs")

    print("\nYOUR SKILL-GAP (Missing tools demanded by market):")
    gap_found = False
    for skill_name, count in top_skills:
        if skill_name.upper() not in my_skills_upper:
            percentage = round((count / total_vacancies) * 100)
            if percentage >= 10:
                print(f"  - {skill_name}: found in {percentage}% of jobs! Consider learning this.")
                gap_found = True

    if not gap_found:
        print("  - Perfect match! No critical skill gaps found for the current market state.")

    db.close()


if __name__ == "__main__":
    my_current_stack = ["python", "pandas", "numpy", "sql", "postgresql", "power bi", "excel", "machine learning",
                        "mysql", "tableau", "git", "github", "a/b testing", "statistics", "nlp", "api", "ETL"]

    run_skill_gap_radar(my_current_stack)