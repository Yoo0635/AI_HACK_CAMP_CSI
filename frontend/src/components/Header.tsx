import { FiRefreshCw, FiSearch } from "react-icons/fi";

interface HeaderProps {
  lastUpdated: string;
  isRefreshing: boolean;
  onFetchBeds: () => void;
  onAddBed: () => void;
}

const Header = ({
  lastUpdated,
  isRefreshing,
  onFetchBeds,
  onAddBed,
}: HeaderProps) => {
  return (
    <header className="flex justify-between items-center mb-8 bg-[#0B0E14] pt-4 px-4">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">
          환자 모니터링 대시보드
        </h1>
        <p className="text-gray-400 text-sm mt-1">
          실시간 이상 행동 감지 시스템
        </p>
      </div>

      <div className="flex items-center space-x-4">
        <div className="relative">
          <FiSearch className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-500" />
          <input
            type="text"
            placeholder="환자 검색..."
            className="bg-[#151821] border border-gray-700 text-sm rounded-full pl-10 pr-4 py-2 focus:outline-none focus:border-green-500 transition"
          />
        </div>

        <div className="flex items-center space-x-2 text-sm text-green-400 bg-[#151821] px-4 py-2 rounded-full border border-gray-700">
          <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
          <span>최근 업데이트: {lastUpdated}</span>
        </div>

        <div className="flex gap-2">
          <button
            onClick={onAddBed}
            className="px-4 py-2 bg-green-500 text-black rounded hover:bg-green-400 transition font-bold"
          >
            + 침대 추가
          </button>
        </div>

        <button
          onClick={onFetchBeds}
          className={`p-2 bg-[#151821] rounded-full border border-gray-700 hover:bg-gray-700 transition ${isRefreshing ? "animate-spin" : ""}`}
        >
          <FiRefreshCw className="text-gray-300" />
        </button>
      </div>
    </header>
  );
};

export default Header;
