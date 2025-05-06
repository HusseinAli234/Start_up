import re
import requests
import time
import json 
from dotenv import load_dotenv
import os
from google import genai
from google.genai import types
import json
import logging
from typing import Dict
logger = logging.getLogger(__name__)
load_dotenv()
import asyncio
import httpx


client = genai.Client(
        api_key=os.environ.get("GEMINI_API_KEY"),
    )

SELLER_INSTRUCTION = """
You are an expert Occupational Psychologist and HR Analyst specializing in evaluating candidates for SALES roles using scraped social-media text data.
Your task is to compute quantitative metrics for both SOFT and HARD skills based strictly on predefined patterns, symbols, and semantic synonyms, then output a structured JSON summary.

Input:
A single string of scraped social-media text (posts, comments, bios).

Total Tokens:
total_tokens = total words + total emoji characters

Skill Definitions & Patterns (allow synonyms and semantically similar terms):

1. HARD Skills (type="HARD")
   • Keywords & synonyms: sales, realization, sbyt, CRM, client base, presentation, assortment, product, commission, rate, etc.
   • hard_skill_count = sum of weighted matches (each match weight = 1)
   • Use Laplace smoothing with α = 5:
       hard_skill_level = round(((hard_skill_count + α) / (total_tokens + α)) * 100)
     (Ensures non-zero even when hard_skill_count is small)

2. SOFT Skills (type="SOFT")
   For each dimension below:
     a. Count only weighted triggers (strong markers = 2 points, weak markers = 1 point)
     b. raw_pct = (weighted_count / total_tokens) * 100
     c. benchmark_pct = {{Communicability: 20, Proactiveness: 15, Clarity: 10, Negativism: 10, Expressiveness: 8,Emotional Expressiveness:10,Humor:15,Creativity:15}}[skill]
     d. scaled_pct = min(100, raw_pct / benchmark_pct * 100)
     e. Apply minimum floor_threshold = 5%:
          level = max(scaled_pct, floor_threshold)
     f. (Optional nonlinear boost—e.g. sqrt):
          level = round( sqrt(level / 100) * 100 )


   a. Communicability / Friendliness
      – Adjectives or synonyms indicating warmth, politeness, gratitude (kind, helpful, appreciative, encouraging)
      – Positive emojis: 😊 🙂 ❤️

   b. Activity / Proactiveness
      – Action verbs or similar (achieve, lead, create, follow up, organize, initiate)
      – Indicators of replies/mentions (“@username”, “reply”, “responded”)

   c. Goal Specification / Clarity
      – Precision adverbs or equivalents (clearly, specifically, definitely, exactly, concretely)
      – Structural markers: bullets (“- ”, “• ”), numbered lists (“1.”, “a)”), headings

   d. Negativism / Irritability
      – Negative words or synonyms (hate, annoy, stupid, ugh, awful, fed up)
      – “!!!” or “???” sequences, ALL-CAPS phrases
      – Negative emojis: 😡 🤬 🙄

   e. Emotional Expressiveness (Emoji Use)
      – emoji_char_pct = (total emojis / total characters) × 100
      – Ideal range = 3–10%; if >15%, flag but still score

   f. Humor (optional)
      – Informal shorthand or equivalents (lol, lmao, bruh, 😂, 🤣, 😅)

   g. Creativity (optional)
      – Metaphors (“like a …”), storytelling cues, unique formatting

Output Format (exact JSON, no extras):

{{
  "soft_total": {{
    "total": <integer 0–100>,
    "justification": "<summary of soft-skill profile in Russian>"
  }},
  "skills": [
    {{
      "title": "<Skill Name>",
      "level": <integer 0–100>,
      "justification": "<brief example-based rationale in Russian>",
      "type": "SOFT" or "HARD"
    }}
    // one entry per defined skill
  ]
}}

Insufficient Data:
If total_tokens < 20, return:
{{
  "soft_total": {{
    "total": 0,
    "justification": "Insufficient data provided for analysis in Russian"
  }},
  "skills": []
}}

Important:
– Use only the specified patterns and their semantic synonyms.
– Do not infer beyond observed tokens.
– All output keys and strings must be in Russian.

"""        

