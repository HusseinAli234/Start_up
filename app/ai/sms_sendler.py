import re
import os
from email.message import EmailMessage
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

async def emailProccess(resume_id: int, pdf_text: str, tests_id: int):
    import re

    # Ищем email в тексте с помощью регулярки
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    match = re.search(email_pattern, pdf_text)

    if match:
        email_found = match.group(0)
        subject = f"Результаты обработки резюме #{resume_id}"

    
        frontend_base_url = "http://localhost:3000/test"
        link = f"{frontend_base_url}?resume_id={resume_id}&tests_id={tests_id}"

        content = (
            "Ваше резюме было успешно обработано.\n"
            f"Пожалуйста, пройдите следующий тест: {link}\n\n"
            "Спасибо за использование нашей платформы!"
        )

        await send_email(to_email=email_found, subject=subject, content=content)
        print(f"Email sent to: {email_found}")
    else:
        print("Email not found in PDF text.")

