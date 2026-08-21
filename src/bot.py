import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
from src.database import SessionLocal, Vacancy

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or ""
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID") or ""

bot = telebot.TeleBot(TOKEN)

MY_STACK = ["python", "pandas", "numpy", "sql", "postgresql", "power bi", "excel", "machine learning",
                        "mysql", "tableau", "git", "github", "a/b testing", "statistics", "nlp", "api", "ETL"]


def calculate_match_score(vacancy_skills, user_stack):
    if not vacancy_skills:
        return 0

    user_stack_lower = [s.lower() for s in user_stack]
    matched = [s for s in vacancy_skills if s.name.lower() in user_stack_lower]

    return int((len(matched) / len(vacancy_skills)) * 100)


def send_new_vacancies():
    db = SessionLocal()

    new_vacancies = db.query(Vacancy).filter(Vacancy.is_sent == False).all()

    if not new_vacancies:
        bot.send_message(CHAT_ID, "There are no new vacancies now. Try to launch parser later.")
        db.close()
        return

    bot.send_message(CHAT_ID, f"Hello! {len(new_vacancies)} new vacancies have been found. Count your Match Score...")

    for vac in new_vacancies:
        score = calculate_match_score(vac.skills, MY_STACK)

        skill_names = [s.name for s in vac.skills]
        skills_str = ", ".join(skill_names) if skill_names else "There are no clear technical requirements"

        if score >= 70:
            emoji = "🟢"
        elif score >= 40:
            emoji = "🟡"
        else:
            emoji = "🔴"

        company_name = vac.company if vac.company else "Не вказано"
        salary_info = vac.salary if vac.salary else "Не вказано"

        msg_text = (
            f"{emoji} *{score}% MATCH* | {vac.title}\n"
            f"*Компанія:* {company_name}\n"
            f"*Зарплата:* {salary_info}\n"
            f"*Досвід:* {vac.experience}\n" 
            f"*Скіли:* {skills_str}\n"
            f"*Посилання:* https://djinni.co/jobs/{vac.id}"
        )

        markup = InlineKeyboardMarkup()
        btn_apply = InlineKeyboardButton("✅ Apply", callback_data=f"applied_{vac.id}")
        markup.add(btn_apply)

        bot.send_message(CHAT_ID, msg_text, reply_markup=markup, parse_mode="Markdown")

        vac.is_sent = True

    db.commit()
    db.close()
    print("All new vacancies have been sent to Telegram!")


@bot.callback_query_handler(func=lambda call: call.data.startswith('applied_'))
def handle_applied_button(call):
    vac_id = call.data.split('_')[1]

    db = SessionLocal()
    vac = db.query(Vacancy).filter(Vacancy.id == vac_id).first()

    if vac:
        vac.is_applied = True
        db.commit()

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=call.message.text + "\n\n✅ *You have already applied this vacancy!*",
            parse_mode="Markdown"
        )

        bot.answer_callback_query(call.id, "Cool! Vacancy closed in database.")

    db.close()


if __name__ == "__main__":
    send_new_vacancies()

    print("Bot in  sleep mode... (Click Ctrl+F2 to stop)")
    bot.infinity_polling()