import os
import sys
import json
import numpy as np
import pandas as pd
import tensorflow as tf
from PIL import Image

try:
    import google.generativeai as genai
except Exception as e:
    genai = None

IMAGE_SIZE = (224, 224)
MODEL_PATH = os.path.join(os.path.dirname(__file__), 'disease_model.keras')
DATA_CSV = os.path.join(os.path.dirname(__file__), 'xray_dataset', 'Data_Entry_2017.csv')

def get_label_columns(csv_path):
    try:
        df = pd.read_csv(csv_path)
        all_labels = np.unique([item for sublist in df['Finding Labels'].str.split('|') for item in sublist])
        return [label for label in all_labels if label != 'No Finding']
    except Exception:
        return ['Atelectasis', 'Cardiomegaly', 'Effusion', 'Infiltration', 'Mass', 'Nodule', 'Pneumonia', 'Pneumothorax', 'Consolidation', 'Edema', 'Emphysema', 'Fibrosis', 'Pleural_Thickening', 'Hernia']

def get_gemini_disease_info(disease_name: str):
    if not genai:
        return None
    
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return None

    genai.configure(api_key=api_key)
    model_name = os.environ.get("GEMINI_MODEL", "models/gemini-2.0-flash")
    model = genai.GenerativeModel(model_name)

    prompt = f"""
You are an expert medical-information assistant that provides clear, non-alarming, evidence-based
information for lay users. Given a disease or condition name from an X-ray finding, return a JSON object with the following fields:
- disease (string): the disease name you were given
- short_description (string): 2-3 sentences describing the disease
- common_symptoms (array of strings): 5 or fewer common symptoms
- common_causes_or_risk_factors (array of strings): up to 6 short items
- precautions_and_prevention (array of strings): actionable precautions & prevention tips (6 items max)
- when_to_see_a_doctor (string): short guidance on when to seek medical care or emergency signs
- confidence (string): "low", "medium", or "high" to indicate how confident the model is about commonness/typicality

Disease: "{disease_name}"
"""

    try:
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.2,
                "response_mime_type": "application/json",
            },
        )
        result_text = (getattr(response, "text", None) or "").strip() or "{}"
        return json.loads(result_text)
    except Exception:
        return None

def predict_single_image(img_path, model, label_columns, threshold=0.2):
    if not os.path.exists(img_path):
        return {"error": f"File {img_path} not found."}

    try:
        img = tf.keras.preprocessing.image.load_img(img_path, target_size=IMAGE_SIZE)
        img_array = tf.keras.preprocessing.image.img_to_array(img)
        img_array = np.expand_dims(img_array, axis=0)

        predictions = model.predict(img_array, verbose=0)[0]
        
        results = []
        for i, label in enumerate(label_columns):
            prob = float(predictions[i])
            results.append((label, prob))
        
        results.sort(key=lambda x: x[1], reverse=True)
        
        findings_above_threshold = [r for r in results if r[1] >= threshold]

        if not findings_above_threshold:
            return {
                "study_type": "Chest X-ray (Normal)",
                "summary": "No significant abnormalities detected based on the current threshold (20%).",
                "key_findings": ["Lung fields appear clear", "No significant opacities detected"],
                "likely_conditions": ["Normal Chest X-ray"],
                "recommendations": ["Regular follow-up if symptoms persist"],
                "urgency": "Low",
                "confidence": "Normal",
                "top_finding": None,
                "other_possibilities": []
            }
        
        top_finding_tuple = findings_above_threshold[0]
        top_finding_name = top_finding_tuple[0]
        top_finding_prob = top_finding_tuple[1]
        
        other_possibilities = [f"{r[0]} ({r[1]*100:.1f}%)" for r in findings_above_threshold[1:]]
        
        # Get AI details for top finding
        ai_details = get_gemini_disease_info(top_finding_name)
        
        summary = f"Top finding: {top_finding_name} ({top_finding_prob*100:.1f}% confidence)."
        if other_possibilities:
            summary += f" Other possibilities include: {', '.join(other_possibilities)}."

        return {
            "study_type": "Chest X-ray (Findings Detected)",
            "summary": summary,
            "key_findings": [f"{r[0]} ({r[1]*100:.1f}%)" for r in findings_above_threshold],
            "likely_conditions": [r[0] for r in findings_above_threshold],
            "recommendations": ["Consult with a radiologist for a formal interpretation", "Correlate with clinical symptoms and history"],
            "urgency": "Medium" if top_finding_prob < 0.7 else "High",
            "confidence": f"{top_finding_prob*100:.1f}%",
            "top_finding": {
                "name": top_finding_name,
                "probability": f"{top_finding_prob*100:.1f}%",
                "details": ai_details
            },
            "other_possibilities": other_possibilities
        }
    except Exception as e:
        return {"error": f"Prediction failed: {str(e)}"}

if __name__ == "__main__":
    try:
        payload = json.loads(sys.argv[1])
        file_path = payload.get("file_path")
        
        if not file_path or not os.path.exists(file_path):
            print(json.dumps({"error": f"Invalid or missing file path: {file_path}"}))
            sys.exit(1)

        if not os.path.exists(MODEL_PATH):
            print(json.dumps({"error": f"Model file not found at {MODEL_PATH}. Please train the model first."}))
            sys.exit(1)

        model = tf.keras.models.load_model(MODEL_PATH)
        label_columns = get_label_columns(DATA_CSV)
        
        result = predict_single_image(file_path, model, label_columns)
        print(json.dumps(result))

        if ".next" in file_path:
            try:
                os.remove(file_path)
            except:
                pass

    except Exception as e:
        print(json.dumps({"error": str(e)}))
