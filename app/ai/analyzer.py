import requests
from dotenv import load_dotenv
import os
from app.ai.social_analyzer import social_network_analyzer
from openai import OpenAI
from google import genai
from google.genai import types
import json
load_dotenv()

client = genai.Client(
        api_key=os.environ.get("GEMINI_API_KEY"),
    )

def analyze_resume(user_prompt:str): 
    model = "gemini-2.0-flash"
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=user_prompt),
            ],
        ),
    ]
    generate_content_config = types.GenerateContentConfig(
        temperature=0.4,
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
                                    enum = ["HARD"]
                                ),
                            },
                        ),
                    ),
                },
            ),
        ),
        system_instruction=[
            types.Part.from_text(text="""Ты — эксперт по анализу и структурированию данных из резюме. Твоя задача — взять текст резюме и преобразовать его в строго форматированный JSON-объект для хранения в базе данных:
                , HARD скиллы ОЦЕНИВАЙ ОЧЕНЬ СТРОГО(90 - это Senior, 60 - Middle, 35 - Junior, 15 - Новичок),SOFT СКИЛЛ ,ИХ НЕТУ,ЛУЧШЕ ПОСТАВЬ НИЖЕ ЧЕМ ВЫШЕ РЕАЛЬНОГО, не делай описание длинным , пиши только суть , если просто упоминается навык то ставь ниже 15, 
                                 нужно чтобы данные которые попадут в поле experience были сжаты нужна только основаня ифнормация, а не все что есть в резюме, только поле experience нужно сжать, education и skills оставь как есть, ПИШИ НА АНГЛИЙСКОМ"""),
        ],
    )

    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=generate_content_config,
    )

    # print(response.to_json_dict()['candidates'][0]['content']['parts'][0]['text'])
    json_text = response.to_json_dict()['candidates'][0]['content']['parts'][0]['text']
    
    try:
        parsed_json = json.loads(json_text) 
    except json.JSONDecodeError as e:
        raise ValueError(f"Ошибка декодирования JSON: {e}")
    return parsed_json[0]

