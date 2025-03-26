import requests
from dotenv import load_dotenv
import os
import re

load_dotenv()

def analyze_resume(resume):
    api_key = os.getenv("API_KEY")
    if not api_key:
        return "API key not found. Check .env file."
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    data = {
        "model": "google/gemini-2.5-pro-exp-03-25:free",
        "messages": [
            {
                "role": "user",
                "content": f"""я тебя сейчас отправлю резюме ты должен вернуть мне в виде json формата основные навыки которые есть в резюме в том числе и soft и hard skill,также отдельно должно быть пояснения по каждому баллу которое ты дал для каждого навыка от 0 до 1 через точку указывай ,БЕЗ ЛИШНИХ СЛОВ ТОЛЬКО ОТКРЫТАЯ СКОБКА ФИГУРНАЯ И НАВЫКИ И ПОТОМ ЗАКРЫВАЙ СКОБКУ,а вот резюме,БУДЬ ОЧЕНЬ СТРОГИМ К АНАЛИЗУ , если навык просто упоминается то ставь ниже 0.3,короче будь как строгий работодатель:
{resume}
"""
            }
        ],
    }
    
    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=data
        )
        response.raise_for_status()
        response_data = response.json()
        content = response_data.get('choices', [{}])[0].get('message', {}).get('content', 'No content')
        match = re.search(r"\{.*\}", content.strip(), re.DOTALL)
        result = match.group(0) if match else None
        return result
    except requests.exceptions.RequestException as e:
        return f"Error: {e}"
