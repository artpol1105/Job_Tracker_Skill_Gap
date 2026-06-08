import os
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("POSTGRES_URL")
if not DATABASE_URL:
    raise ValueError("POSTGRES_URL hasn`t found in .env")

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class VacancySkill(Base):
    __tablename__ = 'vacancy_skills'

    vacancy_id = Column(String, ForeignKey('vacancies.id', ondelete='CASCADE'), primary_key=True)
    skill_id = Column(Integer, ForeignKey('skills.id', ondelete='CASCADE'), primary_key=True)


class Vacancy(Base):
    __tablename__ = 'vacancies'

    id = Column(String, primary_key=True)
    platform = Column(String, nullable=False)
    title = Column(String, nullable=False)
    company = Column(String)
    salary_min = Column(Integer, nullable=True)
    salary_max = Column(Integer, nullable=True)
    description = Column(Text, nullable=False)
    posted_at = Column(DateTime)
    parsed_at = Column(DateTime)
    is_active = Column(Boolean, default=True)

    skills = relationship("Skill", secondary="vacancy_skills", back_populates="vacancies")


class Skill(Base):
    __tablename__ = 'skills'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)
    category = Column(String)

    vacancies = relationship("Vacancy", secondary="vacancy_skills", back_populates="skills")


def init_db():
    Base.metadata.create_all(engine)
    print("Tables successfully created at PostgreSQL!")


if __name__ == "__main__":
    init_db()