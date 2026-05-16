import argparse
import json
import os
import sys
import time

import numpy as np
import redis

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))
from config import REDIS_HOST, REDIS_PORT, CSI_STREAM_NAME

LABELS = ("NORMAL", "MOVE", "FALL")


def collect(label: str, duration: int, output_dir: str) -> None:
    r = redis.Redis(host=REDIS_HOST, port=int(REDIS_PORT))
    os.makedirs(output_dir, exist_ok=True)

    samples = []
    last_id = "$"
    deadline = time.time() + duration

    print(f"[{label}] 수집 시작 — {duration}초")

    while time.time() < deadline:
        block_ms = min(int((deadline - time.time()) * 1000), 1000)
        if block_ms <= 0:
            break

        entries = r.xread({CSI_STREAM_NAME: last_id}, block=block_ms, count=10)
        if not entries:
            continue

        for _, messages in entries:
            for msg_id, data in messages:
                raw = data.get(b"csi_matrix") or data.get("csi_matrix")
                if raw is None:
                    continue
                samples.append(json.loads(raw))
                last_id = msg_id

    arr = np.array(samples, dtype=np.float32)
    filename = f"{label}_{int(time.time())}_{len(arr)}samples.npy"
    path = os.path.join(output_dir, filename)
    np.save(path, arr)

    print(f"저장 완료: {path}  ({len(arr)}개 샘플)")


def main():
    parser = argparse.ArgumentParser(description="CSI 현장 데이터 수집기")
    parser.add_argument("--label", required=True, choices=LABELS)
    parser.add_argument("--duration", type=int, default=60, help="수집 시간 (초)")
    parser.add_argument("--output", default="data/raw", help="저장 디렉터리")
    args = parser.parse_args()

    collect(args.label, args.duration, args.output)


if __name__ == "__main__":
    main()