import { useState, useEffect, useCallback, useRef } from "react";
import Sidebar from "./components/Sidebar";
import Header from "./components/Header";
import StatsOverview from "./components/StatsOverview";
import BedCard from "./components/BedCard";
import AlertPopup, { type AlertData } from "./components/AlertPopup";

export interface BedData {
  id?: number;
  bed_id: string;
  node_id: string;
  nickname: string;
  age: number;
  disease: string;
}

function App() {
  const [lastUpdated, setLastUpdated] = useState<string>(
    new Date().toLocaleTimeString(),
  );
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);

  // 백엔드에서 불러올 병상 리스트 관리 (초기 임시 데이터 완전 제거)
  const [beds, setBeds] = useState<BedData[]>([]);

  // 🌟 AlertPopup 및 실시간 그래프 데이터 스트림 상태 관리
  const [activeAlert, setActiveAlert] = useState<AlertData | null>(null);
  const [alertLogs, setAlertLogs] = useState<AlertData[]>([]);
  const [nodeHistories, setNodeHistories] = useState<Record<string, number[]>>(
    {},
  );

  const wsRef = useRef<WebSocket | null>(null);
  const HISTORY_SIZE = 20; // 그래프에 표기할 데이터 유지 개수

  const [newBed, setNewBed] = useState<BedData>({
    bed_id: "",
    node_id: "",
    nickname: "",
    age: 0,
    disease: "",
  });

  // 실시간 통계 수치 동기화
  const totalBeds = beds.length;
  const warningCount = alertLogs.length; // 누적 위험 알림 수 (Sidebar 배지 연동)
  const normalCount = Math.max(0, totalBeds - (activeAlert ? 1 : 0));

  // 백엔드 API로부터 병상 데이터 가져오기 (Fetch)
  const fetchBeds = useCallback(async () => {
    setIsRefreshing(true);
    try {
      const response = await fetch("http://localhost:8000/api/beds");
      if (!response.ok) {
        throw new Error("병상 데이터를 가져오는데 실패했습니다.");
      }
      const data = await response.json();

      const bedsArray = Array.isArray(data) ? data : data.beds || [];

      const formattedBeds = bedsArray.map((b: any) => ({
        id: b.id,
        bed_id: b.bed_id || b.bedId || "",
        node_id: b.node_id || b.nodeId || b.nodeID || "",
        nickname: b.nickname || "",
        age: Number(b.age) || 0,
        disease: b.disease || "",
      }));

      setBeds(formattedBeds);
      setLastUpdated(new Date().toLocaleTimeString());
    } catch (error) {
      console.error("❌ 병상 로딩 에러:", error);
    } finally {
      setIsRefreshing(false);
    }
  }, []);

  // 컴포넌트 마운트 시 데이터 패치 및 웹소켓 연결
  useEffect(() => {
    fetchBeds();

    const connectWebSocket = () => {
      const wsUrl = "ws://localhost:8000/ws/alerts";
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log("🟢 [웹소켓] 대시보드 실시간 알림 채널 연결 성공");
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log("📩 [웹소켓 수신]:", data);

          const bedId = data.bed_id || "";
          const score =
            typeof data.risk_score === "number"
              ? data.risk_score
              : parseFloat(data.risk_score) || 0;

          // 1. 🌟 해당 병상(노드)의 실시간 그래프 이력 누적 업데이트
          if (bedId) {
            setNodeHistories((prev) => {
              const currentHistory = prev[bedId] || Array(HISTORY_SIZE).fill(0);
              const updatedHistory = [...currentHistory.slice(1), score];
              return {
                ...prev,
                [bedId]: updatedHistory,
              };
            });
          }

          // 2. 🌟 위험 상황 조건 충족 시 AlertPopup 생성 트리거
          if (data.type === "ALERT" || score >= 0.7) {
            const newAlert: AlertData = {
              bed_id: bedId,
              nickname: data.nickname || "환자",
              label: data.label || "이상 행동 감지",
              cnn_timestamp: data.cnn_timestamp
                ? String(data.cnn_timestamp)
                : new Date().toLocaleTimeString(),
              sllm_summary:
                data.sllm_summary ||
                "환자의 위험 실시간 행동 요소가 식별되었습니다.",
              risk_score: score,
            };

            // 전체 알림 내역 로그에 추가
            setAlertLogs((prev) => [newAlert, ...prev]);
            // 현재 화면에 띄울 최신 팝업 활성화
            setActiveAlert(newAlert);
          }
        } catch (error) {
          console.error("웹소켓 메시지 파싱 오류:", error);
        }
      };

      ws.onclose = () => {
        console.warn("🔴 [웹소켓] 연결 종료. 3초 후 재연결을 시도합니다...");
        setTimeout(connectWebSocket, 3000);
      };

      ws.onerror = (error) => {
        console.error("웹소켓 에러 발생:", error);
        ws.close();
      };
    };

    connectWebSocket();

    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, [fetchBeds]);

  // 신규 병상 등록 처리
  const handleAddBedSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const response = await fetch("http://localhost:8000/api/beds", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newBed),
      });

      if (!response.ok) {
        throw new Error("병상 등록 실패");
      }

      setIsModalOpen(false);
      setNewBed({ bed_id: "", node_id: "", nickname: "", age: 0, disease: "" });
      fetchBeds();
    } catch (error) {
      console.error("❌ 병상 등록 에러:", error);
      alert("병상 등록 처리 중 오류가 발생했습니다.");
    }
  };

  return (
    <div className="flex h-screen bg-[#0B0E14] text-white font-sans overflow-hidden relative">
      {/* 🌟 Sidebar 컴포넌트 필수 Props 데이터 매핑 (간호 일지 배지 카운트 연동) */}
      <Sidebar
        onOpenLogs={() => console.log("간호 일지 로그 보기 열기")}
        logCount={warningCount}
      />

      <div className="flex-1 flex flex-col h-full overflow-y-auto p-8 relative">
        <Header
          lastUpdated={lastUpdated}
          isRefreshing={isRefreshing}
          onFetchBeds={fetchBeds}
          onAddBed={() => setIsModalOpen(true)}
        />

        <StatsOverview
          totalBeds={totalBeds}
          normalCount={normalCount}
          warningCount={warningCount}
        />

        <main className="flex-1">
          {beds.length === 0 ? (
            <div className="text-center py-20 text-gray-500 border border-dashed border-gray-800 rounded-2xl">
              등록된 병상이 존재하지 않습니다. 우측 상단 버튼을 통해 침대를
              추가해 주세요.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 gap-6">
              {beds.map((bed, index) => (
                <BedCard key={`${bed.bed_id}-${index}`} bed={bed} />
              ))}
            </div>
          )}
        </main>
      </div>

      {/* 🌟 실시간 위험 알림 대형 팝업 (AlertPopup) 연동 완료 */}
      {activeAlert && (
        <AlertPopup
          data={activeAlert}
          riskHistory={
            nodeHistories[activeAlert.bed_id] ||
            Array(HISTORY_SIZE).fill(activeAlert.risk_score)
          }
          historySize={HISTORY_SIZE}
          onClose={() => setActiveAlert(null)}
        />
      )}

      {/* 신규 병상 등록 모달 */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4 animate-fadeIn">
          <div className="bg-[#151821] border border-gray-700 rounded-2xl w-full max-w-md p-6 shadow-2xl">
            <h2 className="text-xl font-bold mb-6 text-white">
              🛏️ 신규 병상 등록
            </h2>
            <form onSubmit={handleAddBedSubmit} className="space-y-4">
              <div>
                <label className="block text-xs text-gray-400 mb-1">
                  병상 번호 (예: BED-105)
                </label>
                <input
                  type="text"
                  required
                  value={newBed.bed_id}
                  onChange={(e) =>
                    setNewBed({ ...newBed, bed_id: e.target.value })
                  }
                  className="w-full bg-[#0B0E14] border border-gray-700 rounded-lg px-4 py-2 text-white focus:border-green-500 outline-none transition"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">
                  노드 ID (예: node_001)
                </label>
                <input
                  type="text"
                  required
                  value={newBed.node_id}
                  onChange={(e) =>
                    setNewBed({ ...newBed, node_id: e.target.value })
                  }
                  className="w-full bg-[#0B0E14] border border-gray-700 rounded-lg px-4 py-2 text-white focus:border-green-500 outline-none transition"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">
                  환자 닉네임
                </label>
                <input
                  type="text"
                  required
                  value={newBed.nickname}
                  onChange={(e) =>
                    setNewBed({ ...newBed, nickname: e.target.value })
                  }
                  className="w-full bg-[#0B0E14] border border-gray-700 rounded-lg px-4 py-2 text-white focus:border-green-500 outline-none transition"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs text-gray-400 mb-1">
                    나이
                  </label>
                  <input
                    type="number"
                    required
                    min="0"
                    value={newBed.age || ""}
                    onChange={(e) =>
                      setNewBed({ ...newBed, age: Number(e.target.value) })
                    }
                    className="w-full bg-[#0B0E14] border border-gray-700 rounded-lg px-4 py-2 text-white focus:border-green-500 outline-none transition"
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-400 mb-1">
                    질환명
                  </label>
                  <input
                    type="text"
                    required
                    value={newBed.disease}
                    onChange={(e) =>
                      setNewBed({ ...newBed, disease: e.target.value })
                    }
                    className="w-full bg-[#0B0E14] border border-gray-700 rounded-lg px-4 py-2 text-white focus:border-green-500 outline-none transition"
                  />
                </div>
              </div>
              <div className="flex gap-3 mt-8 pt-4">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="flex-1 px-4 py-2 bg-gray-800 text-white rounded-lg font-bold hover:bg-gray-700 transition"
                >
                  취소
                </button>
                <button
                  type="submit"
                  className="flex-1 px-4 py-2 bg-green-500 text-black font-bold rounded-lg hover:bg-green-400 transition"
                >
                  등록하기
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
