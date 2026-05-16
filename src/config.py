import os
from dotenv import load_dotenv

load_dotenv()

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
CSI_STREAM_NAME = os.getenv("CSI_STREAM_NAME", "csi_log_stream")
ANALYSIS_STREAM = os.getenv("ANALYSIS_STREAM", "csi_analysis_stream")
TFLITE_MODEL_PATH = os.getenv("TFLITE_MODEL_PATH", "models/activity_cnn_int8.tflite")
GGUF_MODEL_PATH = os.getenv("GGUF_MODEL_PATH", "models/sllm_model.gguf")
RISK_THRESHOLD = float(os.getenv("RISK_THRESHOLD", "0.7"))
