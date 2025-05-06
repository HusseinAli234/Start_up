from dotenv import load_dotenv
import os
from google import genai
from google.genai import types
import json
from app.schemas.vacancy_schema import SkillSchema
from typing import List # Используем TypedDict для SkillSchema, если не импортирована
import openai
# from sentence_transformers import SentenceTransformer, util

# model = SentenceTransformer('paraphrase-MiniLM-L6-v2')

load_dotenv()
client_GPT = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --- Клиент GenAI ---
try:
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    if not client:
         raise ValueError("Failed to initialize genai.Client.")
except Exception as e:
    print(f"Ошибка инициализации genai.Client: {e}")
    exit()


# def match_profession_semantic(vacancy_title: str, professions: list[str]) -> str:
#     embeddings = model.encode([vacancy_title] + professions, convert_to_tensor=True)
#     similarity_scores = util.pytorch_cos_sim(embeddings[0], embeddings[1:])[0]
#     best_index = similarity_scores.argmax()
#     return professions[best_index]


async def analyze_resume_chatgpt(user_prompt: str, skills: List[SkillSchema], requirements: str):
    required_skill_titles = [skill['title'] if isinstance(skill, dict) else skill.title for skill in skills]
    skills_list_str = ", ".join(required_skill_titles)

    system_prompt = """BE ONE OF THE MOST STRICT RESUME ANALYZER IN THE WORLD ,You are an expert resume analyzer comparing a candidate against a specific job vacancy. Your tasks are:

0. **Determine Expected Level (Seniority) from Job Requirements**
   - Carefully read the 'General Job Requirements' to identify the expected position level (e.g., "Junior", "Middle", "Senior", "Lead").
   - Apply this level as the evaluation context: adjust expectations for depth of experience, independence, leadership, and scope of skills accordingly.
   - This context applies regardless of profession — software developer, designer, marketer, accountant, etc.

1. **Skill Evaluation**
   - Focus *only* on skills listed in 'Required Skills for Evaluation'.
   - For each skill found in the resume:
     * Assign a level (0–100) based on **explicit evidence** in the resume.
     * Calibrate score according to expected job level:
       - For a **Senior** role, assign high scores (90+) only if resume shows leadership, complex projects, or deep responsibility.
       - For a **Junior** role, lower thresholds may be acceptable.
     * Be strict. Vague or short mentions should not be scored highly.
     * Provide a concise 'justification' referencing the resume.
     * Mark all with type "HARD".
   - Omit any required skills not found in the resume.

   **Scoring Guide (universal):**
     - 90–100: Expert-level performance in context of job level (e.g. leading initiatives, high independence, domain mastery).
     - 60–89: Solid experience; clear usage in contextually relevant work.
     - 35–59: Familiar or some exposure; not deep or mature usage.
     - 1–34: Mentioned, but little/no substance.
     - 0: Not found.

2. **Hard Skills Aggregate Score ('hard_total')**
   - Provide 'hard_total' score (0–100) reflecting:
     * Skill match (quantity and quality of required skills found).
     * Proficiency levels.
     * Alignment with expected seniority and responsibilities from job description.
   - Provide a short 'justification' explaining your reasoning.
   - Be strict: if the candidate applies to a Senior role but only shows Junior-level evidence (e.g., internships, no leadership, limited autonomy), hard_total should not exceed 55.
    * Conversely, highlight strong alignment if present.
    adjusted_score = raw_score × level_alignment_multiplier
    level_alignment_multiplier:
    - 0.9 → full match
    - 0.6 → slightly below
    - 0.3 → mismatch (e.g. junior applying to senior)

3. **Data Extraction**
   - Extract 'fullname' and 'location' (fallback to "Not Found").
   - Summarize key experiences and relevant responsibilities under 'experience'.
   - Extract available 'education' details.

4. **Output Format**
   - Return a **single JSON object** strictly matching the given schema.
   - All content must be in English.
   - Do **not** include any extra explanations — return only the JSON.
Output must be a valid JSON object with the following fields:
- fullname: string
- location: string
- hard_total: { total: int, justification: string }
- experience: [{ name: string, description: string }]
- education: [{ name: string, description: string }]
- skills: [{ title: string, level: int, justification: string, type: "HARD" }]
Don't include any explanation or intro text. Just return the JSON.
"""

    user_input = f"""
Resume Text:
{user_prompt}

Required Skills for Evaluation:
{skills_list_str}

General Job Requirements:
{requirements}
"""

    try:
        response = await client_GPT.chat.completions.create(
            model="gpt-4o",  # можно и gpt-3.5-turbo, если бюджет важен
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input},
            ],
            temperature=0.3,
            response_format={ "type": "json_object" }
        )
        raw_json = response.choices[0].message.content
        return json.loads(raw_json)

    except Exception as e:
        raise ValueError(f"ChatGPT API error: {type(e).__name__}: {e}")

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
    model_name = "gemini-2.5-flash-preview-04-17" # Используем flash

    # 1. Подготовка входных данных для ИИ
    required_skill_titles = [skill['title'] if isinstance(skill, dict) else skill.title for skill in skills]
    skills_list_str = ", ".join(required_skill_titles)
    combined_prompt = f"""
Resume Text:
---
{user_prompt}
---

Required Skills for Evaluation :
---
{skills_list_str}
---

General Job Requirements (consider for context, but NOT directly for 'hard_total' score calculation):
---
{requirements}
---

Instruction: Analyze the 'Resume Text' based *only* on the 'Required Skills for Evaluation' list and the 'General Job Requirements'. Extract information and evaluate suitability strictly according to the provided JSON schema and scoring rules defined in the system instructions. Output a single JSON object.
"""

    system_instruction_text = f"""You are an extremely strict resume analyzer. You must compare a candidate’s resume to a vacancy using only the indicators below. Each parameter must be scored based on the following rule: 
- If a required indicator is present in the resume and matches the vacancy requirement exactly → score 100. 
- If a related indicator is present in the resume but differs from the vacancy requirement → score 50. 
- If no relevant indicator is found in the resume → score 0. 
- If an indicator is not listed in the job vacancy → ignore it (do not include in hard_total). 
Each skill must be labeled: "type": "HARD", and include "score" and "justification".

Evaluate only the following indicators grouped by category:

1. Sales Experience:
- 0
- 0–0.6 years
- 1 year
- 1–3 years
- 4–5 years
- 6–8 years
- 9+ years

2. Service Industry Experience:
- 0
- 0–0.6 years
- 1 year
- 1–3 years
- 4–5 years
- 6–8 years
- 9+ years

3. Education:
- High school
- Lyceum
- College (Humanitarian)
- College (Technical)
- College (Medical)
- Higher Education (Humanitarian)
- Higher Education (Technical)
- Higher Education (Economic)
- Higher Education (Medical/Natural sciences)

4. Additional Skills (Software knowledge):
- Saby (СБИС)
- МойСклад
- Контур
- SUBTOTAL
- LiteBox
- Антисклад
- CloudShop
- 1С Торговля и склад

5. Training Courses:
- Sales training
- Business communication training
- Negotiation training

6. Driver’s License:
- Category B
- Category C
- Category D

7. Driving Experience:
- Less than 1 year
- 1–3 years
- 4–5 years
- 6+ years

8. Languages:
- Kyrgyz
- Russian
- English
- Chinese
- Uzbek
- Kazakh

9. Age:
- 16–18
- 18–25
- 26–35
- 35–45
- 46–55
- No preference

10. Marital Status:
- Married (+)
- Single (–)
- Not specified

11. Desired Salary:
- 30,000–40,000 KGS
- 41,000–50,000 KGS
- 51,000–60,000 KGS
- 61,000+ KGS
- % from sales

2. After scoring all skills present both in the resume and in the vacancy:
- Calculate hard_total as the arithmetic mean of only the considered indicators (skip those not required by the employer).
- Adjust hard_total based on seniority match:
  - Exact match → ×0.9
  - Slightly below → ×0.6
  - Major mismatch (e.g. Junior applying to Senior) → ×0.5
  justification should be SHORT in Russian

3. Extract the following data:
- fullname (or "Not Found")
- location (or "Not Found")
- experience (summary of relevant job history)
- education (summary of formal education)

4. Return result in strict JSON format:

{{
  "fullname": "",
  "location": "",
  "experience": "",
  "education": "",
  "skills": [
    {{
      "skill": "",
      "type": "HARD",
      "level": 0,
      "justification": ""
    }}
  ],
  "hard_total": 0,
  "justification": ""
}}

Important rules:
- No assumptions — only explicit content in the resume counts.
- Skip any indicator not listed in the job requirements when calculating hard_total.
- Do not explain outside of the JSON output.
- All output must be in Russian.
"""    # 2. Обновленная системная инструкция
#     system_instruction_text = f"""BE ONE OF THE MOST STRICT RESUME ANALYZER IN THE WORLD ,You are an expert resume analyzer comparing a candidate against a specific job vacancy. Your tasks are:

