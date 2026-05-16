from backend.utils.gorilla import compress_float64_sequence


def compress_risk_scores(risk_scores: list[float]) -> bytes:
    return compress_float64_sequence(risk_scores)
