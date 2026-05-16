import { useState } from "react";
import { FiSend } from "react-icons/fi";
import { FaThermometerHalf, FaTint } from "react-icons/fa";
import type { BedData } from "../App";

interface BedCardProps {
  bed: BedData;
}

const GRAPH_HEIGHT = 20;
const GRAPH_HISTORY_SIZE = 20;
const ALERT_THRESHOLD = 0.7;

function normalizeRiskScore(score: number) {
  return Math.max(0, score);
}

const BedCard = ({ bed }: BedCardProps) => {
  const [riskScore, setRiskScore] = useState<number>(0);
  const [history, setHistory] = useState<number[]>(
    Array(GRAPH_HISTORY_SIZE).fill(0),
  );

  const activeNodeId = bed.node_id;

  // 그래프 UI 업데이트 함수
  const updateGraph = (score: number) => {
    const safeScore = normalizeRiskScore(score);
    setRiskScore(safeScore);
    setHistory((prev) => [...prev.slice(1), safeScore]);
  };

  // 🌟 백엔드 통신 로직 제거 및 가짜 데이터 생성 로직으로 대체
  const handleTestUI = () => {
    // 0.0 ~ 1.0 사이의 랜덤한 수치를 만들어 그래프와 경고등 UI가 잘 작동하는지 확인합니다.
    const randomScore = Math.random();
    console.log(
      `[${bed.bed_id}] 가짜 위험도 데이터 생성:`,
      randomScore.toFixed(2),
    );
    updateGraph(randomScore);
  };

  const isWarning = riskScore >= ALERT_THRESHOLD;

  const graphMaxValue = Math.max(1, ALERT_THRESHOLD, riskScore, ...history);

  const graphPath = history
    .map((val, i) => {
      const x = (i / (history.length - 1)) * 100;
      const normalizedY = val / graphMaxValue;
      const y = GRAPH_HEIGHT - normalizedY * GRAPH_HEIGHT;

      return `${i === 0 ? "M" : "L"} ${x},${y}`;
    })
    .join(" ");

  return (
    <div
      className={`relative overflow-hidden rounded-2xl border transition-all duration-500 flex flex-col h-full ${
        isWarning
          ? "bg-red-950/20 border-red-500 shadow-[0_0_20px_rgba(239,68,68,0.2)]"
          : "bg-[#151821] border-gray-800"
      }`}
    >
      <div className="p-5 relative z-10">
        <div className="flex justify-between items-start mb-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span
                className={`w-2 h-2 rounded-full ${
                  isWarning ? "bg-red-500 animate-ping" : "bg-green-500"
                }`}
              />
              <h3 className="font-bold text-lg text-white">{bed.bed_id}</h3>
            </div>

            <p className="text-gray-400 text-sm">
              {bed.nickname} ({bed.age}세)
            </p>

            <p className="text-[10px] text-gray-500 mt-1 uppercase tracking-widest">
              ID: {activeNodeId || "node_id 없음"}
            </p>
          </div>

          <button
            onClick={handleTestUI}
            className="p-2 bg-gray-800 hover:bg-blue-600 rounded-lg transition-colors group"
            title="그래프 UI 테스트"
          >
            <FiSend className="text-gray-400 group-hover:text-white" />
          </button>
        </div>

        <div className="flex items-end justify-between mb-6">
          <div className="flex flex-col">
            <span className="text-gray-500 text-xs font-medium mb-1 uppercase tracking-wider">
              Risk Score
            </span>

            <span
              className={`text-4xl font-black tracking-tighter ${
                isWarning ? "text-red-500" : "text-green-400"
              }`}
            >
              {riskScore.toFixed(2)}
            </span>

            <span className="text-[10px] text-gray-500 mt-1">
              0.7이상 : 위험
            </span>
          </div>

          <div className="w-32 h-12">
            <svg
              viewBox={`0 0 100 ${GRAPH_HEIGHT}`}
              className="w-full h-full"
              preserveAspectRatio="none"
            >
              <line
                x1="0"
                y1={
                  GRAPH_HEIGHT -
                  (ALERT_THRESHOLD / graphMaxValue) * GRAPH_HEIGHT
                }
                x2="100"
                y2={
                  GRAPH_HEIGHT -
                  (ALERT_THRESHOLD / graphMaxValue) * GRAPH_HEIGHT
                }
                stroke="rgba(250,204,21,0.55)"
                strokeWidth="0.6"
                strokeDasharray="2 2"
              />

              <path
                d={graphPath}
                fill="none"
                stroke={isWarning ? "#ef4444" : "#4ade80"}
                strokeWidth="2"
                className="transition-all duration-300"
              />
            </svg>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3 mt-auto">
          <div className="bg-[#0B0E14] rounded-xl p-3 text-center border border-gray-800">
            <FaThermometerHalf className="text-orange-400 mx-auto mb-1" />
            <span className="block font-bold text-sm text-white">
              {isWarning ? "37.8°" : "36.5°"}
            </span>
          </div>

          <div className="bg-[#0B0E14] rounded-xl p-3 text-center border border-gray-800">
            <FaTint className="text-blue-400 mx-auto mb-1" />
            <span className="block font-bold text-sm text-white">98%</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default BedCard;
