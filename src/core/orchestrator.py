import json
import redis
from config import REDIS_URL, RESULT_STREAM
from activity_engine.preprocessing import preprocess
from activity_engine.model_engine import ActivityEngine
from core.risk_scoring import compute_risk
from summary_engine.llama_cpp_wrapper import SummaryEngine


class Orchestrator:
    def __init__(self):
        self.r = redis.from_url(REDIS_URL)
        self.activity_engine = ActivityEngine()
        self.summary_engine = SummaryEngine()

    def process(self, data: dict) -> None:
        pass
