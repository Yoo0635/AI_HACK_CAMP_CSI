import { useState, useEffect, useRef } from "react";
import Header from "./components/Header";
import Sidebar from "./components/Sidebar";
import BedCard from "./components/BedCard";
import StatsOverview from "./components/StatsOverview";

export interface BedData {
  bed_id: string;
  nickname: string;
  age: number;
  node_id?: string;
}

// 웹소켓 알림 데이터 타입 정의
export interface AlertWsMessage {
  id?: string;
  type?: string;
  bed_id?: string;
  nickname?: string;
  risk_score?: number;
  sllm_summary?: string;
}

const INITIAL_BEDS: BedData[] = [
  { bed_id: "BED-101", nickname: "김환자", age: 65, node_id: "node_001" },
  { bed_id: "BED-102", nickname: "이환자", age: 72, node_id: "node_002" },
  { bed_id: "BED-103", nickname: "박환자", age: 58, node_id: "node_003" },
  { bed_id: "BED-104", nickname: "최환자", age: 81, node_id: "node_004" },
];

function App() {
  const [lastUpdated, setLastUpdated] = useState<string>(
    new Date().toLocaleTimeString(),
  );
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);

  const [beds, setBeds] = useState<BedData[]>(INITIAL_BEDS);

  // 실시간 알림 상태 및 웹소켓 Ref
  const [alerts, setAlerts] = useState<AlertWsMessage[]>([]);
  const wsRef = useRef<WebSocket | null>(null);

  const [newBed, setNewBed] = useState<BedData>({
    bed_id: "",
    nickname: "",
    age: 0,
    node_id: "",
  });

  // 실시간 데이터 기반 통계 수치 동기화
  const totalBeds = beds.length;
  const warningCount = alerts.length; // 들어온 알림 개수만큼 위험 카운트 증가
  const normalCount = Math.max(0, totalBeds - warningCount);

  // 웹소켓 연결 및 이벤트 리스너 설정 (컴포넌트 마운트 시 실행)
  useEffect(() => {
    const connectWebSocket = () => {
      // 백엔드 웹소켓 주소 (환경에 맞게 포트/경로 수정 필요)
      const wsUrl = "ws://localhost:8000/ws/alerts";
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log("🟢 [웹소켓] 대시보드 알림 서버 연결 성공");
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log("📩 [웹소켓 수신]:", data);

          // 위험 알림(ALERT)인 경우 화면에 표시할 alerts 배열에 추가
          if (data.type === "ALERT" || data.risk_score >= 0.7) {
            setAlerts((prev) => [
              { ...data, id: Date.now().toString() }, // 고유 ID 부여
              ...prev,
            ]);
          }
        } catch (error) {
          console.error("웹소켓 메시지 파싱 오류:", error);
        }
      };

      ws.onclose = () => {
        console.warn("🔴 [웹소켓] 연결 끊김. 3초 후 재연결 시도...");
        setTimeout(connectWebSocket, 3000);
      };

      ws.onerror = (error) => {
        console.error("웹소켓 에러 발생:", error);
        ws.close();
      };
    };

    connectWebSocket();

    // 컴포넌트 언마운트 시 웹소켓 연결 해제
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  // 수신된 알림 닫기 함수
  const handleCloseAlert = (alertId: string) => {
    setAlerts((prev) => prev.filter((alert) => alert.id !== alertId));
  };

  const handleFetchBeds = () => {
    setIsRefreshing(true);
    setTimeout(() => {
      setIsRefreshing(false);
      setLastUpdated(new Date().toLocaleTimeString());
    }, 1000);
  };

  const handleAddBedSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setBeds([...beds, newBed]);
    setIsModalOpen(false);
    setNewBed({ bed_id: "", nickname: "", age: 0, node_id: "" });
  };

  return (
    <div className="flex h-screen bg-[#0B0E14] text-white font-sans overflow-hidden relative">
      <Sidebar />

      <div className="flex-1 flex flex-col h-full overflow-y-auto p-8 relative">
        <Header
          lastUpdated={lastUpdated}
          isRefreshing={isRefreshing}
          onFetchBeds={handleFetchBeds}
          onAddBed={() => setIsModalOpen(true)}
        />

        <StatsOverview
          totalBeds={totalBeds}
          normalCount={normalCount}
          warningCount={warningCount}
        />

        <main className="flex-1">
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 gap-6">
            {beds.map((bed, index) => (
              <BedCard key={`${bed.bed_id}-${index}`} bed={bed} />
            ))}
          </div>
        </main>
      </div>

      {/* 웹소켓 알림(Toast) UI 영역 */}
      <div className="fixed top-24 right-8 z-50 flex flex-col gap-3 w-80">
        {alerts.map((alert) => (
          <div
            key={alert.id}
            className="bg-red-950/90 border border-red-500 rounded-xl p-4 shadow-[0_0_20px_rgba(239,68,68,0.3)] animate-fadeIn flex flex-col gap-2"
          >
            <div className="flex justify-between items-start">
              <h3 className="text-red-400 font-bold flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-red-500 animate-ping" />
                🚨 위험 감지: {alert.bed_id || "알 수 없음"}
              </h3>
              <button
                onClick={() => handleCloseAlert(alert.id!)}
                className="text-gray-400 hover:text-white transition"
              >
                ✕
              </button>
            </div>
            <p className="text-sm text-gray-200">
              {alert.sllm_summary || "환자의 이상 행동이 감지되었습니다."}
            </p>
          </div>
        ))}
      </div>

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
                    노드 ID (선택)
                  </label>
                  <input
                    type="text"
                    value={newBed.node_id}
                    onChange={(e) =>
                      setNewBed({ ...newBed, node_id: e.target.value })
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
