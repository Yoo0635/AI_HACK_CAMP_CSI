import os
import unittest

from cryptography.fernet import Fernet


os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("REDIS_PORT", "6379")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("FERNET_KEY", Fernet.generate_key().decode("utf-8"))

from fastapi import WebSocketDisconnect

from backend.config.database import Base, SessionLocal, engine
from backend.entities import AnalysisResult, Bed
from backend.services import csi_ws_service


class FakeRedisAsync:
    def __init__(self, batches):
        self.batches = list(batches)

    async def xread(self, streams, count=1, block=3000):
        if self.batches:
            return self.batches.pop(0)
        return []


class FakeWebSocket:
    def __init__(self, stop_after):
        self.stop_after = stop_after
        self.sent = []

    async def send_json(self, payload):
        self.sent.append(payload)
        if len(self.sent) >= self.stop_after:
            raise WebSocketDisconnect()


class CsiWsServiceTestCase(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)

    def tearDown(self):
        Base.metadata.drop_all(bind=engine)

    async def test_stream_alert_sends_init_then_alert_risk_score(self):
        db = SessionLocal()
        original_redis_async_client = csi_ws_service.redis_async_client
        csi_ws_service.redis_async_client = FakeRedisAsync(
            batches=[
                [
                    (
                        "csi_analysis_stream",
                        [
                            (
                                "1-0",
                                {
                                    "node_id": "node-1",
                                    "label": "FALL",
                                    "cnn_timestamp": "1711111111",
                                    "risk_score": "0.91",
                                    "is_anomaly": "true",
                                },
                            )
                        ],
                    )
                ],
                [
                    (
                        "csi_analysis_stream",
                        [
                            (
                                "2-0",
                                {
                                    "node_id": "node-1",
                                    "label": "FALL",
                                    "cnn_timestamp": "1711111112",
                                    "risk_score": "0.93",
                                    "is_anomaly": "true",
                                },
                            )
                        ],
                    )
                ],
            ]
        )

        try:
            bed = Bed(
                bed_id="bed-1",
                node_id="node-1",
                nickname="테스트 병상",
                age=72,
                disease="none",
            )
            db.add(bed)
            db.commit()

            db.add(
                AnalysisResult(
                    bed_id=bed.id,
                    secure_log=b"encrypted",
                    sllm_summary="요약",
                    sllm_timestamp=1711111111,
                )
            )
            db.commit()

            ws = FakeWebSocket(stop_after=2)

            with self.assertRaises(WebSocketDisconnect):
                await csi_ws_service.stream_alert(ws, db)

            self.assertEqual(
                ws.sent,
                [
                    {
                        "type": "INIT_ALERT",
                        "bed_id": "bed-1",
                        "nickname": "테스트 병상",
                        "label": "FALL",
                        "cnn_timestamp": 1711111111,
                        "sllm_summary": "요약",
                        "risk_score": 0.91,
                    },
                    {
                        "type": "ALERT_RISK_SCORE",
                        "risk_score": 0.93,
                    },
                ],
            )
        finally:
            csi_ws_service.redis_async_client = original_redis_async_client
            db.close()

    async def test_stream_alert_falls_back_when_latest_result_missing(self):
        db = SessionLocal()
        original_redis_async_client = csi_ws_service.redis_async_client
        csi_ws_service.redis_async_client = FakeRedisAsync(
            batches=[
                [
                    (
                        "csi_analysis_stream",
                        [
                            (
                                "1-0",
                                {
                                    "node_id": "node-1",
                                    "label": "FALL",
                                    "cnn_timestamp": "1711111111",
                                    "risk_score": "0.91",
                                    "is_anomaly": "true",
                                },
                            )
                        ],
                    )
                ]
            ]
        )

        try:
            db.add(
                Bed(
                    bed_id="bed-1",
                    node_id="node-1",
                    nickname="테스트 병상",
                    age=72,
                    disease="none",
                )
            )
            db.commit()

            ws = FakeWebSocket(stop_after=1)

            with self.assertRaises(WebSocketDisconnect):
                await csi_ws_service.stream_alert(ws, db)

            self.assertEqual(
                ws.sent,
                [
                    {
                        "type": "INIT_ALERT",
                        "bed_id": "bed-1",
                        "nickname": "테스트 병상",
                        "label": "FALL",
                        "cnn_timestamp": 1711111111,
                        "sllm_summary": "none",
                        "risk_score": 0.91,
                    }
                ],
            )
        finally:
            csi_ws_service.redis_async_client = original_redis_async_client
            db.close()


if __name__ == "__main__":
    unittest.main()
