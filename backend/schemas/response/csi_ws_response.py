from pydantic import BaseModel


class RiskScoreResponse(BaseModel):
    type: str = "RISK_SCORE"
    node_id: str
    risk_score: float


class InitAlertResponse(BaseModel):
    type: str = "INIT_ALERT"
    bed_id: str
    nickname: str
    label: str
    cnn_timestamp: int
    sllm_summary: str
    risk_score: float

class AlertRiskScoreResponse(BaseModel):
    type: str = "ALERT_RISK_SCORE"
    risk_score: float

class WebSocketErrorResponse(BaseModel):
    type: str = "ERROR"
    message: str
    error_code: str
    details: dict | None = None
