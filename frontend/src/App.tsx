import { useState } from "react";
import Header from "./components/Header";
import Sidebar from "./components/Sidebar";
import BedCard from "./components/BedCard";
import StatsOverview from "./components/StatsOverview";

// BedCard에서 사용할 데이터 타입 정의
export interface BedData {
  bed_id: string;
  nickname: string;
  age: number;
  node_id?: string;
}

// UI 테스트를 위한 가짜 병상 데이터 리스트
const MOCK_BEDS: BedData[] = [
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

  // 통계 수치 테스트용 데이터 세팅
  const totalBeds = MOCK_BEDS.length;
  const warningCount = 1; // UI 테스트를 위해 위험 감지 건수를 1로 설정
  const normalCount = totalBeds - warningCount;

  // 새로고침 동작 테스트
  const handleFetchBeds = () => {
    setIsRefreshing(true);
    console.log("🔄 [테스트] 백엔드 데이터 새로고침 요청됨");

    setTimeout(() => {
      setIsRefreshing(false);
      setLastUpdated(new Date().toLocaleTimeString());
    }, 1000);
  };

  // 침대 추가 동작 테스트
  const handleAddBed = () => {
    console.log("➕ [테스트] 침대 추가 모달 열기 요청됨");
    setIsModalOpen(true);
  };

  return (
    // 전체 화면을 Flex로 좌우 분할
    <div className="flex h-screen bg-[#0B0E14] text-white font-sans overflow-hidden">
      <Sidebar />

      <div className="flex-1 flex flex-col h-full overflow-y-auto p-8">
        <Header
          lastUpdated={lastUpdated}
          isRefreshing={isRefreshing}
          onFetchBeds={handleFetchBeds}
          onAddBed={handleAddBed}
        />

        {/* 헤더와 메인 병상 리스트 사이에 StatsOverview 배치 */}
        <StatsOverview
          totalBeds={totalBeds}
          normalCount={normalCount}
          warningCount={warningCount}
        />

        <main className="flex-1">
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 gap-6">
            {MOCK_BEDS.map((bed) => (
              <BedCard key={bed.bed_id} bed={bed} />
            ))}
          </div>
        </main>
      </div>

      {isModalOpen && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4 animate-fadeIn">
          <div className="bg-[#151821] border border-gray-700 rounded-2xl w-full max-w-md p-6 shadow-2xl">
            <h2 className="text-xl font-bold mb-4 text-green-400">
              신규 병상 등록
            </h2>
            <p className="text-gray-400 text-sm mb-6">침대 등록 구현 미완성</p>
            <button
              onClick={() => setIsModalOpen(false)}
              className="w-full px-4 py-2 bg-green-500 text-black font-bold rounded-lg hover:bg-green-400 transition"
            >
              닫기
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
