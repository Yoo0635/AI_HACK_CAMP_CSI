import os
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
CSI_STREAM = os.getenv("CSI_STREAM", "CsiLogStream")
ANALYSIS_STREAM = os.getenv("ANALYSIS_STREAM", "CsiAnalysisStream")
ALERT_STREAM = os.getenv("ALERT_STREAM", "CsiAlertStream")
TFLITE_MODEL_PATH = os.getenv("TFLITE_MODEL_PATH", "models/activity_cnn_int8.tflite")
GGUF_MODEL_PATH = os.getenv("GGUF_MODEL_PATH", "models/sllm_model.gguf")
RISK_THRESHOLD = float(os.getenv("RISK_THRESHOLD", "0.7"))
