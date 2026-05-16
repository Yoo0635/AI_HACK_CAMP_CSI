import numpy as np

BASE_SCORE = {
    "NORMAL": 20,
    "MOVE":   65,
    "FALL":   85,
}
ENERGY_MAX_BONUS = 15
ANOMALY_THRESHOLD = 43


def compute_risk(label: str, confidence: float, energy: float) -> tuple[float, bool]:
    """
    risk_score = 기본점수 × confidence + 에너지 보정 (최대 15점)
    is_anomaly = risk_score > 43

    returns: (risk_score, is_anomaly)
    """
    base = BASE_SCORE.get(label, 0)

    # 에너지 보정: energy를 0~1로 정규화 후 최대 15점 가산
    energy_bonus = float(np.clip(energy / 100.0, 0.0, 1.0)) * ENERGY_MAX_BONUS

    risk_score = base * confidence + energy_bonus
    is_anomaly = risk_score > ANOMALY_THRESHOLD

    return round(risk_score, 4), is_anomaly
