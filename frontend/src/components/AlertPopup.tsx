import { useEffect, useMemo, useRef } from "react";
import { FiAlertOctagon, FiX } from "react-icons/fi";

export interface AlertData {
  bed_id: string;
  nickname: string;
  label: string;
  cnn_timestamp: string;
  sllm_summary: string;
  risk_score: number;
}

interface AlertPopupProps {
  data: AlertData;
  riskHistory: number[];
  historySize: number;
  onClose: () => void;
}

const ALERT_THRESHOLD = 80.1;
const GRAPH_HEIGHT = 40;

const normalizeRiskScore = (score: number) => {
  return Math.max(0, score);
};

const AlertPopup = ({
  data,
  riskHistory,
  historySize,
  onClose,
}: AlertPopupProps) => {
  const audioContextRef = useRef<AudioContext | null>(null);
  const soundTimerRef = useRef<number | null>(null);

  useEffect(() => {
    const AudioContextClass =
      window.AudioContext ||
      (
        window as typeof window & {
          webkitAudioContext?: typeof AudioContext;
        }
      ).webkitAudioContext;

    if (!AudioContextClass) {
      console.warn("이 브라우저는 Web Audio API를 지원하지 않습니다.");
      return;
    }

    const audioContext = new AudioContextClass();
    audioContextRef.current = audioContext;

    const playSirenPattern = () => {
      try {
        const now = audioContext.currentTime;

        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();

        oscillator.type = "sawtooth";

        oscillator.frequency.setValueAtTime(520, now);
        oscillator.frequency.linearRampToValueAtTime(1200, now + 0.45);
        oscillator.frequency.linearRampToValueAtTime(520, now + 0.9);
        oscillator.frequency.linearRampToValueAtTime(1200, now + 1.35);
        oscillator.frequency.linearRampToValueAtTime(520, now + 1.8);

        gainNode.gain.setValueAtTime(0.0001, now);
        gainNode.gain.exponentialRampToValueAtTime(0.18, now + 0.05);
        gainNode.gain.setValueAtTime(0.18, now + 1.7);
        gainNode.gain.exponentialRampToValueAtTime(0.0001, now + 1.85);

        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);

        oscillator.start(now);
        oscillator.stop(now + 1.9);
      } catch (error) {
        console.warn("사이렌 소리를 재생하지 못했습니다.", error);
      }
    };

    playSirenPattern();

    soundTimerRef.current = window.setInterval(() => {
      playSirenPattern();
    }, 2000);

    return () => {
      if (soundTimerRef.current !== null) {
        window.clearInterval(soundTimerRef.current);
        soundTimerRef.current = null;
      }

      if (audioContextRef.current) {
        void audioContextRef.current.close();
        audioContextRef.current = null;
      }
    };
  }, []);

  const handleClose = () => {
    if (soundTimerRef.current !== null) {
      window.clearInterval(soundTimerRef.current);
      soundTimerRef.current = null;
    }

    if (audioContextRef.current) {
      void audioContextRef.current.close();
      audioContextRef.current = null;
    }

    onClose();
  };

  const latestScore = normalizeRiskScore(data.risk_score);

  const visibleHistory = useMemo(() => {
    const safeHistory = riskHistory.map(normalizeRiskScore);
    return safeHistory.slice(-historySize);
  }, [riskHistory, historySize]);

  const graphMaxValue = useMemo(() => {
    const maxValue = Math.max(
      1,
      ALERT_THRESHOLD,
      latestScore,
      ...visibleHistory,
    );

    return maxValue;
  }, [latestScore, visibleHistory]);

  const graphPath = useMemo(() => {
    if (visibleHistory.length === 0) {
      return "";
    }

    if (visibleHistory.length === 1) {
      const y =
        GRAPH_HEIGHT - (visibleHistory[0] / graphMaxValue) * GRAPH_HEIGHT;
      return `M 0,${y} L 100,${y}`;
    }

    return visibleHistory
      .map((value, index) => {
        const x = (index / (visibleHistory.length - 1)) * 100;
        const y = GRAPH_HEIGHT - (value / graphMaxValue) * GRAPH_HEIGHT;

        return `${index === 0 ? "M" : "L"} ${x},${y}`;
      })
      .join(" ");
  }, [visibleHistory, graphMaxValue]);

  const latestPointY =
    GRAPH_HEIGHT - (latestScore / graphMaxValue) * GRAPH_HEIGHT;

  const thresholdY =
    GRAPH_HEIGHT - (ALERT_THRESHOLD / graphMaxValue) * GRAPH_HEIGHT;

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center animate-in fade-in duration-300">
      <div className="bg-red-950 border-4 border-red-500 rounded-2xl p-6 md:p-8 max-w-lg w-full shadow-[0_0_50px_rgba(239,68,68,0.6)] relative">
        <button
          onClick={handleClose}
          className="absolute top-4 right-4 text-red-300 hover:text-white transition"
        >
          <FiX size={28} />
        </button>

        <div className="flex justify-center mb-4 text-red-500 animate-pulse">
          <FiAlertOctagon size={64} />
        </div>

        <h1 className="text-3xl font-black text-white text-center mb-6">
          <span className="text-red-400">{data.bed_id}</span> {data.nickname}{" "}
          환자 위험합니다!
        </h1>

        <div className="bg-black/40 rounded-lg p-4 mb-6 text-center text-gray-300 text-sm border border-red-500/30">
          <p>
            현재 상태: <span className="text-white font-bold">{"낙상"}</span>
          </p>
          <p>
            신호 발생 시각:{" "}
            <span className="text-white">{data.cnn_timestamp}</span>
          </p>
        </div>

        <div className="text-center mb-6">
          <p className="text-2xl font-bold text-yellow-300">
            🚨 {data.sllm_summary || "긴급 상황 발생"} 🚨
          </p>
        </div>

        <div className="bg-red-900/50 rounded-xl p-4 border border-red-500/50 mb-4">
          <div className="flex justify-between items-center mb-4">
            <span className="text-red-200 font-bold text-lg">
              AI 위험도 평가 (Risk Score)
            </span>
            <span className="text-4xl font-black text-white">
              {latestScore.toFixed(2)}
            </span>
          </div>

          <div className="bg-black/40 rounded-lg p-3 border border-red-500/30">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-red-200 font-semibold">
                실시간 위험 지수 변화
              </span>
              <span className="text-xs text-gray-300">
                최근 {visibleHistory.length}/{historySize}개 수신값
              </span>
            </div>

            <div className="h-24 w-full">
              <svg
                viewBox={`0 0 100 ${GRAPH_HEIGHT}`}
                className="w-full h-full"
                preserveAspectRatio="none"
              >
                <line
                  x1="0"
                  y1={thresholdY}
                  x2="100"
                  y2={thresholdY}
                  stroke="rgba(250,204,21,0.7)"
                  strokeWidth="0.8"
                  strokeDasharray="3 3"
                />

                <line
                  x1="0"
                  y1={GRAPH_HEIGHT}
                  x2="100"
                  y2={GRAPH_HEIGHT}
                  stroke="rgba(255,255,255,0.15)"
                  strokeWidth="0.8"
                />

                <path
                  d={graphPath}
                  fill="none"
                  stroke="#facc15"
                  strokeWidth="2.2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />

                <circle cx="100" cy={latestPointY} r="2.2" fill="#ffffff" />
              </svg>
            </div>

            <div className="flex justify-between text-[10px] text-gray-400 mt-1">
              <span>0.00</span>
              <span className="text-yellow-300">
                위험 기준 {ALERT_THRESHOLD.toFixed(2)}
              </span>
              <span>Max {graphMaxValue.toFixed(2)}</span>
            </div>
          </div>
        </div>

        <p className="text-center text-xs text-red-200/80">
          위험 점수가 기준치를 초과했습니다. 즉시 환자 상태를 확인해주세요.
        </p>
      </div>
    </div>
  );
};

export default AlertPopup;
