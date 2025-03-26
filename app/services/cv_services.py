import pdfplumber
import json
from app.ai.analyzer import analyze_resume
def parse_pdf(file_path: str) -> str:
    text = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text(layout=True)
            if page_text:
                text.append(page_text)
    result = analyze_resume("\n".join(text))
    if result.startswith('"') and result.endswith('"'):
        result = result[1:-1]
    
    result = result.replace("\\n", "\n")
    
    parsed_json = json.loads(result)
    return parsed_json

