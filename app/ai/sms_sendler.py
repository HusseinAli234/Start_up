import os
from email.message import EmailMessage
from urllib.parse import quote
from dotenv import load_dotenv
from app.ai.social_analyzer import extract_emails_from_resume
from aiosmtplib import send

load_dotenv()

# Отправка email с текстом и HTML
async def send_email(to_email: str, subject: str, plain_text: str, html_content: str):
    message = EmailMessage()
    message["From"] = os.getenv("SMTP_USERNAME")
    message["To"] = to_email
    message["Subject"] = subject

    message.set_content(plain_text)
    message.add_alternative(html_content, subtype="html")

    await send(
        message,
        hostname=os.getenv("SMTP_HOST"),
        port=int(os.getenv("SMTP_PORT")),
        start_tls=True,
        username=os.getenv("SMTP_USERNAME"),
        password=os.getenv("SMTP_PASSWORD"),
    )

# HTML шаблон письма кандидату
def build_candidate_html(resume_id, test_id, resume_name, company_name, position):
    test_id_str = ",".join(map(str, test_id)) if isinstance(test_id, list) else str(test_id)
    safe_resume_name = quote(resume_name)
    link = f"https://sandbox.sdinis.org/test?resume_id={resume_id}&tests_id={test_id_str}&resume_name={safe_resume_name}"

    return f"""
    <html>
    <body style="margin:0;padding:0;background:#f4f4f4;font-family:Arial,sans-serif;">
        <table align="center" width="600" style="background:#fff;padding:20px;border-radius:8px;box-shadow:0 4px 10px rgba(0,0,0,0.1);">
            <tr>
                <td>
                    <h2 style="color:#333;">Здравствуйте, {resume_name}!</h2>
                    <p>Вы подавали заявку на позицию <strong>{position}</strong> в компанию <strong>{company_name}</strong>.</p>
                    <p>Пожалуйста, пройдите тест по ссылке ниже:</p>
                    <p style="text-align:center;margin:30px 0;">
                        <a href="{link}" style="background:#007bff;color:#fff;padding:12px 20px;border-radius:5px;text-decoration:none;">Пройти тест</a>
                    </p>
                    <p>Если кнопка не работает, перейдите по ссылке вручную:</p>
                    <p><a href="{link}" style="color:#007bff;">{link}</a></p>
                    <p>С уважением,<br>Команда <strong>SANDBOX</strong></p>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """

# HTML шаблон письма работодателю
def build_employer_html(resume_id, test_id, resume_name):
    test_id_str = ",".join(map(str, test_id)) if isinstance(test_id, list) else str(test_id)
    safe_resume_name = quote(resume_name)
    link = f"https://sandbox.sdinis.org/test?resume_id={resume_id}&tests_id={test_id_str}&resume_name={safe_resume_name}"

    return f"""
    <html>
    <body style="margin:0;padding:0;background:#f4f4f4;font-family:Arial,sans-serif;">
        <table align="center" width="600" style="background:#fff;padding:20px;border-radius:8px;box-shadow:0 4px 10px rgba(0,0,0,0.1);">
            <tr>
                <td>
                    <h2 style="color:#333;">Оценка бывшего сотрудника</h2>
                    <p>Просим вас оценить сотрудника <strong>{resume_name}</strong>, который указал вас как бывшего работодателя.</p>
                    <p>Пожалуйста, заполните форму по ссылке ниже:</p>
                    <p style="text-align:center;margin:30px 0;">
                        <a href="{link}" style="background:#28a745;color:#fff;padding:12px 20px;border-radius:5px;text-decoration:none;">Оценить кандидата</a>
                    </p>
                    <p>Если кнопка не работает, перейдите по ссылке вручную:</p>
                    <p><a href="{link}" style="color:#28a745;">{link}</a></p>
                    <p>С уважением,<br>Система <strong>SANDBOX</strong></p>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """

# Текстовая версия писем
def build_candidate_text(resume_id, test_id, resume_name, company_name, position):
    test_id_str = ",".join(map(str, test_id)) if isinstance(test_id, list) else str(test_id)
    link = f"https://sandbox.sdinis.org/test?resume_id={resume_id}&tests_id={test_id_str}&resume_name={quote(resume_name)}"
    return (
        f"Уважаемый(ая) {resume_name},\n\n"
        f"Вы подавали на позицию {position} в компанию {company_name}.\n"
        f"Пожалуйста, пройдите тест по ссылке:\n{link}\n\n"
        f"С уважением,\nКоманда SANDBOX"
    )

def build_employer_text(resume_id, test_id, resume_name):
    test_id_str = ",".join(map(str, test_id)) if isinstance(test_id, list) else str(test_id)
    link = f"https://sandbox.sdinis.org/test?resume_id={resume_id}&tests_id={test_id_str}&resume_name={quote(resume_name)}"
    return (
        f"Уважаемый(ая) бывший работодатель,\n\n"
        f"Просим вас оценить кандидата {resume_name}, который указал вас как бывшего работодателя.\n"
        f"Ссылка для прохождения оценки:\n{link}\n\n"
        f"С уважением,\nСистема SANDBOX"
    )

# Основная логика рассылки писем
async def emailProccess(
    resume_id: int,
    pdf_text: str,
    tests_id: int,
    employers_test_id: int,
    resume_name: str,
    company_name: str,
    position: str
):
    try:
        email_data = await extract_emails_from_resume(pdf_text)
    except Exception as e:
        print(f"Ошибка при извлечении email через AI: {e}")
        return

    employee_email = email_data.get("employee_email")
    employer_emails = email_data.get("employer_emails", [])

    subject = f"Уважаемый(ая), отличная новость для Вас!"

    # Отправка кандидату
    if employee_email:
        try:
            await send_email(
                to_email=employee_email,
                subject=subject,
                plain_text=build_candidate_text(resume_id, tests_id, resume_name, company_name, position),
                html_content=build_candidate_html(resume_id, tests_id, resume_name, company_name, position)
            )
            print(f"Email sent to candidate: {employee_email}")
        except Exception as e:
            print(f"Ошибка при отправке письма кандидату: {e}")
    else:
        print("Email кандидата не найден.")

    # Отправка работодателям
    for employer_email in employer_emails:
        try:
            await send_email(
                to_email=employer_email,
                subject=subject,
                plain_text=build_employer_text(resume_id, employers_test_id, resume_name),
                html_content=build_employer_html(resume_id, employers_test_id, resume_name)
            )
            print(f"Email sent to employer: {employer_email}")
        except Exception as e:
            print(f"Ошибка при отправке письма работодателю ({employer_email}): {e}")
