import asyncio
import tempfile
import os
from dotenv import load_dotenv
import plotly.graph_objects as go
from google.cloud import storage
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from datetime import datetime
from reportlab.platypus import ListFlowable, ListItem

from pathlib import Path

load_dotenv()
BASE_DIR = Path(__file__).resolve().parents[2]
font_path = BASE_DIR / "util/arialmt.ttf"

pdfmetrics.registerFont(TTFont('Arial', str(font_path)))

def _create_resume_analysis_chart(resume, filename: str):
    labels = ["Анализ CV", "Анализ Соц-сетей", "Итоги Опросников","Отзыв бывших работодателей"]
    values = [
        resume.hard_total.total if resume.hard_total else 0,
        resume.soft_total.total if resume.soft_total else 0,
        resume.test_total.total if resume.test_total else 0,
        resume.feedback_total.total if resume.feedback_total else 0,
    ]
    justifications = [
        resume.hard_total.justification if resume.hard_total else "Нет данных",
        resume.soft_total.justification if resume.soft_total else "Нет данных",
        resume.test_total.justification if resume.test_total else "Нет данных",
        resume.feedback_total.justification if resume.feedback_total else "Нет данных",
    ]

    fig = go.Figure(data=[
        go.Bar(
            x=labels,
            y=values,
            text=[f"{v}%" for v in values],
            textposition='auto',
            hovertext=justifications,
            hoverinfo='text'
        )
    ])
    fig.update_layout(
        title="Результаты анализа резюме",
        yaxis=dict(title="Оценка (0–100)"),
        xaxis=dict(title="Категория"),
        height=400
    )
    fig.write_image(filename, format="png", width=700, height=400)

# Асинхронная обёртка
async def create_resume_analysis_chart(resume, filename: str):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _create_resume_analysis_chart, resume, filename)

# Функция генерации PDF
def _generate_resume_pdf(pdf_path: str, chart_path: str, resume):
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        rightMargin=50,
        leftMargin=50,
        topMargin=50,
        bottomMargin=50
    )

    styles = getSampleStyleSheet()

    # Настройка собственных стилей
    styles.add(ParagraphStyle(
    name='MyTitle', 
    fontName='Arial',
    fontSize=18,
    leading=22,
    alignment=TA_CENTER,
    spaceAfter=20
    ))

    styles.add(ParagraphStyle(
        name='SectionTitle',
        fontName='Arial',
        fontSize=14,
        leading=18,
        alignment=TA_LEFT,
        spaceBefore=14,
        spaceAfter=6
    ))

    styles.add(ParagraphStyle(
        name='Text',
        fontName='Arial',
        fontSize=11,
        leading=14,
        alignment=TA_LEFT
    ))

    styles.add(ParagraphStyle(
        name='Footer',
        fontName='Arial',
        fontSize=9,
        leading=11,
        alignment=TA_CENTER,
        textColor='grey'
    ))

    Story = []

    # Заголовок
    Story.append(Paragraph(f"Анализ резюме: {resume.fullname}", styles['MyTitle']))

    # Дата
    current_date = datetime.now().strftime("%d.%m.%Y")
    Story.append(Paragraph(f"Дата анализа: {current_date}", styles['Text']))
    Story.append(Spacer(1, 12))

    # График
    Story.append(Paragraph("Диаграмма оценки:", styles['SectionTitle']))
    Story.append(Image(chart_path, width=6*inch, height=3*inch))
    Story.append(Spacer(1, 10))
    Story.append(HRFlowable(width="100%", thickness=1, color="#cccccc"))
    Story.append(Spacer(1, 12))

    # Пояснения по каждой категории
    categories = [
        "-Анализ CV", 
        "-Анализ Социальных сетей", 
        "-Результаты опросника на выявление личностных качеств", 
        "-Отзывы бывших работодателей"
    ]

    justifications = [
        resume.hard_total.justification if resume.hard_total else "Нет данных",
        resume.soft_total.justification if resume.soft_total else "Нет данных",
        resume.test_total.justification if resume.test_total else "Нет данных",
        resume.feedback_total.justification if resume.feedback_total else "Нет данных"
    ]

    # Выделение скиллов с уровнем -1
    negative_skills = [s.title for s in getattr(resume, "skills", []) if s.level == -1]

    # Подготовим форматированный список, если скиллы есть
    skills_list_flowable = None
    if negative_skills:
        skills_list = [ListItem(Paragraph(skill, styles['Text'])) for skill in negative_skills]
        skills_list_flowable = ListFlowable(
            skills_list,
            bulletType='bullet',
            leftIndent=20
        )

    for i, (cat, justification) in enumerate(zip(categories, justifications)):
        Story.append(Paragraph(cat + ":", styles['SectionTitle']))
        Story.append(Paragraph(justification.replace("\n", "<br/>"), styles['Text']))
        if i == 3 and skills_list_flowable:  # Добавляем список только к последнему разделу
            Story.append(Spacer(1, 6))
            Story.append(Paragraph("Характеристики от бывших работодателей:", styles['Text']))
            Story.append(skills_list_flowable)
        Story.append(Spacer(1, 10))

    Story.append(HRFlowable(width="100%", thickness=1, color="#cccccc"))
    Story.append(Spacer(1, 20))

    # Подпись/авторство
    Story.append(Paragraph("Отчет сгенерирован автоматически системой анализа резюме", styles['Footer']))
    Story.append(Paragraph("© Sandbox, 2025", styles['Footer']))

    doc.build(Story)

# Обновлённая асинхронная генерация PDF для одного резюме
async def generate_pdf_for_single_resume(resume) -> str:
    # Создаём временный PDF-файл
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
        pdf_path = tmp_pdf.name

    # Создаём временный файл для графика
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_img:
        chart_path = tmp_img.name

    # Генерируем диаграмму
    await create_resume_analysis_chart(resume, chart_path)

    # Рисуем PDF
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _generate_resume_pdf, pdf_path, chart_path, resume)

    # Удаляем временный PNG
    os.remove(chart_path)

    return pdf_path

async def upload_pdf_to_gcs(local_path: str, destination_blob_name: str) -> str:
    credentials_path = "school-kg-7bd58d53b816.json"
    bucket_name = os.getenv("GCS_BUCKET_NAME", "your-default-bucket-name")

    def _upload():
        client = storage.Client.from_service_account_json(credentials_path)
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)
        blob.upload_from_filename(local_path, content_type="application/pdf")
        return f"gs://{bucket_name}/{destination_blob_name}"

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _upload)  
