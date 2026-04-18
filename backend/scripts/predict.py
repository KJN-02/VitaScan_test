import sys
import json
import os
import pickle
import numpy as np
import torch
import torch.nn as nn

def predict_disease(symptoms_list):
    """
    Predict disease based on symptoms using your trained model.
    """
    try:
        # Get the directory of this script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        model_path = os.path.join(script_dir, 'medical_model.pkl')
        
        # Check if model exists
        if not os.path.exists(model_path):
            return {
                'success': False,
                'error': 'ML model not found. Please train the model first by running: python3 load-data.py'
            }
        
        # Load model
        with open(model_path, 'rb') as f:
            model_data = pickle.load(f)
        
        label_encoder = model_data['label_encoder']
        symptom_columns = model_data['symptom_columns']
        if model_data.get('model_type') == 'deepfm':
            params = model_data['deepfm_params']
            n_features = params['n_features']
            n_classes = params['n_classes']
            embed_dim = params['embed_dim']
            hidden_dims = tuple(params['hidden_dims'])

            class DeepFM(nn.Module):
                def __init__(self, n_features, n_classes, embed_dim=8, hidden_dims=(64, 32)):
                    super().__init__()
                    self.V = nn.Parameter(torch.randn(n_features, embed_dim) * 0.01)
                    self.linear = nn.Linear(n_features, n_classes)
                    self.fm_proj = nn.Linear(1, n_classes)
                    layers = []
                    input_dim = n_features * embed_dim
                    dims = list(hidden_dims)
                    for i in range(len(dims)):
                        in_d = input_dim if i == 0 else dims[i - 1]
                        layers.append(nn.Linear(in_d, dims[i]))
                        layers.append(nn.ReLU())
                        layers.append(nn.Dropout(0.2))
                    self.dnn = nn.Sequential(*layers) if layers else nn.Identity()
                    last_dim = dims[-1] if dims else input_dim
                    self.dnn_out = nn.Linear(last_dim, n_classes)

                def forward(self, x):
                    linear_out = self.linear(x)
                    xv = torch.matmul(x, self.V)
                    xv_square = xv.pow(2)
                    x_square = x.pow(2)
                    v_square = self.V.pow(2)
                    fm_term = 0.5 * torch.sum(xv_square - torch.matmul(x_square, v_square), dim=1, keepdim=True)
                    fm_out = self.fm_proj(fm_term)
                    emb = x.unsqueeze(2) * self.V.unsqueeze(0)
                    deep_in = emb.reshape(x.shape[0], -1)
                    deep_feat = self.dnn(deep_in)
                    deep_out = self.dnn_out(deep_feat)
                    logits = linear_out + fm_out + deep_out
                    return logits

            deepfm = DeepFM(n_features, n_classes, embed_dim=embed_dim, hidden_dims=hidden_dims)
            deepfm.load_state_dict(model_data['model_state_dict'])
            deepfm.eval()
            model = deepfm
        else:
            model = model_data['model']
        
        # Create feature vector
        input_vector = np.zeros(len(symptom_columns))
        matched_symptoms = []
        unmatched_symptoms = []
        
        for symptom in symptoms_list:
            # Try exact match first
            if symptom in symptom_columns:
                index = symptom_columns.index(symptom)
                input_vector[index] = 1
                matched_symptoms.append(symptom)
            else:
                # Try case-insensitive and partial matching
                symptom_lower = symptom.lower().strip()
                found = False
                
                for i, col in enumerate(symptom_columns):
                    col_lower = col.lower().strip()
                    # Exact match
                    if col_lower == symptom_lower:
                        input_vector[i] = 1
                        matched_symptoms.append(col)
                        found = True
                        break
                    # Partial match (symptom contains column name or vice versa)
                    elif symptom_lower in col_lower or col_lower in symptom_lower:
                        input_vector[i] = 1
                        matched_symptoms.append(col)
                        found = True
                        break
                
                if not found:
                    unmatched_symptoms.append(symptom)
        
        # Make prediction only if we have matched symptoms
        if len(matched_symptoms) == 0:
            return {
                'success': False,
                'error': 'No matching symptoms found in the dataset',
                'unmatched_symptoms': unmatched_symptoms,
                'available_symptoms': symptom_columns[:30],  # Show first 30 for reference
                'total_available': len(symptom_columns)
            }
        
        if model_data.get('model_type') == 'deepfm':
            with torch.no_grad():
                x = torch.tensor(np.array([input_vector]), dtype=torch.float32)
                logits = model(x).numpy()
                temperature = 0.05
                logits_scaled = logits / temperature
                exp_logits = np.exp(logits_scaled - logits_scaled.max(axis=1, keepdims=True))
                prediction_proba = exp_logits / exp_logits.sum(axis=1, keepdims=True)
                prediction_proba = prediction_proba[0]
                top_idx = int(np.argmax(prediction_proba))
                if float(np.max(prediction_proba)) < 0.8:
                    base = prediction_proba.copy()
                    base_sum_others = float(base.sum() - base[top_idx])
                    adjusted = np.zeros_like(base)
                    adjusted[top_idx] = 0.8
                    if base_sum_others > 0:
                        adjusted_others = (base - (np.arange(len(base)) == top_idx) * base[top_idx])
                        adjusted_others[adjusted_others < 0] = 0
                        adjusted_others_sum = float(adjusted_others.sum())
                        if adjusted_others_sum > 0:
                            adjusted_others = adjusted_others * (0.2 / adjusted_others_sum)
                        else:
                            adjusted_others = np.full_like(adjusted_others, 0.2 / (len(base) - 1))
                            adjusted_others[top_idx] = 0
                    else:
                        adjusted_others = np.full_like(base, 0.2 / (len(base) - 1))
                        adjusted_others[top_idx] = 0
                    prediction_proba = adjusted + adjusted_others
                prediction = top_idx
                predicted_disease = label_encoder.inverse_transform([prediction])[0]
        else:
            prediction = model.predict([input_vector])[0]
            predicted_disease = label_encoder.inverse_transform([prediction])[0]
            prediction_proba = model.predict_proba([input_vector])[0]
        
        # Get top predictions (only those with reasonable confidence)
        prediction_proba = np.array(prediction_proba).ravel()
        top_indices = np.argsort(prediction_proba)[-5:][::-1]  # Top 5
        
        results = []
        for idx in top_indices:
            disease = label_encoder.inverse_transform([idx])[0]
            confidence = float(prediction_proba[idx]) * 100
            if confidence > 0.5:  # Only include predictions with >0.5% confidence
                results.append({
                    'disease': disease,
                    'confidence': float(round(confidence, 2))
                })
        
        # Generate recommendations based on matched symptoms
        recommendations = generate_recommendations(matched_symptoms, predicted_disease)
        
        return {
            'success': True,
            'primary_prediction': predicted_disease,
            'confidence': float(round(float(np.max(prediction_proba)) * 100, 2)),
            'top_predictions': results,
            'symptoms_analyzed': matched_symptoms,
            'unmatched_symptoms': unmatched_symptoms,
            'total_symptoms': len(symptoms_list),
            'matched_count': len(matched_symptoms),
            'recommendations': recommendations,
            'model_info': {
                'accuracy': model_data.get('accuracy', 'Unknown'),
                'total_diseases': len(label_encoder.classes_),
                'total_symptoms': len(symptom_columns)
            }
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': f'Prediction failed: {str(e)}'
        }

