import json
import os
import sys
import threading
import time

import redis

sys.path.insert(0, os.path.dirname(__file__))

from config import REDIS_HOST, REDIS_PORT, CSI_STREAM_NAME, ANALYSIS_STREAM
from core.orchestrator import Orchestrator
from summary_engine.llama_cpp_wrapper import SummaryEngine


def cnn_loop(orchestrator: Orchestrator) -> None:
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
    last_id = "$"

    print(f"[CNN] 시작 — {CSI_STREAM_NAME} 구독 중")
    while True:
        entries = r.xread({CSI_STREAM_NAME: last_id}, block=1000, count=10)
        if not entries:
            continue

        for _, messages in entries:
            for msg_id, data in messages:
                try:
                    node_id  = (data.get(b"node_id") or b"").decode()
                    seq_num  = int(data.get(b"seq_num") or 0)
                    raw      = data.get(b"csi_matrix") or data.get("csi_matrix")
                    if raw is None:
                        continue
                    csi_matrix = json.loads(raw)
                    orchestrator.process(node_id, seq_num, csi_matrix)
                except Exception as e:
                    print(f"[CNN] 처리 오류: {e}")
                finally:
                    last_id = msg_id


def llm_loop(summary_engine: SummaryEngine) -> None:
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
    last_id = "$"

    print(f"[LLM] 시작 — {ANALYSIS_STREAM} 구독 중")
    while True:
        entries = r.xread({ANALYSIS_STREAM: last_id}, block=1000, count=1)
        if not entries:
            continue

        for _, messages in entries:
            for msg_id, data in messages:
                try:
                    is_anomaly = (data.get(b"is_anomaly") or b"false").decode()
                    if is_anomaly != "true":
                        last_id = msg_id
                        continue

                    label      = (data.get(b"label")     or b"NORMAL").decode()
                    cnn_score  = float(data.get(b"cnn_score")  or 0)
                    risk_score = float(data.get(b"risk_score") or 0)
                    energy     = float(data.get(b"energy")     or 0)

                    summary = summary_engine.summarize(
                        label, cnn_score, risk_score, energy
                    )

                    r.xadd(
                        ANALYSIS_STREAM,
                        {
                            "node_id":        (data.get(b"node_id") or b"").decode(),
                            "seq_num":        (data.get(b"seq_num") or b"0").decode(),
                            "sllm_summary":   summary,
                            "sllm_timestamp": int(time.time() * 1000),
                        },
                        maxlen=600,
                    )
                    print(f"[LLM] 요약 완료: {summary[:40]}...")
                except Exception as e:
                    print(f"[LLM] 처리 오류: {e}")
                finally:
                    last_id = msg_id


def main() -> None:
    orchestrator   = Orchestrator()
    summary_engine = SummaryEngine()

    llm_thread = threading.Thread(
        target=llm_loop,
        args=(summary_engine,),
        daemon=True,
    )
    llm_thread.start()

    cnn_loop(orchestrator)


if __name__ == "__main__":
    main()