async def extract_social_media_links_json(text):
    """Extracts social media profile links from text."""
    social_media_patterns = {
        "facebook": r"(?:https?:\/\/)?(?:www\.)?facebook\.com\/[A-Za-z0-9_\-\.]+/?",
        "twitter": r"(?:https?:\/\/)?(?:www\.)?(?:x\.com|twitter\.com)\/[A-Za-z0-9_]+/?",
        "instagram": r"(?:https?:\/\/)?(?:www\.)?instagram\.com\/[A-Za-z0-9_\-\.]+/?",
        "linkedin": r"(?:https?:\/\/)?(?:www\.)?linkedin\.com\/(?:in|company)\/[a-zA-Z0-9\-]+(?:-[a-zA-Z0-9]+)*\/?",
    }

    social_media_links = {}
    for platform, pattern in social_media_patterns.items():
       
        matches = re.findall(pattern, text, re.IGNORECASE) 
        if matches:
         
            link = matches[0].rstrip('/')
            social_media_links[platform] = link

    return social_media_links



async def process_platform(platform, link, dataset_id_map, api_key, bucket_name, max_retries=3):
    summary = ""
    if platform not in dataset_id_map:
        return f"  -> Warning: No dataset_id configured for platform '{platform}'. Skipping.\n"
    
    current_dataset_id = dataset_id_map[platform]
    input_data = [{"url": link}]
    trigger_payload = {
        "deliver": {
            "type": "s3",
            "filename": {"template": f"{platform}_{{[snapshot_id]}}", "extension": "json"},
            "bucket": bucket_name,
            "directory": ""
        },
        "input": input_data,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    for attempt in range(1, max_retries + 1):
        async with httpx.AsyncClient() as client:
            try:
                print(f"     Attempt {attempt} for {platform}")
                # Step 1: Trigger
                trigger_response = await client.post(
                    "https://api.brightdata.com/datasets/v3/trigger",
                    headers=headers,
                    params={"dataset_id": current_dataset_id, "include_errors": "true"},
                    json=trigger_payload
                )
                trigger_response.raise_for_status()
                snapshot_id = trigger_response.json().get("snapshot_id")

                if not snapshot_id:
                    raise ValueError("Missing snapshot_id in trigger response")

                # Step 2: Polling
                while True:
                    progress_response = await client.get(
                        f"https://api.brightdata.com/datasets/v3/progress/{snapshot_id}",
                        headers={"Authorization": f"Bearer {api_key}"}
                    )
                    progress_response.raise_for_status()
                    status = progress_response.json().get("status", "unknown")

                    if status == "ready":
                        result_response = await client.get(
                            f"https://api.brightdata.com/datasets/v3/snapshot/{snapshot_id}",
                            headers={"Authorization": f"Bearer {api_key}"},
                            params={"format": "json", "batch_size": 1500}
                        )
                        result_response.raise_for_status()
                        json_data = result_response.json()

                        if not json_data:
                            return f"{platform}: Empty result."

                        cleaned_data = {
                            key: (value[:3] if isinstance(value, list) and value else value)
                            for key, value in json_data[0].items()
                        }
                        summary += f"\"{platform}\": " + json.dumps(cleaned_data, ensure_ascii=False, indent=4) + "\n"
                        print(f"     Finished for {platform}")
                        return summary

                    elif status in ["failed", "unknown"]:
                        raise RuntimeError(f"Status for {platform} is '{status}'")

                    else:
                        print(f"     Waiting on {platform}...")
                        await asyncio.sleep(5)

            except Exception as e:
                print(f"     [Attempt {attempt}] Error for {platform}: {e}")
                if attempt < max_retries:
                    await asyncio.sleep(3)  # маленький бэкофф
                    continue
                else:
                    return f"{platform}: Failed after {max_retries} attempts. Last error: {str(e)}"



async def social_network_analyzer(text_to_extract):
    dataset_id_map = {
        "instagram": "gd_l1vikfch901nx3by4",
        "linkedin": "gd_l1viktl72bvl7bjuj0",
        "facebook": "gd_lkaxegm826bjpoo9m5",
        "twitter": "gd_lwxmeb2u1cniijd7t4",
    }

    BRIGHTDATA_API_KEY = "259e983b7ec9d9c06f559edf8eff81cf9a3c7cd73536f42617542dcbecde00f2"
    S3_BUCKET_NAME = "start_up"

    extracted_links = await extract_social_media_links_ai(text_to_extract)
    if not extracted_links:
        return "No social media links found."
    tasks = [
        process_platform(platform, link, dataset_id_map, BRIGHTDATA_API_KEY, S3_BUCKET_NAME)
        for platform, link in extracted_links.items()
    ]

    results = await asyncio.gather(*tasks)
    return "\n".join(results)

async def extract_social_media_links_ai(text: str) -> Dict[str, str]:
    prompt = f"""
You are a smart AI that extracts social media profile links from text. Return a JSON dictionary with keys as platforms (facebook, instagram, linkedin, x) and values as the first URL found in the text for each platform (if any).

If a link is not found for a platform, do not include that key.

Example format:
{{
  "linkedin": "https://linkedin.com/in/example",
  "x": "https://x.com/example",
  "instagram":"https://instagram.com/example"
  "facebook":"https://facebook.com/example"
}}

Return a JSON dictionary where keys are lowercase platform names: "facebook", "x", "instagram", "linkedin".

Values must be full URLs starting with **https://** and without a trailing slash.


Text:
{text}
"""

    try:
        response = await client.aio.models.generate_content(
            model="gemini-1.5-flash-8b",
            contents=[types.Content(role="user", parts=[types.Part.from_text(text=prompt)])],
            config=types.GenerateContentConfig(
                temperature=0.2,
                response_mime_type="application/json"
            )
        )

        # Преобразуем результат в словарь
        import json
        return json.loads(response.text)

    except Exception as e:
        print(f"Ошибка при извлечении ссылок через AI: {e}")
        return {}

async def analyze_survey(metodology: str,result:float) -> str:
    prompt = f"""

METHODOLOGY: 
{metodology}
"""

    model = "gemini-2.0-flash"
    try:
        response = await client.aio.models.generate_content(
            model=model,
            contents=[types.Content(role="user", parts=[types.Part.from_text(text=prompt)])] ,
            config=types.GenerateContentConfig(
                temperature=0.4,
                response_mime_type="text/plain"
            ),
        )

        # Извлекаем ответ
        text = response.text
        return text
    except Exception as e:
        print(f"Error in metodology analysis: {e}")
        return "sorry don't have any analyze"  # fallback на дефолт

async def analyze_proffesion(title: str, description: str, requirement: str) -> str:
    prompt = f"""
You are an HR expert. Given the job title, description, and requirements, classify the job into one of the following categories:

- IT
- salesman
- salesman of IT-product
- manager

Only return one of the exact strings above. Do not explain.

Title: {title}
Description: {description}
Requirements: {requirement}
"""

    model = "gemini-2.0-flash"
    try:
        response = await client.aio.models.generate_content(
            model=model,
            contents=[types.Content(role="user", parts=[types.Part.from_text(text=prompt)])] ,
            config=types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type="text/plain"
            ),
        )

        # Извлекаем ответ
        text = response.text.strip().lower()
        # allowed = {"it", "salesman", "manager","salesman of it-product"}
        allowed = {"salesman"}

        # Валидация
        if text not in allowed:
            return "salesman"
            # raise ValueError(f"Invalid classification returned: {text}")
        print(text)
        return text

    except Exception as e:
        print(f"Error in profession analysis: {e}")
        return "salesman"  # fallback на дефолт

     
