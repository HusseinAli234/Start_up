import requests
from dotenv import load_dotenv
import os
import re
from openai import OpenAI
load_dotenv()




base_url = "https://api.aimlapi.com/v1"

api_key = f"{os.getenv("API_KEY")}"

system_prompt = f"""Ты — эксперт по анализу и структурированию данных из резюме. Твоя задача — взять текст резюме и преобразовать его в строго форматированный JSON-объект для хранения в базе данных:
                только json без ничего лишнего в таком виде,ОЦЕНИВАЙ ОЧЕНЬ СТРОГО,ЛУЧШЕ ПОСТАВЬ НИЖЕ ЧЕМ ВЫШЕ РЕАЛЬНОГО,не делай описание длинным , пиши только суть , если просто упоминается навык то ставь ниже 20,:
                [
                  "fullname": "string",
                  "location": "string",
                  "experience":  [
                    [
                      "name": "string",
                      "description": "string"
                    ]
                  ],
                  "education": [
                    [
                      "name": "string",
                      "description": "string"
                    ]
                  ],
                  "skills": [
                    [
                      "title": "string",
                      "level": "int"(от 0 до 100),
                      "justification": "string",
                      "type": "string"("HARD", "SOFT")
                    ]
                  ]
                ]"""

api = OpenAI(api_key=api_key, base_url=base_url)


def analyze_resume(user_prompt:str):
    completion = api.chat.completions.create(
        model="gpt-4o-mini-2024-07-18",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
        max_tokens=2000,
    )

    response = completion.choices[0].message.content
    match = re.search(r"\{.*\}", response.strip(), re.DOTALL)
    result = match.group(0) if match else None
    print("AI:", result)
    return result


