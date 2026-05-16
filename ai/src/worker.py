import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import json
import redis
from config import REDIS_HOST, REDIS_PORT, CSI_STREAM_NAME
from core.orchestrator import Orchestrator


def main():
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
    orchestrator = Orchestrator()
    last_id = "$"

    print(f"worker started — listening on {CSI_STREAM_NAME}")
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
