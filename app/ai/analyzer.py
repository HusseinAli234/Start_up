import requests
from dotenv import load_dotenv
import os
from google import genai
from google.genai import types
import json
from app.schemas.vacancy_schema import SkillSchema
from typing import List, TypedDict # Используем TypedDict для SkillSchema, если не импортирована

load_dotenv()

# --- Клиент GenAI ---
try:
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    if not client:
         raise ValueError("Failed to initialize genai.Client.")
except Exception as e:
    print(f"Ошибка инициализации genai.Client: {e}")
    exit()


async def analyze_resume(user_prompt: str, skills: List[SkillSchema], requirements: str):
    """
    Анализирует резюме по заданным навыкам и требованиям, возвращая структурированный JSON,
    используя асинхронный client.aio.models.generate_content.

    Args:
        user_prompt: Текст резюме.
        skills: Список объектов SkillSchema (должен содержать как минимум 'title').
        requirements: Строка с общими требованиями вакансии.

    Returns:
        Словарь с данными из резюме и оценками.

    Raises:
        ValueError: Если ответ ИИ не может быть декодирован как JSON или произошла ошибка API.
    """
    # Вы можете выбрать модель 'gemini-1.5-pro-latest' для лучших результатов, если Flash не справляется
    model_name = "gemini-2.0-flash" # Используем flash как в вашем коде

    # 1. Подготовка входных данных для ИИ
    required_skill_titles = [skill['title'] if isinstance(skill, dict) else skill.title for skill in skills]
    skills_list_str = ", ".join(required_skill_titles)
    combined_prompt = f"""
Resume Text:
---
{user_prompt}
---

Required Skills for Evaluation (evaluate ONLY these):
---
{skills_list_str}
---

General Job Requirements (consider for context, but NOT directly for 'hard_total' score calculation):
---
{requirements}
---

Instruction: Analyze the 'Resume Text' based *only* on the 'Required Skills for Evaluation' list and the 'General Job Requirements'. Extract information and evaluate suitability strictly according to the provided JSON schema and scoring rules defined in the system instructions. Output a single JSON object.
"""

    # 2. Обновленная системная инструкция
    system_instruction_text = f"""You are an expert resume analyzer comparing a candidate against specific job criteria. Your tasks are:
1.  Parse the provided 'Resume Text' (within the combined prompt) into the specified JSON format.
2.  **Skill Evaluation:**
    * Focus *exclusively* on the skills listed in 'Required Skills for Evaluation'. Do NOT evaluate skills not on this list.
    * For each skill from the 'Required Skills for Evaluation' list *found* in the resume, assign a 'level' score from 0 to 100 based *only* on resume evidence.
    * **Scoring Guide (0-100):** 90+ (Expert/Senior, strong demonstrated experience), 60-89 (Proficient/Middle, clear application shown), 35-59 (Familiar/Junior, some experience or mention), 1-34 (Basic Awareness, minimal mention), 0 (Not Found in resume). Be strict: prefer lower scores if evidence is weak.
    * Provide a brief 'justification' for each individual skill's score, citing resume evidence.
    * Mark these evaluated skills with type 'HARD'. If a required skill is not found, do not include it in the output 'skills' list.
3.  **Hard Skills Aggregate Score ('hard_total'):**
    * Calculate a 'hard_total' score object representing the candidate's match *specifically based on the required hard skills listed*.
    * Inside 'hard_total', provide a 'total' score from 0 to 100.
    * This aggregate 'total' score should primarily consider:
        * How many of the 'Required Skills for Evaluation' were found in the resume.
        * The proficiency ('level') achieved for those found skills.
    * Do *not* heavily weigh general requirements (like years of experience, overall education unless directly proving a skill) for *this specific* 'hard_total' score; focus solely on the evidence for the required hard skills.
    * Inside 'hard_total', provide a 'justification' string briefly explaining *why this aggregate hard skill score* was given (e.g., "Strong proficiency in Python/Django, basic Docker knowledge, missing AWS, results in score X").
4.  **Data Extraction:**
    * Extract 'fullname' and 'location' if available. If missing, use appropriate placeholders like "Not Found".
    * Summarize 'experience' entries concisely, focusing on key responsibilities/achievements relevant to the requirements.
    * Extract 'education' details as found.
5.  **Output:** Generate a single JSON object adhering strictly to the schema. Ensure all text in the JSON is in English. Do not add any explanatory text before or after the JSON object.
"""

    # 3. Конфигурация запроса к ИИ
    contents = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=combined_prompt)],
        ),
    ]

    # Определяем схему ответа (с обновленным hard_total)
    response_schema = types.Schema(
        type=types.Type.OBJECT,
        # !!! Обновляем required: 'total' заменен на 'hard_total' !!!
        required=["fullname", "location", "hard_total", "experience", "education", "skills"],
        properties={
            "fullname": types.Schema(type=types.Type.STRING),
            "location": types.Schema(type=types.Type.STRING),
            "hard_total": types.Schema(
                type=types.Type.OBJECT,
                required=["total", "justification"],
                properties={
                    "total": types.Schema(type=types.Type.INTEGER, description="Aggregate score (0-100) based ONLY on required hard skills found and their levels."),
                    "justification": types.Schema(type=types.Type.STRING, description="Brief explanation for the aggregate hard_total score."),
                },
                description="Overall assessment based purely on the required hard skills."
            ),
            "experience": types.Schema(
                type=types.Type.ARRAY,
                items=types.Schema(
                    type=types.Type.OBJECT,
                    required=["name", "description"],
                    properties={
                        "name": types.Schema(type=types.Type.STRING),
                        "description": types.Schema(type=types.Type.STRING, description="Summarized key info"),
                    },
                ),
            ),
            "education": types.Schema(
                type=types.Type.ARRAY,
                items=types.Schema(
                    type=types.Type.OBJECT,
                    required=["name", "description"],
                    properties={
                        "name": types.Schema(type=types.Type.STRING),
                        "description": types.Schema(type=types.Type.STRING),
                    },
                ),
            ),
            "skills": types.Schema(
                type=types.Type.ARRAY,
                description="ONLY includes skills from the required list found in the resume, with 0-100 level.",
                items=types.Schema(
                    type=types.Type.OBJECT,
                    required=["title", "level", "justification", "type"],
                    properties={
                        "title": types.Schema(type=types.Type.STRING),
                        "level": types.Schema(
                            type=types.Type.INTEGER,
                            description="Proficiency score (0-100) based on resume evidence."
                        ),
                        "justification": types.Schema(type=types.Type.STRING),
                        "type": types.Schema(
                            type=types.Type.STRING,
                            enum=["HARD"]
                        ),
                    },
                ),
            ),
        },
    )

    generate_content_config = types.GenerateContentConfig(
        temperature=0.3,
        response_mime_type="application/json",
        response_schema=response_schema,
        system_instruction=[
            types.Part.from_text(text=system_instruction_text)
        ]
    )

    # 4. Асинхронный вызов ИИ
    try:
        # !!! Используем await и client.aio !!!
        response = await client.aio.models.generate_content(
             # Убираем 'models/' префикс для aio вызова, как в вашем коде
            model=f'{model_name}',
            contents=contents,
            config=generate_content_config,
        )

        # Анализ ответа
        if hasattr(response, 'text') and response.text:
             json_text = response.text
        else:
             try:
                  json_text = response.candidates[0].content.parts[0].text
             except (AttributeError, IndexError, TypeError) as e:
                  print(f"Error accessing response parts via candidates structure. Response: {response}. Error: {e}")
                  raise ValueError("Could not extract text from AI response using known methods.")

    except Exception as e:
        print(f"Error during Gemini API call with client.aio.models.generate_content: {type(e).__name__}: {e}")
        raise ValueError(f"Error during AI generation: {e}")

    # 5. Парсинг ответа
    try:
        parsed_json = json.loads(json_text)
        if not isinstance(parsed_json, dict):
             raise json.JSONDecodeError(f"Response is not a JSON object (got {type(parsed_json)})", json_text, 0)

    except json.JSONDecodeError as e:
        print(f"Raw AI response that failed JSON parsing:\n---\n{json_text}\n---")
        raise ValueError(f"Ошибка декодирования JSON: {e}. Ответ ИИ: {json_text}")
    except Exception as e:
        print(f"Unexpected error during JSON parsing: {e}")
        raise ValueError(f"Unexpected error parsing JSON: {e}")

    return parsed_json