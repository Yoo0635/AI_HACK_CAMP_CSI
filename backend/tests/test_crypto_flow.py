import os
import unittest

from cryptography.fernet import Fernet


os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("REDIS_PORT", "6379")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("FERNET_KEY", Fernet.generate_key().decode("utf-8"))

from backend.config.database import Base, SessionLocal, engine
from backend.entities import AnalysisResult, Bed
from backend.services.analysis_result_service import save_analysis_result_db
from backend.services import risk_score_secure_service
from backend.utils.fernet_crypto import decrypt_bytes, encrypt_bytes, get_fernet
from backend.utils.gorilla_compressor import compress_risk_scores


class FakeRedis:
    def __init__(self, stream_entries=None):
        self.stream_entries = stream_entries or []

    def xrange(self, name, min="-", max="+", count=None):
        if count is None:
            return list(self.stream_entries)

        return list(self.stream_entries[:count])


class CryptoFlowTestCase(unittest.TestCase):
    def setUp(self):
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        get_fernet.cache_clear()

    def tearDown(self):
        Base.metadata.drop_all(bind=engine)

    def test_encrypt_log_round_trip(self):
        plaintext = b"sensitive-log"

        encrypted = encrypt_bytes(plaintext)

        self.assertNotEqual(encrypted, plaintext)
        self.assertEqual(decrypt_bytes(encrypted), plaintext)

    def test_analysis_result_db_encrypts_secure_log(self):
        db = SessionLocal()

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

            result = save_analysis_result_db(
                db=db,
                fields={
                    "node_id": "node-1",
                    "risk_score": 0.9,
                    "sllm_summary": "낙상 위험 요약",
                    "sllm_timestamp": 1711111111,
                },
                risk_scores=[0.1, 0.4, 0.9],
            )
            db.commit()

            stored = db.query(AnalysisResult).filter_by(id=result.id).one()

            self.assertEqual(stored.sllm_summary, "낙상 위험 요약")
            self.assertEqual(
                decrypt_bytes(stored.secure_log),
                compress_risk_scores([0.1, 0.4, 0.9]),
            )
        finally:
            db.close()

    def test_store_secure_risk_scores_reads_node_window_and_saves(self):
        db = SessionLocal()
        original_redis = risk_score_secure_service.redis_client
        risk_score_secure_service.redis_client = FakeRedis(
            stream_entries=[
                ("1-0", {"node_id": "node-1", "risk_score": "0.1"}),
                ("2-0", {"node_id": "node-2", "risk_score": "9.9"}),
                ("3-0", {"node_id": "node-1", "risk_score": "0.2"}),
                ("4-0", {"node_id": "node-1", "risk_score": "0.3"}),
                ("5-0", {"node_id": "node-1", "risk_score": "0.4"}),
                ("6-0", {"node_id": "node-2", "risk_score": "8.8"}),
                ("7-0", {"node_id": "node-1", "risk_score": "0.5"}),
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

            result = risk_score_secure_service.store_secure_risk_scores(
                db=db,
                fields={
                    "node_id": "node-1",
                    "risk_score": 0.3,
                    "sllm_summary": "이상 징후 요약",
                    "sllm_timestamp": 1711111111,
                },
                trigger_message_id="4-0",
            )
            db.commit()

            stored = db.query(AnalysisResult).filter_by(id=result.id).one()

            self.assertEqual(
                decrypt_bytes(stored.secure_log),
                compress_risk_scores([0.1, 0.2, 0.4, 0.5]),
            )
        finally:
            risk_score_secure_service.redis_client = original_redis
            db.close()


if __name__ == "__main__":
    unittest.main()
