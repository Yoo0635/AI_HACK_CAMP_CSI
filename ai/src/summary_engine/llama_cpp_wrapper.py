from llama_cpp import Llama

from config import GGUF_MODEL_PATH

PROMPT_TEMPLATE = """당신은 병원 병동의 환자 모니터링 AI입니다.
아래 센서 분석 결과를 바탕으로, 환자의 현재 상황과 수치들의 의미를 의료진이 파악하기 쉽도록 자세하게 설명하세요.

[센서 데이터]
- 감지 상태: {label}
- CNN 신뢰도: {cnn_score:.1%}
- 위험 지수: {risk_score:.1f} / 100
- 에너지 수치: {energy:.2f}

[작성 가이드]
1. 현재 감지된 상태({label})가 무엇인지 언급하고, 인공지능의 분석 신뢰도({cnn_score:.1%})를 함께 설명하세요.
2. 위험 지수({risk_score:.1f}/100)와 에너지 수치({energy:.2f})가 현재 환자의 건강 상태나 행동에 어떤 의미를 가지는지 종합적으로 분석하여 서술하세요.
3. 의료진이 즉각적인 조치를 취해야 하는 상황인지, 혹은 지속적인 관찰이 필요한 상황인지 행동 지침을 포함하세요.

상황 설명:"""


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
            max_tokens=512,
            temperature=0.3,
            stop=["\n\n"],
        )

        return result["choices"][0]["text"].strip()
