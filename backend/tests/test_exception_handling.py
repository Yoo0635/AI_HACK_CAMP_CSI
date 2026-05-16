import os
import unittest

from cryptography.fernet import Fernet
from fastapi import FastAPI
from fastapi.testclient import TestClient
from redis.exceptions import RedisError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("REDIS_PORT", "6379")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("FERNET_KEY", Fernet.generate_key().decode("utf-8"))

from backend.config.database import Base, get_db
from backend.controllers.bed_controller import bed_router
from backend.controllers.csi_controller import csi_router
from backend.controllers.csi_ws_controller import ws_router
from backend.exceptions.global_handler import register_exception_handlers
from backend.services import csi_ws_service


class FakeRedisAsyncError:
    async def xread(self, streams, count=1, block=3000):
        raise RedisError("redis down")


class ExceptionHandlingTestCase(unittest.TestCase):
    def setUp(self):
        self.database_path = "./test_exception_handling.db"
        self.test_engine = create_engine(
            f"sqlite:///{self.database_path}",
            connect_args={"check_same_thread": False},
        )
        self.TestSessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.test_engine,
        )
        Base.metadata.drop_all(bind=self.test_engine)
        Base.metadata.create_all(bind=self.test_engine)

    def tearDown(self):
        Base.metadata.drop_all(bind=self.test_engine)
        self.test_engine.dispose()
        if os.path.exists(self.database_path):
            os.remove(self.database_path)

    def create_app(self):
        app = FastAPI()
        register_exception_handlers(app)
        app.include_router(bed_router)
        app.include_router(csi_router)
        app.include_router(ws_router)

        def override_get_db():
            db = self.TestSessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        return app

    def test_bed_validation_error_returns_detailed_korean_message(self):
        app = self.create_app()
        client = TestClient(app)

        response = client.post(
            "/beds",
            json={
                "bed_id": "   ",
                "node_id": "node-1",
                "nickname": "테스트",
                "age": -1,
                "disease": "none",
            },
        )

        self.assertEqual(response.status_code, 422)
        payload = response.json()
        self.assertEqual(payload["error_code"], "INVALID_REQUEST")
        self.assertEqual(payload["path"], "/beds")
        self.assertEqual(payload["errors"][0]["field"], "bed_id")
        self.assertEqual(payload["errors"][0]["message"], "최소 1자 이상 입력해야 합니다.")
        self.assertEqual(payload["errors"][1]["field"], "age")
        self.assertEqual(payload["errors"][1]["message"], "0 이상이어야 합니다.")

    def test_duplicate_bed_returns_conflict_with_details(self):
        app = self.create_app()
        client = TestClient(app)

        first_response = client.post(
            "/beds",
            json={
                "bed_id": "bed-1",
                "node_id": "node-1",
                "nickname": "테스트 병상",
                "age": 72,
                "disease": "none",
            },
        )
        second_response = client.post(
            "/beds",
            json={
                "bed_id": "bed-1",
                "node_id": "node-2",
                "nickname": "다른 병상",
                "age": 68,
                "disease": "none",
            },
        )

        self.assertEqual(first_response.status_code, 201)
        self.assertEqual(second_response.status_code, 409)
        payload = second_response.json()
        self.assertEqual(payload["error_code"], "BED_DUPLICATE")
        self.assertEqual(payload["details"]["field"], "bed_id")
        self.assertEqual(payload["details"]["value"], "bed-1")

    def test_invalid_csi_packet_size_returns_detailed_error(self):
        app = self.create_app()
        client = TestClient(app)

        response = client.post(
            "/csi/raw",
            content=b"short-packet",
            headers={"content-type": "application/octet-stream"},
        )

        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertEqual(payload["error_code"], "CSI_PACKET_SIZE_INVALID")
        self.assertEqual(payload["details"]["expected_size"], 280)
        self.assertEqual(payload["details"]["actual_size"], len(b"short-packet"))

    def test_websocket_stream_error_sends_korean_error_payload(self):
        original_redis_async_client = csi_ws_service.redis_async_client
        csi_ws_service.redis_async_client = FakeRedisAsyncError()

        try:
            app = self.create_app()
            client = TestClient(app)

            with client.websocket_connect("/ws/csi/node-1") as websocket:
                payload = websocket.receive_json()

            self.assertEqual(payload["type"], "ERROR")
            self.assertEqual(payload["error_code"], "WS_STREAM_READ_FAILED")
            self.assertEqual(
                payload["message"],
                "실시간 분석 스트림을 읽지 못했습니다. 연결을 다시 시도해주세요.",
            )
        finally:
            csi_ws_service.redis_async_client = original_redis_async_client


if __name__ == "__main__":
    unittest.main()
