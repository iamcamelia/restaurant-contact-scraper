"""
AI Extraction & Verification Layer
Uses Google Gemini AI (free tier) to intelligently analyze messy website text,
search snippets, and social media data to extract verified restaurant contacts.
"""

import os
import json
import requests
from typing import Optional, Dict

DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"


def get_gemini_api_key(custom_key: Optional[str] = None) -> Optional[str]:
    """Retrieve Gemini API key from custom input or environment variable."""
    return custom_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")


def extract_contacts_with_ai(
    name: str,
    location: str = "Houston, TX",
    website_text: str = "",
    search_snippets: str = "",
    api_key: Optional[str] = None,
    timeout: int = 12
) -> Optional[Dict]:
    """
    Use Gemini AI to extract phone, email, address, and social links with confidence scoring.
    Returns dict if successful, None if API key missing or request fails.
    """
    key = get_gemini_api_key(api_key)
    if not key:
        return None

    # Truncate text to keep within prompt budget while retaining contact sections
    combined_context = f"""
RESTAURANT NAME: {name}
LOCATION: {location}

WEBSITE EXTRACT (First 3500 chars):
{website_text[:3500]}

SEARCH ENGINE SNIPPETS & SOCIAL DATA:
{search_snippets[:2500]}
"""

    prompt = f"""
You are an expert restaurant contact information extractor and data validator.
Analyze the provided website and search text for "{name}" in "{location}".
Your job is to identify the verified primary business phone number, email address, physical street address, and official social media accounts.

Rules:
1. Ignore template or placeholder phone numbers (like 111-111-1111, 123-456-7890).
2. Ignore web designer/developer/SaaS platform emails (e.g. info@squarespace.com, support@wix.com, privacy@...).
3. If multiple locations exist, pick the phone number that specifically matches the branch or city in "{location}".
4. Clean and format the phone number nicely, e.g. (512) 469-0002.
5. Provide a confidence rating ("high", "medium", "low") and a brief 1-sentence note explaining your findings.

Respond strictly in valid JSON matching this schema:
{{
  "phone": "string or null",
  "email": "string or null",
  "address": "string or null",
  "facebook": "string or null",
  "instagram": "string or null",
  "confidence": "high" | "medium" | "low",
  "notes": "string"
}}

Data Context:
{combined_context}
"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{DEFAULT_GEMINI_MODEL}:generateContent?key={key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "response_mime_type": "application/json",
            "temperature": 0.1
        }
    }

    try:
        resp = requests.post(url, json=payload, timeout=timeout)
        if resp.status_code == 200:
            data = resp.json()
            candidates = data.get("candidates", [])
            if candidates:
                part = candidates[0].get("content", {}).get("parts", [{}])[0]
                text = part.get("text", "{}")
                parsed = json.loads(text)
                return {
                    "phone": parsed.get("phone") or "",
                    "email": parsed.get("email") or "",
                    "address": parsed.get("address") or "",
                    "facebook": parsed.get("facebook") or "",
                    "instagram": parsed.get("instagram") or "",
                    "confidence": parsed.get("confidence") or "medium",
                    "notes": parsed.get("notes") or ""
                }
    except Exception:
        pass

    return None
