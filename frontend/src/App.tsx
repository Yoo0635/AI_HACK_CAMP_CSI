import { useState } from "react";
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

// 초기 데이터
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

  // 병상 리스트를 State로 관리하여 추가/삭제가 화면에 즉각 반영되도록 변경
  const [beds, setBeds] = useState<BedData[]>(INITIAL_BEDS);

  // 🌟 신규 병상 등록 폼의 입력값을 관리하는 State
  const [newBed, setNewBed] = useState<BedData>({
    bed_id: "",
    nickname: "",
    age: 0,
    node_id: "",
  });

  // 통계 수치 동기화
  const totalBeds = beds.length;
  const warningCount = 1;
  const normalCount = totalBeds - warningCount;

  const handleFetchBeds = () => {
    setIsRefreshing(true);
    setTimeout(() => {
      setIsRefreshing(false);
      setLastUpdated(new Date().toLocaleTimeString());
    }, 1000);
  };

  // 폼 제출 시 실행되는 함수: 새로운 병상을 배열에 추가하고 모달을 닫음
  const handleAddBedSubmit = (e: React.FormEvent) => {
    e.preventDefault(); // 페이지 새로고침 방지

    setBeds([...beds, newBed]); // 기존 배열에 새 데이터 추가
    setIsModalOpen(false); // 모달 닫기

    // 폼 초기화
    setNewBed({
      bed_id: "",
      nickname: "",
      age: 0,
      node_id: "",
    });
  };

  return (
    <div className="flex h-screen bg-[#0B0E14] text-white font-sans overflow-hidden">
      <Sidebar />

      <div className="flex-1 flex flex-col h-full overflow-y-auto p-8">
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

      {/* 병상 등록 폼 모달 */}
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
