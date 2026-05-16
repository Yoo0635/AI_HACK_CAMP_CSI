from config import TFLITE_MODEL_PATH


class ActivityEngine:
    def __init__(self):
        pass

    def predict(self, window: list) -> tuple[str, float]:
        """TFLite 추론 → (activity_label, confidence)"""
        pass
