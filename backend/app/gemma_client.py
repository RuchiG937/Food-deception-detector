import json
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from PIL import Image

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

AUDIT_PROMPT_TEMPLATE = """
You are CleanLabel AI, a strict food safety biochemist and deceptive marketing auditor.
Analyze the provided packaged food label image.

USER HEALTH PROFILE CONDITIONS: {health_profiles}
CLAIMED FRONT-OF-PACK MARKETING: "{front_claim}"

Audit the ingredients and nutrition table strictly. Return ONLY a valid JSON object matching this exact schema:

{{
  "product_name": "Detected Product Name or Category",
  "deception_score": "Low | Moderate | High | Severe",
  "marketing_vs_reality": "Direct analysis exposing if claims match the back ingredients (e.g., claimed whole grain but mostly maida/sugar)",
  "verdict": "SAFE | MODERATION | STRICTLY AVOID",
  "verdict_reason": "One clear paragraph explaining why for the selected health profiles",
  "key_ingredients": [
    {{"name": "Ingredient 1", "percentage_or_rank": "High/Rank 1", "risk_level": "Safe | Warning | Toxic"}}
  ],
  "harmful_additives": [
    {{"code": "INS 150d / E-number", "common_name": "Caramel Color IV", "concern": "Potential carcinogenic byproduct, gut irritant"}}
  ],
  "health_profile_risks": [
    {{"condition": "Condition Name", "risk_level": "High | Medium | Low", "details": "Specific biochemical reason"}}
  ],
  "clean_alternatives": [
    {{"name": "Better Food Alternative", "why": "No refined sugar or hydrogenated oils"}}
  ]
}}

CRITICAL: Return strictly valid JSON. Do not wrap in markdown quotes if possible, or wrap cleanly in ```json ... ```.
"""


def audit_food_label(
    image: Image.Image, health_profiles: str, front_claim: str
) -> dict:
  prompt = AUDIT_PROMPT_TEMPLATE.format(
      health_profiles=health_profiles or "General Public",
      front_claim=front_claim or "Not Specified",
  )

  response = client.models.generate_content(
      model="gemma-4",
      contents=[image, prompt],
      config=types.GenerateContentConfig(
          response_mime_type="application/json"
      ),
  )

  raw_text = response.text.strip()
  if raw_text.startswith("```json"):
    raw_text = raw_text[7:]
  if raw_text.endswith("```"):
    raw_text = raw_text[:-3]

  return json.loads(raw_text.strip())