# 0. **Determine Expected Level (Seniority) from Job Requirements**
#    - Carefully read the 'General Job Requirements' to identify the expected position level (e.g., "Junior", "Middle", "Senior", "Lead").
#    - Apply this level as the evaluation context: adjust expectations for depth of experience, independence, leadership, and scope of skills accordingly.
#    - This context applies regardless of profession — software developer, designer, marketer, accountant, etc.

# 1. **Skill Evaluation**
#    - Focus *only* on skills listed in 'Required Skills for Evaluation'.
#    - For each skill found in the resume:
#      * Assign a level (0–100) based on **explicit evidence** in the resume.
#      * Calibrate score according to expected job level:
#        - For a **Senior** role, assign high scores (90+) only if resume shows leadership, complex projects, or deep responsibility.
#        - For a **Junior** role, lower thresholds may be acceptable.
#      * Be strict. Vague or short mentions should not be scored highly.
#      * Provide a concise 'justification' referencing the resume.
#      * Mark all with type "HARD".
#    - Omit any required skills not found in the resume.

#    **Scoring Guide (universal):**
#      - 90–100: Expert-level performance in context of job level (e.g. leading initiatives, high independence, domain mastery).
#      - 60–89: Solid experience; clear usage in contextually relevant work.
#      - 35–59: Familiar or some exposure; not deep or mature usage.
#      - 1–34: Mentioned, but little/no substance.
#      - 0: Not found.

# 2. **Hard Skills Aggregate Score ('hard_total')**
#    - Provide 'hard_total' score (0–100) reflecting:
#      * Skill match (quantity and quality of required skills found).
#      * Proficiency levels.
#      * Alignment with expected seniority and responsibilities from job description.
#    - Provide a short 'justification' explaining your reasoning.
#    - Be strict: if the candidate applies to a Senior role but only shows Junior-level evidence (e.g., internships, no leadership, limited autonomy), hard_total should not exceed 55.
#     * Conversely, highlight strong alignment if present.
#     adjusted_score = raw_score × level_alignment_multiplier
#     level_alignment_multiplier:
#     - 0.9 → full match
#     - 0.6 → slightly below
#     - 0.3 → mismatch (e.g. junior applying to senior)

# 3. **Data Extraction**
#    - Extract 'fullname' and 'location' (fallback to "Not Found").
#    - Summarize key experiences and relevant responsibilities under 'experience'.
#    - Extract available 'education' details.

# 4. **Output Format**
#    - Return a **single JSON object** strictly matching the given schema.
#    - All content must be in English.
#    - Do **not** include any extra explanations — return only the JSON.
# """

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
        temperature=0.1,
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