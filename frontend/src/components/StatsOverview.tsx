interface StatsProps {
  totalBeds: number;
  normalCount: number;
  warningCount: number;
}

const StatsOverview = ({
  totalBeds,
  normalCount,
  warningCount,
}: StatsProps) => {
  return (
    <div className="flex space-x-4 mb-8">
      <div className="bg-[#151821] border border-gray-700 rounded-lg px-6 py-3 flex items-center justify-between min-w-[160px]">
        <span className="text-gray-400 text-sm">등록 병상 수</span>
        <span className="text-xl font-bold">{totalBeds}개</span>
      </div>

      <div className="bg-[#151821] border border-gray-700 rounded-lg px-6 py-3 flex items-center justify-between min-w-[160px]">
        <div className="flex items-center">
          <span className="w-2 h-2 bg-green-500 rounded-full mr-2"></span>
          <span className="text-gray-400 text-sm">정상 수신</span>
        </div>
        <span className="text-xl font-bold text-green-500">
          {normalCount}개
        </span>
      </div>

      <div className="bg-[#151821] border border-gray-700 rounded-lg px-6 py-3 flex items-center justify-between min-w-[160px]">
        <div className="flex items-center">
          <span className="w-2 h-2 bg-red-500 rounded-full mr-2 animate-pulse"></span>
          <span className="text-gray-400 text-sm">위험 감지</span>
        </div>
        <span className="text-xl font-bold text-red-500">{warningCount}건</span>
      </div>
    </div>
  );
};

export default StatsOverview;