async def extract_emails_from_resume(pdf_info: str):
    model = "gemini-2.0-flash"

    system_instruction = """
You are an AI assistant helping a recruiter extract email addresses from a candidate's resume. Your task is to find:
1. The candidate's personal email address.
2. A list of email addresses that appear to belong to employers (e.g., company domains, HR contacts, supervisors).

Rules:
- If multiple personal emails are found, choose the one that clearly belongs to the candidate.
- For employer emails, return a list of unique company-related email addresses.
- If no data is found, return null for the personal email and an empty list for employers.

Output format (JSON):
{
  "employee_email": "example@gmail.com",
  "employer_emails": ["hr@company.com", "lead@techcorp.com" , "example@gmail.com"]
}
If nothing found:
{
  "employee_email": null,
  "employer_emails": []
}
"""

    contents = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=pdf_info)],
        ),
    ]

    generate_content_config = types.GenerateContentConfig(
        temperature=0.2,
        response_mime_type="application/json",
        system_instruction=[types.Part.from_text(text=system_instruction)],
        response_schema=genai.types.Schema(
            type=genai.types.Type.OBJECT,
            required=["employee_email", "employer_emails"],
            properties={
                "employee_email": genai.types.Schema(
                    type=genai.types.Type.STRING,
                    description="Candidate's email address, or null if not found.",
                    nullable=True,
                ),
                "employer_emails": genai.types.Schema(
                    type=genai.types.Type.ARRAY,
                    description="List of employer/company email addresses.",
                    items=genai.types.Schema(type=genai.types.Type.STRING),
                ),
            },
        ),
    )

    try:
        response = await client.aio.models.generate_content(
            model=model,
            contents=contents,
            config=generate_content_config,
        )

        if hasattr(response, 'text') and response.text:
            json_text = response.text
        else:
            try:
                json_text = response.candidates[0].content.parts[0].text
            except (AttributeError, IndexError, TypeError) as e:
                print(f"Error accessing response parts via candidates. Error: {e}")
                raise ValueError("Could not extract text from AI response.")

    except Exception as e:
        print(f"Gemini API call failed: {type(e).__name__}: {e}")
        raise ValueError(f"AI generation error: {e}")

    try:
        parsed_json = json.loads(json_text)
        if not isinstance(parsed_json, dict):
            raise json.JSONDecodeError("Not a JSON object", json_text, 0)
    except json.JSONDecodeError as e:
        print(f"JSON decode error:\n---\n{json_text}\n---")
        raise ValueError(f"JSON decoding error: {e}. AI response: {json_text}")
    except Exception as e:
        print(f"Unexpected error parsing JSON: {e}")
        raise ValueError(f"Unexpected JSON parsing error: {e}")

    print(parsed_json)
    return parsed_json
    


