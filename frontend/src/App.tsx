import { useState } from "react";
import Header from "./components/Header";

function App() {
  const [lastUpdated, setLastUpdated] = useState<string>(
    new Date().toLocaleTimeString(),
  );
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);

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
    <div className="min-h-screen bg-[#0B0E14] text-white p-8 font-sans">
      <Header
        lastUpdated={lastUpdated}
        isRefreshing={isRefreshing}
        onFetchBeds={handleFetchBeds}
        onAddBed={handleAddBed}
      />

      <main className="mt-8 border-2 border-dashed border-gray-800 rounded-xl p-20 text-center text-gray-500">
        <p className="text-lg font-medium text-gray-400">
          여기에 다음 단계에서 개발할 병상 카드(BedCard) 리스트가 배치될
          예정입니다.
        </p>
        <p className="text-sm mt-2 text-gray-600">
          상단의 새로고침 회전 버튼과 '+ 침대 추가' 버튼이 활성화되는지 먼저
          확인해 보세요.
        </p>
      </main>

      {/* 침대 추가 버튼 누르면 뜨는 임시 모달 창 (정상 작동 확인용) */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4 animate-fadeIn">
          <div className="bg-[#151821] border border-gray-700 rounded-2xl w-full max-w-md p-6 shadow-2xl">
            <h2 className="text-xl font-bold mb-4 text-green-400">
              🛏️ 신규 병상 등록 모달 트리거 완료
            </h2>
            <p className="text-gray-400 text-sm mb-6">
              Header 컴포넌트의 버튼 이벤트가 부모 컴포넌트(App.tsx)의 State를
              정상적으로 변조시켜 모달을 띄웠습니다! 테일윈드 v4 스타일도 아주
              깔끔하게 적용되네요.
            </p>
            <button
              onClick={() => setIsModalOpen(false)}
              className="w-full px-4 py-2 bg-green-500 text-black font-bold rounded-lg hover:bg-green-400 transition"
            >
              인터랙션 확인 완료 및 닫기
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
