"""
Extract text and structured data from all 11 PNG images in evidence/images using Gemini 3.5 Flash Lite.
Caches results to dataset/evidence/images_extracted/ to ensure fast, deterministic offline runs.
"""
import os
import glob
import json
import base64
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent?key={API_KEY}"
OUTPUT_DIR = "dataset/evidence/images_extracted"
os.makedirs(OUTPUT_DIR, exist_ok=True)

images = glob.glob("dataset/evidence/images/*.png")
print(f"Found {len(images)} images to process.")

total_prompt_tokens = 0
total_candidate_tokens = 0

for img_path in images:
    base_name = os.path.basename(img_path)
    json_path = os.path.join(OUTPUT_DIR, f"{base_name}.json")
    
    if os.path.exists(json_path):
        print(f"Skipping already processed: {base_name}")
        continue
    
    print(f"Processing {base_name}...")
    with open(img_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode("utf-8")
    
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": (
                            "Extract all information from this system console screenshot. "
                            "List all resource IDs, user IDs, customer references, emails, usernames, "
                            "status codes (e.g., ACTIVE, DELETED, 404), dates/timestamps, and table rows accurately."
                        )
                    },
                    {
                        "inline_data": {
                            "mime_type": "image/png",
                            "data": img_b64
                        }
                    }
                ]
            }
        ]
    }
    
    resp = requests.post(URL, json=payload)
    if resp.status_code == 200:
        data = resp.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        usage = data.get("usageMetadata", {})
        total_prompt_tokens += usage.get("promptTokenCount", 0)
        total_candidate_tokens += usage.get("candidatesTokenCount", 0)
        
        with open(json_path, "w", encoding="utf-8") as out_f:
            json.dump({
                "image": base_name,
                "extracted_text": text,
                "usage": usage
            }, out_f, indent=2)
        print(f"  -> Extracted {len(text)} chars from {base_name}")
    else:
        print(f"  -> Error {resp.status_code}: {resp.text}")

print(f"Done! Total prompt tokens: {total_prompt_tokens}, candidate tokens: {total_candidate_tokens}")
