import random
import time


def analyze_csi_with_cnn(_csi_matrix: list[float]) -> dict:
    """
    TODO: 실제 CNN 모델 연결 전 임시 함수, 해당 함수는 is_anomaly=True로 프론트에 알림을 보냄
    """
    return {
        "label": "NORMAL",
        "cnn_score": 0.0,
        "energy": 0.0,
        "is_anomaly": True,
        "cnn_timestamp": int(time.time() * 1000),
        "risk_score": round(random.uniform(0.0, 1.0), 2),
    }
