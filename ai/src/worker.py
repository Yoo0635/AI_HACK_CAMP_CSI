import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import redis
from config import REDIS_URL, CSI_STREAM
from core.orchestrator import Orchestrator


def main():
    r = redis.from_url(REDIS_URL)
    orchestrator = Orchestrator()
    last_id = "$"

    print(f"worker started — listening on {CSI_STREAM}")
    while True:
        entries = r.xread({CSI_STREAM: last_id}, block=1000, count=10)
        if not entries:
            continue
        for _, messages in entries:
            for msg_id, data in messages:
                orchestrator.process(data)
                last_id = msg_id


if __name__ == "__main__":
    main()
