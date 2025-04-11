import requests
from dotenv import load_dotenv
import os
from app.ai.social_analyzer import social_network_analyzer
from openai import OpenAI
from google import genai
from google.genai import types
import json
from app.schemas.vacancy_schema import SkillSchema
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
load_dotenv()

client = genai.Client(
        api_key=os.environ.get("GEMINI_API_KEY"),
    )



# --- Configure your GenAI client here ---
# Example:
# genai.configure(api_key="YOUR_API_KEY")
# client = genai.GenerativeModel(...)
# -----------------------------------------
# Make sure 'client' is initialized before calling the function


async def analyze_resume(user_prompt: str, skills: List[SkillSchema], requirements: str):
    # """
    # Анализирует резюме по заданным навыкам и требованиям, возвращая структурированный JSON,
    # используя client.models.generate_content.

    # Args:
    #     user_prompt: Текст резюме.
    #     skills: Список объектов SkillSchema (должен содержать как минимум 'title').
    #     requirements: Строка с общими требованиями вакансии.

    # Returns:
    #     Словарь с данными из резюме и оценками.

    # Raises:
    #     ValueError: Если ответ ИИ не может быть декодирован как JSON или произошла ошибка API.
    #     AttributeError: Если объект ответа имеет неожиданную структуру.
    # """
    # Модель остается Pro для сложных инструкций
    model_name = "gemini-2.0-flash"

    # 1. Подготовка входных данных для ИИ (остается без изменений)
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

General Job Requirements (consider for 'total' score):
---
{requirements}
---

Instruction: Analyze the 'Resume Text' based *only* on the 'Required Skills for Evaluation' list and the 'General Job Requirements'. Extract information and evaluate suitability strictly according to the provided JSON schema and scoring rules. Output a single JSON object.
"""

    # 2. Системная инструкция (остается без изменений)
    system_instruction_text = f"""You are an expert resume analyzer comparing a candidate against specific job criteria. Your tasks are:
1.  Parse the provided 'Resume Text' (within the combined prompt) into the specified JSON format.
2.  **Skill Evaluation:**
    * Focus *exclusively* on the skills listed in 'Required Skills for Evaluation'. Do NOT evaluate skills not on this list.
    * For each skill from the 'Required Skills for Evaluation' list *found* in the resume, assign a 'level' score from 0 to 100 based *only* on resume evidence.
    * **Scoring Guide (0-100):** 90+ (Expert/Senior, strong demonstrated experience), 60-89 (Proficient/Middle, clear application shown), 35-59 (Familiar/Junior, some experience or mention), 1-34 (Basic Awareness, minimal mention), 0 (Not Found in resume). Be strict: prefer lower scores if evidence is weak.
    * Provide a brief 'justification' for each score, citing resume evidence.
    * Mark these evaluated skills with type 'HARD'. If a required skill is not found, do not include it in the output 'skills' list.
3.  **Overall Score ('total'):**
    * Calculate a 'total' score from 0 to 100 representing the candidate's *overall* match for the role based *only* on the provided resume text, the evaluated required skills (presence and level), and alignment with the 'General Job Requirements'. This is a holistic assessment.
4.  **Data Extraction:**
    * Extract 'fullname' and 'location' if available. If missing, use appropriate placeholders like "Not Found".
    * Summarize 'experience' entries concisely, focusing on key responsibilities/achievements relevant to the requirements.
    * Extract 'education' details as found.
5.  **Output:** Generate a single JSON object adhering strictly to the schema. Ensure all text in the JSON is in English. Do not add any explanatory text before or after the JSON object.
"""

    # 3. Конфигурация запроса к ИИ (как в вашем первом рабочем коде)
    contents = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=combined_prompt)],
        ),
    ]

    # Определяем схему ответа (ОБЪЕКТ, а не массив)
    response_schema = types.Schema(
        type=types.Type.OBJECT,
        required=["fullname", "location", "total", "experience", "education", "skills"],
        properties={
            "fullname": types.Schema(type=types.Type.STRING),
            "location": types.Schema(type=types.Type.STRING),
            "total": types.Schema(
                type=types.Type.INTEGER,
                description="Overall match score (0-100) based on skills and requirements."
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

    # !!! Возвращаем system_instruction внутрь GenerateContentConfig !!!
    generate_content_config = types.GenerateContentConfig(
        temperature=0.3,
        response_mime_type="application/json", # Включаем JSON режим
        response_schema=response_schema,      # Передаем схему
        # !!! System instruction здесь, как в вашем первом коде !!!
        system_instruction=[
            types.Part.from_text(text=system_instruction_text)
        ]
    )

    # 4. Вызов ИИ (!!! Используем client.models.generate_content !!!)
    try:
        response = await client.aio.models.generate_content(
            # !!! Модель указывается с префиксом 'models/' !!!
            model=f'{model_name}',
            contents=contents,
            # !!! Передаем объект config !!!
            config=generate_content_config,
        )

        # Анализ ответа от client.models.generate_content
        # Пробуем сначала .text, так как JSON режим может его предоставлять
        if hasattr(response, 'text') and response.text:
             json_text = response.text
        else:
             # Если .text нет или пустой, пробуем старый метод доступа
             # (менее надежен с JSON режимом, но соответствует структуре ответа из вашего первого кода)
             try:
                  # Доступ к тексту через структуру кандидатов
                  json_text = response.candidates[0].content.parts[0].text
                  # print("Warning: Used candidate parsing, might be less reliable with JSON mode.") # Можно убрать для чистоты
             except (AttributeError, IndexError, TypeError) as e:
                  # Ловим возможные ошибки доступа к частям ответа
                  print(f"Error accessing response parts via candidates structure. Response: {response}. Error: {e}")
                  raise ValueError("Could not extract text from AI response using known methods.")


    except Exception as e:
        # Обработка общих ошибок API вызова
        print(f"Error during Gemini API call with client.models.generate_content: {type(e).__name__}: {e}")
        # Дополнительно можно проверить тип ошибки, если нужно специфическое поведение
        raise ValueError(f"Error during AI generation: {e}")


    # 5. Парсинг ответа (остается без изменений, ожидаем объект)
    try:
        parsed_json = json.loads(json_text)
        if not isinstance(parsed_json, dict):
             # Дополнительная проверка, что результат - это словарь
             raise json.JSONDecodeError(f"Response is not a JSON object (got {type(parsed_json)})", json_text, 0)

    except json.JSONDecodeError as e:
        print(f"Raw AI response that failed JSON parsing:\n---\n{json_text}\n---")
        raise ValueError(f"Ошибка декодирования JSON: {e}. Ответ ИИ: {json_text}")
    except Exception as e:
        print(f"Unexpected error during JSON parsing: {e}")
        raise ValueError(f"Unexpected error parsing JSON: {e}")
    # print(parsed_json) 
    return parsed_json



