import re
import requests
import time
import json 
from dotenv import load_dotenv
import os
from google import genai
from google.genai import types
load_dotenv()

client = genai.Client(
        api_key=os.environ.get("GEMINI_API_KEY"),
    )

def extract_social_media_links_json(text):
    """Extracts social media profile links from text."""
    social_media_patterns = {
        "facebook": r"(?:https?:\/\/)?(?:www\.)?facebook\.com\/[A-Za-z0-9_\-\.]+/?",
      
        "twitter": r"(?:https?:\/\/)?(?:www\.)?(?:x\.com|twitter\.com)\/[A-Za-z0-9_]+/?",
        "instagram": r"(?:https?:\/\/)?(?:www\.)?instagram\.com\/[A-Za-z0-9_\-\.]+/?",
        "linkedin": r"(?:https?:\/\/)?(?:www\.)?linkedin\.com\/(?:in|company)\/[A-Za-z0-9_\-\.]+/?", # Added /company/ possibility
    }

    social_media_links = {}
    for platform, pattern in social_media_patterns.items():
       
        matches = re.findall(pattern, text, re.IGNORECASE) 
        if matches:
         
            link = matches[0].rstrip('/')
            social_media_links[platform] = link

    return social_media_links

def social_network_analyzer(str):
    text_to_extract = str
    summary = f""""""


    dataset_id_map = {
        "instagram": "gd_l1vikfch901nx3by4",
        "linkedin": "gd_l1viktl72bvl7bjuj0",
        "facebook": "gd_lkaxegm826bjpoo9m5",
        "twitter": "gd_lwxmeb2u1cniijd7t4", 
    }


    BRIGHTDATA_API_KEY = "b8ca1069f855a70d33248d585a12a2f7443f585bf840ad45a97605b5bf1f72d4" # Use your actual API key
    TRIGGER_URL = "https://api.brightdata.com/datasets/v3/trigger"
    PROGRESS_URL_BASE = "https://api.brightdata.com/datasets/v3/progress/"
    SNAPSHOT_URL_BASE = "https://api.brightdata.com/datasets/v3/snapshot/"
    S3_BUCKET_NAME = "start_up"




    extracted_links = extract_social_media_links_json(text_to_extract)
    print("Extracted Links:")
    print(json.dumps(extracted_links, indent=2))
    print("-" * 30)


    if not extracted_links:
        print("No social media links found in the text.")
    else:
        for platform, link in extracted_links.items():
            print(f"Processing {platform.capitalize()} link: {link}")

    
            if platform not in dataset_id_map:
                print(f"  -> Warning: No dataset_id configured for platform '{platform}'. Skipping.")
                print("-" * 30)
                continue 

            current_dataset_id = dataset_id_map[platform]
            print(f"  -> Using dataset_id: {current_dataset_id}")

            
            input_data = [{"url": link}]
            trigger_params = {
                "dataset_id": current_dataset_id,
                "include_errors": "true",
                "limit_per_input": "1",
            }
            trigger_headers = {
                "Authorization": f"Bearer {BRIGHTDATA_API_KEY}",
                "Content-Type": "application/json",
            }

            trigger_payload = {
                "deliver": {
                    "type": "s3",
                    "filename": {"template": f"{platform}_{{[snapshot_id]}}", "extension": "json"},
                    "bucket": S3_BUCKET_NAME,
                    "batch_size":10,
                    "directory": "" 
                },
                "input": input_data,
            }

        
            try:
                print(f"  -> Triggering job...")
                response = requests.post(TRIGGER_URL, headers=trigger_headers, params=trigger_params, json=trigger_payload)
                response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
                response_data = response.json()

                if "snapshot_id" not in response_data:
                    print(f"  -> Error: 'snapshot_id' not found in trigger response: {response_data}")
                    print("-" * 30)
                    continue # Skip to next link

                snapshot_id = response_data["snapshot_id"]
                print(f"  -> Job triggered successfully. Snapshot ID: {snapshot_id}")

                # 4. Poll for job completion
                progress_headers = {
                    "Authorization": f"Bearer {BRIGHTDATA_API_KEY}",
                }
                progress_url = f"{PROGRESS_URL_BASE}{snapshot_id}"
                print(f"  -> Monitoring progress...")

                while True:
                    try:
                        progress_response = requests.get(progress_url, headers=progress_headers)
                        progress_response.raise_for_status()
                        progress_data = progress_response.json()
                        status = progress_data.get("status", "unknown") # Default to 'unknown' if status key is missing
                        print(f"     Current status: {status}")

                        if status == "ready":
                            print(f"  -> Job completed successfully!")
                            try:
                                result_url = f"{SNAPSHOT_URL_BASE}{snapshot_id}"
                                result_params = {"format": "json","batch_size":1500}
                                result_response = requests.get(result_url, headers=progress_headers, params=result_params)
                                result_response.raise_for_status()
                                print(type(result_response.json()[0]))
                                cleaned_data = {
                                key: (value[:2] if isinstance(value, list) and value else value)
                                    for key, value in result_response.json()[0].items()
                                }                         
                                print("  -> Results:")
                                text_data = json.dumps(cleaned_data, ensure_ascii=False, indent=4)
                                summary += f"\"{platform}\":" +  text_data + "\n"
                            except requests.exceptions.RequestException as e:
                                print(f"  -> Error fetching results: {e}")
                            except json.JSONDecodeError:
                                print(f"  -> Error decoding result JSON: {result_response.text}")
                            break

                        elif status == "failed":
                            print(f"  -> Error: Job failed.")
                            # You might want to log progress_data here for debugging
                            print(f"     Failure details: {progress_data}")
                            break # Exit the while loop for this job

                        elif status == "unknown":
                            print(f"  -> Warning: Could not determine job status from response: {progress_data}")
                            # Decide how to handle: break, continue polling, etc.
                            # For safety, let's break after a warning.
                            break

                        else:
                            # Status is likely 'processing' or similar, wait and poll again
                            print(f"     Waiting...")
                            time.sleep(5) # Wait 5 seconds before checking again

                    except requests.exceptions.RequestException as e:
                        print(f"  -> Error checking progress: {e}")
                        print(f"     Stopping polling for snapshot {snapshot_id}.")
                        break # Exit the while loop on network or HTTP error during polling
                    except json.JSONDecodeError:
                        print(f"  -> Error decoding progress JSON: {progress_response.text}")
                        print(f"     Stopping polling for snapshot {snapshot_id}.")
                        break # Exit the while loop if progress response is not valid JSON

            except requests.exceptions.RequestException as e:
                print(f"  -> Error triggering Bright Data job for {platform} ({link}): {e}")
                # Print response body if available for more context
                if e.response is not None:
                    print(f"     Response status: {e.response.status_code}")
                    print(f"     Response text: {e.response.text}")
            except Exception as e:
                print(f"  -> An unexpected error occurred during triggering for {platform}: {e}")


            print("-" * 30) 
    print("Finished processing all found links.")  

    return summary







def analyze_social(pdf_info:str): 
    social_info  = social_network_analyzer(pdf_info)
    model = "gemini-2.0-flash"
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
            type = genai.types.Type.ARRAY,
            items = genai.types.Schema(
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
                                    enum = ["SOFT"],
                                ),
                            },
                        ),
                    ),
    
        ),
         system_instruction=[
            types.Part.from_text(text="""Ты опытный психолог который может определять по данным из соц сетей софт скиллы
            человека и отправлять их в json формате, исходя из соцсетей ты должен делать анализ,оценку ставь от 0 до 100,Пиши на английском!!, Если промпт пустой то ничего не возвращай"""),
        ],
    )

    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=generate_content_config,
    )

    print(response.to_json_dict()['candidates'][0]['content']['parts'][0]['text'])
    json_text = response.to_json_dict()['candidates'][0]['content']['parts'][0]['text']
    
    try:
        parsed_json = json.loads(json_text) 
        print(parsed_json)
        return parsed_json[0]
    except json.JSONDecodeError as e:
        raise ValueError(f"Ошибка декодирования JSON: {e}")
    



