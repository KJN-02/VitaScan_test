import sys
import json
import os
import requests

def get_disease_info(disease_name: str):
    api_key = os.environ.get("NVIDIA_API_KEY")
    if not api_key:
        return {"error": "NVIDIA_API_KEY not configured"}

    base_url = os.environ.get("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
    model_name = os.environ.get("NVIDIA_MODEL", "nvidia/nemotron-3-super-120b-a12b")

    prompt = f"""
You are an expert medical-information assistant that provides clear, non-alarming, evidence-based
information for lay users. Given a disease or condition name, return a JSON object with the following fields:
- disease (string): the disease name you were given
- short_description (string): 2-3 sentences describing the disease
- common_symptoms (array of strings): 5 or fewer common symptoms
- common_causes_or_risk_factors (array of strings): up to 6 short items
- precautions_and_prevention (array of strings): actionable precautions & prevention tips (6 items max)
- when_to_see_a_doctor (string): short guidance on when to seek medical care or emergency signs
- confidence (string): "low", "medium", or "high" to indicate how confident the model is about commonness/typicality

If the disease name is ambiguous or not recognized, clearly say so inside the
"short_description" field and provide general precautionary advice. Avoid giving direct medical instructions like dosing.

Disease: "{disease_name}"
"""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model_name,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2,
        "top_p": 0.7,
        "max_tokens": 1024,
    }

    try:
        response = requests.post(f"{base_url}/chat/completions", headers=headers, json=payload)
        response.raise_for_status()
        response_json = response.json()
        result_text = response_json['choices'][0]['message']['content'].strip() or "{}"
    except Exception as e:
        return {"error": f"NVIDIA API request failed: {str(e)}"}

    try:
        # Extract JSON from potential markdown blocks
        first = result_text.find("{")
        last = result_text.rfind("}")
        if first != -1 and last != -1:
            result_json = json.loads(result_text[first:last+1])
        else:
            result_json = json.loads(result_text)
    except json.JSONDecodeError:
        result_json = {"error": "Could not parse valid JSON from model response", "raw_output": result_text}

    if isinstance(result_json, dict):
        if "disease" not in result_json:
            result_json["disease"] = disease_name
    return result_json

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(json.dumps({"error": "Usage: python disease_info.py <disease_name>"}))
        sys.exit(1)
    disease = sys.argv[1]
    info = get_disease_info(disease)
    print(json.dumps(info, ensure_ascii=False))