import time
from collections import defaultdict, deque

import numpy as np
import redis

from config import REDIS_HOST, REDIS_PORT, ANALYSIS_STREAM
from activity_engine.preprocessing import Preprocessor
from activity_engine.model_engine import ActivityEngine
from core.risk_scoring import compute_risk

SENSOR1_ID = "NODE001"   # CNN 추론 센서
SENSOR2_ID = "NODE002"   # 낙상 검증 센서 (rule-based)

FALL_CONFIRM_WINDOW_SEC   = 5.0   # FALL 판정 시 D1에서 소급 확인할 시간(초)
SENSOR2_MOVEMENT_THRESH   = 0.03  # D1 에너지 표준편차 임계값 (이 이상이면 움직임 있음)
SENSOR2_HISTORY_MAXLEN    = 450   # 최대 보관 프레임 수 (~15초 @ 30fps)


class Orchestrator:
    def __init__(self):
        self._r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
        self._preprocessors: dict[str, Preprocessor] = defaultdict(Preprocessor)
        self._engine = ActivityEngine()

        # D1 에너지 이력: deque of (timestamp_sec, energy)
        self._sensor2_history: deque[tuple[float, float]] = deque(
            maxlen=SENSOR2_HISTORY_MAXLEN
        )

    # ------------------------------------------------------------------ #
    #  D1 헬퍼                                                             #
    # ------------------------------------------------------------------ #

    def _update_sensor2(self, csi_matrix: list) -> None:
        energy = float(np.mean(np.array(csi_matrix, dtype=np.float32)) / 20.0)
        self._sensor2_history.append((time.time(), energy))

    def _sensor2_had_movement(self) -> "bool | None":
        """
        최근 FALL_CONFIRM_WINDOW_SEC 내 D1 에너지 변동을 확인.
        - True  : 움직임 감지 → 실제 낙상
        - False : 변동 없음   → 소파 눕기 등 오탐
        - None  : 데이터 부족 → D1 미연결, 판단 불가
        """
        now = time.time()
        cutoff = now - FALL_CONFIRM_WINDOW_SEC
        recent = [e for t, e in self._sensor2_history if t >= cutoff]
        if len(recent) < 5:
            return None
        return float(np.std(recent)) > SENSOR2_MOVEMENT_THRESH

    # ------------------------------------------------------------------ #
    #  메인 처리                                                           #
    # ------------------------------------------------------------------ #

    def process(self, node_id: str, seq_num: int, csi_matrix: list) -> bool:
        """
        CSI 프레임 1개를 처리해 분석 결과를 csi_analysis_stream에 xadd.
        슬라이딩 윈도우가 아직 안 찼으면 False 반환.
        """
        if node_id == SENSOR2_ID:
            self._update_sensor2(csi_matrix)
            return True

        # D0: CNN 추론
        window = self._preprocessors[node_id].push(csi_matrix)
        if window is None:
            return False

        label, confidence, energy, probs = self._engine.predict(window)

        # 두 센서 낙상 검증: D1이 움직임을 명시적으로 확인한 경우만 FALL 유지
        fall_confirmed = False
        if label == "FALL":
            if self._sensor2_had_movement() is True:
                fall_confirmed = True
            else:
                # D1 미감지 또는 데이터 부족 → MOVE로 강제 재분류
                label = "MOVE"
                confidence = float(probs[1])

        risk_score, is_anomaly = compute_risk(label, confidence, energy)

        s2_movement = self._sensor2_had_movement()
        self._r.xadd(
            ANALYSIS_STREAM,
            {
                "node_id":        node_id,
                "seq_num":        seq_num,
                "label":          label,
                "cnn_score":      confidence,
                "energy":         energy,
                "risk_score":     risk_score,
                "is_anomaly":     "true" if is_anomaly else "false",
                "fall_confirmed": "true" if fall_confirmed else "false",
                "cnn_timestamp":  int(time.time() * 1000),
                "d1_movement":    "true" if s2_movement is True else ("false" if s2_movement is False else "none"),
                "d1_history_len": len(self._sensor2_history),
            },
            maxlen=600,
        )
        return True