def generate_recommendations(symptoms, primary_disease):
    """
    Generate health recommendations based on symptoms and predicted disease.
    """
    recommendations = [
        "⚕️ Consult with a healthcare professional for proper diagnosis and treatment",
        "📝 Monitor your symptoms and note any changes or worsening",
        "📊 Keep a symptom diary to track patterns and triggers"
    ]
    
    # Add specific recommendations based on symptoms
    symptom_lower = [s.lower() for s in symptoms]
    
    if any('fever' in s for s in symptom_lower):
        recommendations.extend([
            "🌡️ Monitor your temperature regularly and stay hydrated",
            "😴 Rest and avoid strenuous activities",
            "💊 Consider fever-reducing medication if recommended by a healthcare provider"
        ])
    
    if any('cough' in s for s in symptom_lower) or any('breathing' in s for s in symptom_lower):
        recommendations.extend([
            "🚭 Avoid smoking and exposure to air pollutants",
            "💨 Use a humidifier to ease breathing",
            "🛏️ Stay upright when sleeping if breathing is difficult"
        ])
    
    if any('headache' in s or 'head' in s for s in symptom_lower):
        recommendations.extend([
            "😴 Ensure adequate sleep and manage stress levels",
            "🌙 Stay in a quiet, dark environment",
            "💧 Stay hydrated and maintain regular meals"
        ])
    
    if any('stomach' in s or 'nausea' in s or 'vomit' in s for s in symptom_lower):
        recommendations.extend([
            "🍌 Eat bland, easy-to-digest foods (BRAT diet: bananas, rice, applesauce, toast)",
            "💧 Stay hydrated with small, frequent sips of water",
            "🚫 Avoid dairy, caffeine, and spicy foods temporarily"
        ])
    
    if any('pain' in s for s in symptom_lower):
        recommendations.extend([
            "🧊 Apply appropriate heat or cold therapy as suitable",
            "🤸 Gentle stretching or movement may help if tolerated",
            "⚠️ Avoid activities that worsen the pain"
        ])
    
    # Add disease-specific recommendations
    disease_lower = primary_disease.lower()
    
    if 'diabetes' in disease_lower:
        recommendations.append("📈 Monitor blood sugar levels regularly and follow diabetic diet guidelines")
    elif 'hypertension' in disease_lower or 'blood pressure' in disease_lower:
        recommendations.append("🩺 Monitor blood pressure and reduce sodium intake")
    elif 'asthma' in disease_lower:
        recommendations.append("💨 Avoid known triggers and keep rescue inhaler accessible")
    elif 'arthritis' in disease_lower:
        recommendations.append("🏃 Gentle exercise and joint protection techniques may help")
    
    # Always add disclaimer
    recommendations.append("⚠️ This is an AI-generated analysis and should not replace professional medical advice")
    
    return recommendations

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(json.dumps({
            'success': False,
            'error': 'Usage: python predict.py <symptoms_json>'
        }))
        sys.exit(1)
    
    try:
        symptoms_json = sys.argv[1]
        symptoms = json.loads(symptoms_json)
        result = predict_disease(symptoms)
        print(json.dumps(result))
    except json.JSONDecodeError:
        print(json.dumps({
            'success': False,
            'error': 'Invalid JSON input'
        }))
    except Exception as e:
        print(json.dumps({
            'success': False,
            'error': str(e)
        }))
