from backend.entities.analysis_result import AnalysisResult
from sqlalchemy.orm import Session


def save_analysis_result(
    db: Session,
    bed_id: int,
    secure_log: bytes,
    sllm_summary: str,
    sllm_timestamp: int,
) -> AnalysisResult:
    analysis_result = AnalysisResult(
        bed_id=bed_id,
        secure_log=secure_log,
        sllm_summary=sllm_summary,
        sllm_timestamp=sllm_timestamp,
    )

    db.add(analysis_result)
    db.flush()

    return analysis_result
