from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    LargeBinary,
    Text,
)

from backend.config.database import Base


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id = Column(Integer, primary_key=True, index=True)
    bed_id = Column(Integer, ForeignKey("beds.id"), nullable=False)
    secure_log = Column(LargeBinary, nullable=False)
    sllm_summary = Column(Text, nullable=False)
    sllm_timestamp = Column(Integer, nullable=False)
