import time

import redis

from config import REDIS_HOST, REDIS_PORT, ANALYSIS_STREAM
from activity_engine.preprocessing import Preprocessor
from activity_engine.model_engine import ActivityEngine
from core.risk_scoring import compute_risk


class Orchestrator:
    def __init__(self):
        self._r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
        self._preprocessor = Preprocessor()
        self._engine = ActivityEngine()

    def process(self, node_id: str, seq_num: int, csi_matrix: list) -> bool:
        """
        CSI 프레임 1개를 처리해 분석 결과를 csi_analysis_stream에 xadd.
        슬라이딩 윈도우가 아직 안 찼으면 False 반환.
        """
        window = self._preprocessor.push(csi_matrix)
        if window is None:
            return False

        label, confidence, energy = self._engine.predict(window)
        risk_score, is_anomaly = compute_risk(label, confidence, energy)

        self._r.xadd(
            ANALYSIS_STREAM,
            {
                "node_id":       node_id,
                "seq_num":       seq_num,
                "label":         label,
                "cnn_score":     confidence,
                "energy":        energy,
                "risk_score":    risk_score,
                "is_anomaly":    "true" if is_anomaly else "false",
                "cnn_timestamp": int(time.time() * 1000),
            },
            maxlen=600,
        )
        return True
