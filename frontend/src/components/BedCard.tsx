import { useState, useEffect, useRef } from "react";
import { FiSend } from "react-icons/fi";
import { FaThermometerHalf, FaTint } from "react-icons/fa";
import type { BedData } from "../App";

interface BedCardProps {
  bed: BedData;
}

interface RiskScoreMessage {
  type?: "RISK_SCORE";
  node_id?: string;
  risk_score: number | string;
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

  const wsRef = useRef<WebSocket | null>(null);

  const updateGraph = (score: number) => {
    const safeScore = normalizeRiskScore(score);

    setRiskScore(safeScore);
    setHistory((prev) => [...prev.slice(1), safeScore]);
  };

  useEffect(() => {
    if (!activeNodeId) {
      console.warn(
        `[${bed.bed_id}] node_id가 없어 웹소켓을 연결하지 않습니다.`,
      );
      return;
    }

    const socket = new WebSocket(`ws://localhost:8000/ws/csi/${activeNodeId}`);
    wsRef.current = socket;

    socket.onopen = () => {
      console.log(`✅ [${bed.bed_id}] 소켓 연결 성공 (Node: ${activeNodeId})`);
      console.log(`연결 주소: ws://localhost:8000/ws/csi/${activeNodeId}`);
    };

    socket.onmessage = (event) => {
      try {
        console.log(`📩 [${activeNodeId}] 원본 메시지:`, event.data);

        const data: RiskScoreMessage = JSON.parse(event.data);

        if (data.type && data.type !== "RISK_SCORE") {
          console.warn("RISK_SCORE 메시지가 아닙니다:", data);
          return;
        }

        if (data.node_id && data.node_id !== activeNodeId) {
          console.warn(
            `현재 카드 node_id와 수신 node_id가 다릅니다. 카드=${activeNodeId}, 수신=${data.node_id}`,
          );
          return;
        }

        if (data.risk_score === undefined || data.risk_score === null) {
          console.warn("risk_score가 없는 메시지입니다:", data);
          return;
        }

        const newScore = Number(data.risk_score);

        if (Number.isNaN(newScore)) {
          console.warn("risk_score가 숫자가 아닙니다:", data.risk_score);
          return;
        }

        console.log(`📈 [${activeNodeId}] 그래프 업데이트:`, newScore);
        updateGraph(newScore);
      } catch (e) {
        console.error("데이터 파싱 에러:", e);
        console.error("문제가 된 원본 데이터:", event.data);
      }
    };

    socket.onerror = (error) => {
      console.error(`❌ [${activeNodeId}] 웹소켓 에러:`, error);
    };

    socket.onclose = (event) => {
      console.warn(
        `⚠️ [${activeNodeId}] 웹소켓 종료`,
        "code:",
        event.code,
        "reason:",
        event.reason,
      );
    };

    return () => {
      socket.close();
    };
  }, [activeNodeId, bed.bed_id]);

  const handleSendTestCSI = async () => {
    try {
      const fileRes = await fetch("/csi_test_packet_280bytes.bin");

      if (!fileRes.ok) {
        console.error("테스트 CSI 파일을 찾지 못했습니다.");
        alert(
          "public 폴더에 csi_test_packet_280bytes.bin 파일이 있는지 확인하세요.",
        );
        return;
      }

      const arrayBuffer = await fileRes.arrayBuffer();

      console.log(`🚀 [${bed.bed_id}] 백엔드로 데이터 전송 중...`);
      console.log("현재 카드 node_id:", activeNodeId);
      console.log("전송 파일 크기:", arrayBuffer.byteLength);

      const apiRes = await fetch("http://localhost:8000/csi/raw", {
        method: "POST",
        headers: { "Content-Type": "application/octet-stream" },
        body: arrayBuffer,
      });

      const resultText = await apiRes.text();

      if (!apiRes.ok) {
        console.error("CSI 전송 실패:", apiRes.status, resultText);
        alert(`CSI 전송 실패: ${apiRes.status}`);
        return;
      }

      console.log("✅ 백엔드 전송 성공:", resultText);
      console.log(
        "cnn_worker가 실행 중이면 곧 WebSocket으로 risk_score가 들어와야 합니다.",
      );
    } catch (err) {
      console.error("CSI 전송 중 오류:", err);
    }
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
            onClick={handleSendTestCSI}
            className="p-2 bg-gray-800 hover:bg-blue-600 rounded-lg transition-colors group"
            title="테스트 CSI 전송"
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
