import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import json
import time
import threading
import redis
from config import REDIS_HOST, REDIS_PORT, CSI_STREAM_NAME, ANALYSIS_STREAM
from core.orchestrator import Orchestrator

SLLM_COOLDOWN_SEC = 120
SLLM_RISK_THRESHOLD = 80.1


def sllm_loop():
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
    try:
        from summary_engine.llama_cpp_wrapper import SummaryEngine
        engine = SummaryEngine()
        print("sllm engine loaded", flush=True)
    except Exception as e:
        print(f"sllm engine 로드 실패 (LLM 비활성): {e}", flush=True)
        return

    last_id = "$"
    last_summary_time: dict = {}

    print("sllm worker started", flush=True)
    while True:
        try:
            entries = r.xread({ANALYSIS_STREAM: last_id}, block=1000, count=1)
        except Exception:
            continue
        if not entries:
            continue
        for _, messages in entries:
            for msg_id, data in messages:
                last_id = msg_id

                is_anomaly = data.get(b"is_anomaly", b"false").decode() == "true"
                if not is_anomaly:
                    continue

                try:
                    risk_score = float(data.get(b"risk_score", b"0"))
                except (ValueError, TypeError):
                    continue
                if risk_score < SLLM_RISK_THRESHOLD:
                    continue

                node_id = data.get(b"node_id", b"").decode()
                now = time.time()
                if now - last_summary_time.get(node_id, 0) < SLLM_COOLDOWN_SEC:
                    continue
                last_summary_time[node_id] = now

                label = data.get(b"label", b"").decode()
                cnn_score = float(data.get(b"cnn_score", b"0"))
                energy = float(data.get(b"energy", b"0"))

                print(f"[sllm] {node_id} 요약 생성 중...", flush=True)
                try:
                    summary = engine.summarize(label, cnn_score, risk_score, energy)
                    r.xadd(ANALYSIS_STREAM, {
                        "node_id": node_id,
                        "sllm_summary": summary,
                        "sllm_timestamp": int(time.time() * 1000),
                    }, maxlen=600)
                    print(f"[sllm] {node_id} 완료: {summary[:80]}", flush=True)
                except Exception as e:
                    print(f"[sllm] 요약 실패: {e}", flush=True)


def main():
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
    orchestrator = Orchestrator()
    last_id = "$"

    t = threading.Thread(target=sllm_loop, daemon=True)
    t.start()

    print(f"worker started — listening on {CSI_STREAM_NAME}", flush=True)
    while True:
        entries = r.xread({CSI_STREAM_NAME: last_id}, block=1000, count=10)
        if not entries:
            continue
        for _, messages in entries:
            for msg_id, data in messages:
                node_id = data[b"node_id"].decode()
                seq_num = int(data[b"seq_num"])
                csi_matrix = json.loads(data[b"csi_matrix"])
                ready = orchestrator.process(node_id, seq_num, csi_matrix)
                if ready:
                    print(f"[{node_id}] seq={seq_num} → analyzed", flush=True)
                last_id = msg_id


if __name__ == "__main__":
    main()
