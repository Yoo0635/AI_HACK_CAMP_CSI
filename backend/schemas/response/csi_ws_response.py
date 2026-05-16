from pydantic import BaseModel


class RiskScoreResponse(BaseModel):
    type: str = "RISK_SCORE"
    node_id: str
    risk_score: float
    

class WebSocketErrorResponse(BaseModel):
    type: str = "ERROR"
    message: str
    error_code: str
    details: dict | None = None