async def analyze_social(pdf_info:str,title:str,description:str,requirements:str,resume_id:int): 
    social_info  = await social_network_analyzer(pdf_info)
    print(social_info)
    profession = await analyze_proffesion(title,description,requirements)
    system_instructions = {
        "salesman": SELLER_INSTRUCTION,  # уже используется
        "salesman of it-product":SELLER_INSTRUCTION,
        "it": """You are a senior tech recruiter and behavioral analyst specializing in identifying IT-relevant soft skills from social media presence (LinkedIn, GitHub profiles, Twitter tech threads, etc.). Focus on traits like logical thinking, communication, curiosity, collaboration, consistency, and professionalism in online communication. Use evidence to assign scores and justify clearly.""",
        "manager": """You are a professional organizational psychologist analyzing managerial soft skills based on social media. Look for leadership, decision-making, emotional intelligence, delegation, motivation, and strategic thinking. Score only if evidence is found. Justify each score clearly with examples."""
    }

    chosen_instruction = system_instructions.get(profession, system_instructions["salesman"])
    model = "gemini-2.5-flash-preview-04-17"
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=social_info),
            ],
        ),
    ]
    generate_content_config = types.GenerateContentConfig(
        temperature=0.4,
        response_mime_type="application/json",
        response_schema=genai.types.Schema(
        # Ожидаем один ОБЪЕКТ на выходе
        type=genai.types.Type.OBJECT,
        required=["soft_total", "skills"], # Указываем обязательные поля
        properties={
            # Объект для итоговой оценки soft-скиллов
            "soft_total": genai.types.Schema(
                type=genai.types.Type.OBJECT,
                required=["total", "justification"],
                properties={
                    "total": genai.types.Schema(
                        type=genai.types.Type.INTEGER,
                        description="Aggregate score (0-100) based ONLY on evaluated soft skills relevant to sales. SHOUD BE IN RUSSIAN"
                    ),
                    "justification": genai.types.Schema(
                        type=genai.types.Type.STRING,
                        description="Brief explanation for the aggregate soft_total score.SHOULD BE IN RUSSIAN"
                    ),
                },
                description="Overall assessment based purely on the relevant soft skills identified."
            ),
            # Массив для отдельных soft-скиллов
            "skills": genai.types.Schema(
                type=genai.types.Type.ARRAY,
                description="List of identified soft skills relevant to sales.",
                items=genai.types.Schema(
                    type=genai.types.Type.OBJECT,
                    required=["title", "level", "justification", "type"],
                    properties={
                        "title": genai.types.Schema(type=genai.types.Type.STRING),
                        "level": genai.types.Schema(
                            type=genai.types.Type.INTEGER,
                            description="Proficiency score (0-100) based on social media evidence. SHOULD BE IN RUSSIAN"
                        ),
                        "justification": genai.types.Schema(type=genai.types.Type.STRING),
                        "type": genai.types.Schema(
                            type=genai.types.Type.STRING,
                            enum=["SOFT","HARD"] # Указываем тип как SOFT
                        ),
                    },
                ),
            ),
        }
    ),
         system_instruction=[
            types.Part.from_text(text=(chosen_instruction))],
    )

    try:
        # !!! Используем await и client.aio !!!
        response = await client.aio.models.generate_content(
            model=model,
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
        (f"Raw AI response that failed JSON parsing:\n---\n{json_text}\n---")
        raise ValueError(f"Ошибка декодирования JSON: {e}. Ответ ИИ: {json_text}")
    except Exception as e:
        print(f"Unexpected error during JSON parsing: {e}")
        raise ValueError(f"Unexpected error parsing JSON: {e}")
    print(parsed_json)
    return parsed_json
    



