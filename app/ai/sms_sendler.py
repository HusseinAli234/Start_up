import re
import os
from email.message import EmailMessage
from app.ai.social_analyzer import extract_emails_from_resume
from aiosmtplib import send
from dotenv import load_dotenv

load_dotenv()  # Подгружаем .env переменные

async def send_email(to_email: str, subject: str, content: str):
    message = EmailMessage()
    message["From"] = os.getenv("SMTP_USERNAME")
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(content)

    await send(
        message,
        hostname=os.getenv("SMTP_HOST"),
        port=int(os.getenv("SMTP_PORT")),
        start_tls=True,
        username=os.getenv("SMTP_USERNAME"),
        password=os.getenv("SMTP_PASSWORD"),
    )

async def emailProccess(resume_id: int, pdf_text: str, tests_id: int, employers_test_id: int):
    try:
        email_data = await extract_emails_from_resume(pdf_text)
    except Exception as e:
        print(f"Ошибка при извлечении email через AI: {e}")
        return

    employee_email = email_data.get("employee_email")
    employer_emails = email_data.get("employer_emails", [])

    # Базовая ссылка на фронтенд
    frontend_base_url = "https://husseinali234.github.io/sandbox-hr/test.html"

    # Шаблон письма
    def build_content(test_id):
        # Если test_id — это список, то превращаем его в строку вида 1,2,3
        if isinstance(test_id, list):
            test_id_str = ",".join(map(str, test_id))
        else:
            test_id_str = str(test_id)

        link = f"{frontend_base_url}?resume_id={resume_id}&tests_id={test_id_str}"
        return (
            "Ваше резюме было успешно обработано.\n"
            f"Пожалуйста, пройдите следующий тест: {link}\n\n"
            "Спасибо за использование нашей платформы!"
        )

    subject = f"Результаты обработки резюме #{resume_id}"

    # Отправка письма сотруднику
    if employee_email:
        try:
            await send_email(
                to_email=employee_email,
                subject=subject,
                content=build_content(tests_id)
            )
            print(f"Email sent to candidate: {employee_email}")
        except Exception as e:
            print(f"Ошибка при отправке письма кандидату: {e}")
    else:
        print("Email кандидата не найден.")

    # Отправка писем работодателям
    for employer_email in employer_emails:
        try:
            await send_email(
                to_email=employer_email,
                subject=subject,
                content=build_content(employers_test_id)
            )
            print(f"Email sent to employer: {employer_email}")
        except Exception as e:
            print(f"Ошибка при отправке письма работодателю ({employer_email}): {e}")


