import json
import os
import sys
import time

import numpy as np
import redis

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

from config import REDIS_HOST, REDIS_PORT, CSI_STREAM_NAME, ANALYSIS_STREAM
from core.orchestrator import Orchestrator

LABELS = ["NORMAL", "MOVE", "FALL"]


def inject_dummy_frames(n: int = 30, label_hint: str = "NORMAL") -> None:
    """Redis에 더미 CSI 프레임을 주입해 파이프라인 동작 확인"""
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)

    rng = np.random.default_rng(42)
    print(f"[주입] {n}개 더미 프레임 → {CSI_STREAM_NAME}  (label_hint={label_hint})")

    for i in range(n):
        csi = rng.uniform(0, 20, 64).tolist()
        r.xadd(
            CSI_STREAM_NAME,
            {
                "node_id":    "test_node",
                "seq_num":    i,
                "csi_matrix": json.dumps(csi),
            },
            maxlen=200,
        )
        time.sleep(0.05)

    print("[주입] 완료")


def read_analysis_results(timeout: int = 5) -> None:
    """csi_analysis_stream 최신 결과 출력"""
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
    entries = r.xrevrange(ANALYSIS_STREAM, count=5)
    if not entries:
        print("[결과] csi_analysis_stream 비어 있음")
        return

    print(f"\n[결과] 최근 {len(entries)}개 분석 결과:")
    for msg_id, data in reversed(entries):
        label      = (data.get(b"label")      or b"-").decode()
        cnn_score  = (data.get(b"cnn_score")  or b"-").decode()
        risk_score = (data.get(b"risk_score") or b"-").decode()
        is_anomaly = (data.get(b"is_anomaly") or b"-").decode()
        summary    = (data.get(b"sllm_summary") or b"").decode()

        print(f"  [{label}] score={cnn_score}  risk={risk_score}  anomaly={is_anomaly}")
        if summary:
            print(f"    sLLM: {summary}")


def test_pipeline() -> None:
    """Orchestrator 직접 호출 테스트 (Redis 없이)"""
    print("=== 파이프라인 직접 테스트 ===")
    orchestrator = Orchestrator()

    rng = np.random.default_rng(0)
    passed = 0

    for label in LABELS:
        print(f"\n[{label}] 30프레임 투입 중...")
        for i in range(30):
            csi = rng.uniform(0, 20, 64).tolist()
            ok = orchestrator.process("test", i, csi)
            if ok:
                passed += 1

    print(f"\n추론 성공: {passed}회 (윈도우 20프레임 충족 후)")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="로컬 추론 테스트")
    parser.add_argument("--mode", choices=["pipeline", "inject", "read"], default="pipeline")
    parser.add_argument("--frames", type=int, default=30)
    args = parser.parse_args()

    if args.mode == "pipeline":
        test_pipeline()
    elif args.mode == "inject":
        inject_dummy_frames(args.frames)
    elif args.mode == "read":
        read_analysis_results()
