import requests
from dotenv import load_dotenv
import os
import re
from openai import OpenAI
import google.generativeai as genai
from google.generativeai import types
load_dotenv()




# base_url = "https://api.aimlapi.com/v1"

# api_key = os.getenv("API_KEY")

# system_prompt = f"""Ты — эксперт по анализу и структурированию данных из резюме. Твоя задача — взять текст резюме и преобразовать его в строго форматированный JSON-объект для хранения в базе данных:
#                 только json без ничего лишнего в таком виде, HARD скилы ОЦЕНИВАЙ ОЧЕНЬ СТРОГО,ЛУЧШЕ ПОСТАВЬ НИЖЕ ЧЕМ ВЫШЕ РЕАЛЬНОГО, а SOFT скилы оценивай просто СТРОГО, не делай описание длинным , пиши только суть , если просто упоминается навык то ставь ниже 20,:
#                 [
#                   "fullname": "string",
#                   "location": "string",
#                   "experience":  [
#                     [
#                       "name": "string",
#                       "description": "string"
#                     ]
#                   ],
#                   "education": [
#                     [
#                       "name": "string",
#                       "description": "string"
#                     ]
#                   ],
#                   "skills": [
#                     [
#                       "title": "string",
#                       "level": "int"(от 0 до 100),
#                       "justification": "string",
#                       "type": "string"("HARD", "SOFT")
#                     ]
#                   ]
#                 ]"""

# api = OpenAI(api_key=api_key, base_url=base_url)


# def analyze_resume(user_prompt:str):
#     completion = api.chat.completions.create(
#         model="gpt-4o-mini-2024-07-18",
#         messages=[
#             {"role": "system", "content": system_prompt},
#             {"role": "user", "content": user_prompt},
#         ],
#         temperature=0.2,
#         max_tokens=2000,
#     )

#     response = completion.choices[0].message.content
#     match = re.search(r"\{.*\}", response.strip(), re.DOTALL)
#     result = match.group(0) if match else None
#     print("AI:", result)
#     return result



def analyze_resume(user_prompt:str):
    client = genai.Client(
        api_key=os.environ.get("GEMINI_API_KEY"),
    )

    model = "gemini-2.5-pro-exp-03-25"
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=user_prompt),
            ],
        ),
    ]
    generate_content_config = types.GenerateContentConfig(
        temperature=0.2,
        response_mime_type="application/json",
        response_schema=genai.types.Schema(
            type = genai.types.Type.ARRAY,
            items = genai.types.Schema(
                type = genai.types.Type.OBJECT,
                required = ["fullname", "location", "experience", "education", "skills"],
                properties = {
                    "fullname": genai.types.Schema(
                        type = genai.types.Type.STRING,
                    ),
                    "location": genai.types.Schema(
                        type = genai.types.Type.STRING,
                    ),
                    "experience": genai.types.Schema(
                        type = genai.types.Type.ARRAY,
                        items = genai.types.Schema(
                            type = genai.types.Type.OBJECT,
                            required = ["name", "description"],
                            properties = {
                                "name": genai.types.Schema(
                                    type = genai.types.Type.STRING,
                                ),
                                "description": genai.types.Schema(
                                    type = genai.types.Type.STRING,
                                ),
                            },
                        ),
                    ),
                    "education": genai.types.Schema(
                        type = genai.types.Type.ARRAY,
                        items = genai.types.Schema(
                            type = genai.types.Type.OBJECT,
                            required = ["name", "description"],
                            properties = {
                                "name": genai.types.Schema(
                                    type = genai.types.Type.STRING,
                                ),
                                "description": genai.types.Schema(
                                    type = genai.types.Type.STRING,
                                ),
                            },
                        ),
                    ),
                    "skills": genai.types.Schema(
                        type = genai.types.Type.ARRAY,
                        items = genai.types.Schema(
                            type = genai.types.Type.OBJECT,
                            required = ["title", "level", "justification", "type"],
                            properties = {
                                "title": genai.types.Schema(
                                    type = genai.types.Type.STRING,
                                ),
                                "level": genai.types.Schema(
                                    type = genai.types.Type.INTEGER,
                                ),
                                "justification": genai.types.Schema(
                                    type = genai.types.Type.STRING,
                                ),
                                "type": genai.types.Schema(
                                    type = genai.types.Type.STRING,
                                    enum = ["HARD", "SOFT"],
                                ),
                            },
                        ),
                    ),
                },
            ),
        ),
        system_instruction=[
            types.Part.from_text(text="""Ты — эксперт по анализу и структурированию данных из резюме. Твоя задача — взять текст резюме и преобразовать его в строго форматированный JSON-объект для хранения в базе данных:
                , HARD скилы ОЦЕНИВАЙ ОЧЕНЬ СТРОГО,ЛУЧШЕ ПОСТАВЬ НИЖЕ ЧЕМ ВЫШЕ РЕАЛЬНОГО, а SOFT скилы оценивай просто СТРОГО, не делай описание длинным , пиши только суть , если просто упоминается навык то ставь ниже 20"""),
        ],
    )

    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=generate_content_config,
    )

    print(response.text)
    return response.text

