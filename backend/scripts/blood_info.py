import sys
import json
import os
import requests

try:
    from pdfminer.high_level import extract_text
    PDFMINER_AVAILABLE = True
except Exception as e:
    PDFMINER_AVAILABLE = False
    print(f"Warning: pdfminer.six not available: {e}")

def analyze_labs(payload: dict):
    if not PDFMINER_AVAILABLE:
        return {"error": "PDF analysis component is not available on the server (missing pdfminer.six)"}
    
    api_key = os.environ.get("NVIDIA_API_KEY")
    if not api_key:
        return {"error": "NVIDIA_API_KEY not configured"}

    base_url = os.environ.get("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
    model_name = os.environ.get("NVIDIA_MODEL", "nvidia/nemotron-3-super-120b-a12b")

    file_path = payload.get("file_path")
    if not file_path:
        return {"error": "PDF file path is required"}

    try:
        text = extract_text(file_path)
    except Exception as e:
        return {"error": f"Failed to read PDF: {str(e)}"}

    prompt = (
        "You are a clinical lab interpretation assistant for lay users. "
        "Given the following lab report text, extract abnormalities and map them to potential conditions. "
        "Return a compact JSON with exactly these fields: "
        "- irregularities (array of strings); "
        "- possible_diseases (array of strings); "
        "- irregularity_info (string); "
        "- causes_or_risk_factors (array of strings); "
        "- precautions_and_prevention (array of strings); "
        "- when_to_see_a_doctor (string). "
        "Use typical adult reference ranges; be conservative; avoid dosing instructions; include uncertainty where appropriate. "
        f"\n\nLab Report Text:\n{text}"
    )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    api_payload = {
        "model": model_name,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2,
        "top_p": 0.7,
        "max_tokens": 1024,
    }

    try:
        response = requests.post(f"{base_url}/chat/completions", headers=headers, json=api_payload)
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

    if isinstance(result_json, dict) and "error" not in result_json:
        irregularities = result_json.get("irregularities") or result_json.get("notable_abnormalities") or []
        possible_diseases = result_json.get("possible_diseases") or result_json.get("possible_causes") or []
        irregularity_info = result_json.get("irregularity_info") or result_json.get("summary") or ""
        causes_or_risk_factors = (
            result_json.get("causes_or_risk_factors")
            or result_json.get("common_causes_or_risk_factors")
            or result_json.get("risk_factors")
            or []
        )
        precautions_and_prevention = (
            result_json.get("precautions_and_prevention")
            or result_json.get("precautions")
            or result_json.get("prevention")
            or []
        )
        when_to_see_a_doctor = (
            result_json.get("when_to_see_a_doctor")
            or result_json.get("when_to_seek_medical_care")
            or ""
        )

        final = {
            "irregularities": irregularities if isinstance(irregularities, list) else [str(irregularities)],
            "possible_diseases": possible_diseases if isinstance(possible_diseases, list) else [str(possible_diseases)],
            "irregularity_info": str(irregularity_info or ""),
            "causes_or_risk_factors": causes_or_risk_factors if isinstance(causes_or_risk_factors, list) else [str(causes_or_risk_factors)],
            "precautions_and_prevention": precautions_and_prevention if isinstance(precautions_and_prevention, list) else [str(precautions_and_prevention)],
            "when_to_see_a_doctor": str(when_to_see_a_doctor or ""),
        }
        return final

    return result_json

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(json.dumps({"error": "Usage: python blood_info.py '<json_payload>'"}))
        sys.exit(1)
    try:
        payload = json.loads(sys.argv[1])
    except Exception:
        print(json.dumps({"error": "Invalid JSON payload"}))
        sys.exit(1)
    info = analyze_labs(payload)
    print(json.dumps(info, ensure_ascii=False))
