from fastapi import FastAPI, HTTPException, Body, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import os
import sys
import json
import shutil
import tempfile
import tensorflow as tf
from dotenv import load_dotenv
import logging
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Add scripts directory to path so we can import them
scripts_dir = os.path.join(os.path.dirname(__file__), "scripts")
sys.path.append(scripts_dir)

import predict
import blood_info
import disease_info
import xray_info

app = FastAPI()

# Enable CORS for the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load X-ray model once at startup
XRAY_MODEL_PATH = os.path.join(scripts_dir, 'disease_model.keras')
DATA_CSV = os.path.join(scripts_dir, 'xray_dataset', 'Data_Entry_2017.csv')
xray_model = None
xray_label_columns = []

@app.on_event("startup")
async def startup_event():
    global xray_model, xray_label_columns
    logger.info("Starting up backend...")
    if os.path.exists(XRAY_MODEL_PATH):
        try:
            logger.info(f"Loading X-ray model from {XRAY_MODEL_PATH}")
            xray_model = tf.keras.models.load_model(XRAY_MODEL_PATH)
            xray_label_columns = xray_info.get_label_columns(DATA_CSV)
            logger.info("X-ray model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading X-ray model: {e}")
    else:
        logger.warning(f"X-ray model path {XRAY_MODEL_PATH} does not exist")

@app.get("/")
async def root():
    logger.info("Root endpoint called")
    return {"message": "Vita Backend API is running"}

@app.post("/predict")
async def predict_symptoms(symptoms: list[str] = Body(..., embed=True)):
    logger.info(f"Predict symptoms called with {len(symptoms)} symptoms")
    try:
        result = predict.predict_disease(symptoms)
        logger.info(f"Prediction result: {result.get('disease', 'Unknown')}")
        return result
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze-blood")
async def analyze_blood(file: UploadFile = File(...)):
    logger.info(f"Analyze blood called with file: {file.filename}")
    # Save the uploaded file to a temporary location
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        payload = {"file_path": tmp_path}
        result = blood_info.analyze_labs(payload)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

@app.post("/disease-info")
async def get_disease_info(payload: dict = Body(...)):
    logger.info(f"Disease info called for: {payload.get('disease_name')}")
    try:
        disease_name = payload.get("disease_name")
        if not disease_name:
            raise HTTPException(status_code=400, detail="disease_name is required")
        result = disease_info.get_disease_info(disease_name)
        return result
    except Exception as e:
        logger.error(f"Disease info error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze-xray")
async def analyze_xray(file: UploadFile = File(...)):
    logger.info(f"Analyze X-ray called with file: {file.filename}")
    if not xray_model:
        logger.error("X-ray model not loaded")
        raise HTTPException(status_code=503, detail="X-ray model not loaded")

    # Save the uploaded file to a temporary location
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        result = xray_info.predict_single_image(tmp_path, xray_model, xray_label_columns)
        logger.info("X-ray analysis completed successfully")
        return result
    except Exception as e:
        logger.error(f"X-ray analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"Starting server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
