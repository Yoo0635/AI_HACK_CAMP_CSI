from llama_cpp import Llama

from config import GGUF_MODEL_PATH

PROMPT_TEMPLATE = """당신은 병원 병동의 환자 모니터링 AI입니다.
아래 센서 분석 결과를 바탕으로 현재 상황을 한국어로 2문장 이내로 요약하세요.

- 감지 상태: {label}
- CNN 신뢰도: {cnn_score:.1%}
- 위험 지수: {risk_score:.1f} / 100
- 에너지 수치: {energy:.2f}

요약:"""


class SummaryEngine:
    def __init__(self):
        self._llm = Llama(
            model_path=GGUF_MODEL_PATH,
            n_ctx=512,
            n_threads=4,
            verbose=False,
        )

    def summarize(
        self,
        label: str,
        cnn_score: float,
        risk_score: float,
        energy: float,
    ) -> str:
        prompt = PROMPT_TEMPLATE.format(
            label=label,
            cnn_score=cnn_score,
            risk_score=risk_score,
            energy=energy,
        )

        result = self._llm(
            prompt,
            max_tokens=128,
            temperature=0.3,
            stop=["\n\n"],
        )

        return result["choices"][0]["text"].strip()
