import {
  FiGrid,
  FiActivity,
  FiClipboard,
  FiFileText,
  FiPlus,
  FiSettings,
  FiLock,
} from "react-icons/fi";
import { FaPills } from "react-icons/fa";

interface SidebarProps {
  onOpenLogs: () => void;
  onOpenNursingJournal: () => void;
  logCount: number;
}

const Sidebar = ({
  onOpenLogs,
  onOpenNursingJournal,
  logCount,
}: SidebarProps) => {
  return (
    <aside className="w-64 bg-[#0B0E14] border-r border-gray-800 flex flex-col h-screen sticky top-0 shrink-0">
      <div className="p-6 border-b border-gray-800 flex items-center gap-3">
        <div className="w-8 h-8 bg-green-500/20 text-green-400 rounded-lg flex items-center justify-center">
          <FiPlus size={18} />
        </div>
        <div>
          <h1 className="font-bold text-sm">서울중앙병원</h1>
          <p className="text-xs text-gray-500">간호 모니터링 시스템</p>
        </div>
      </div>

      <div className="p-6 border-b border-gray-800 flex items-center gap-3">
        <div className="w-10 h-10 bg-gray-700 rounded-full flex items-center justify-center font-bold text-white">
          DR
        </div>
        <div>
          <h2 className="font-bold text-sm">김의사</h2>
          <p className="text-xs text-green-400">당직 전문의</p>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto py-6">
        <ul className="space-y-2 px-3">
          <li>
            <a
              href="#"
              className="flex items-center gap-3 px-3 py-3 bg-green-500/10 text-green-400 rounded-xl font-bold"
            >
              <FiGrid size={18} />
              <span className="text-sm">대시보드</span>
            </a>
          </li>

          <li>
            <a
              href="#"
              className="flex items-center gap-3 px-3 py-3 text-gray-400 hover:text-white hover:bg-gray-800/50 rounded-xl transition"
            >
              <FiClipboard size={18} />
              <span className="text-sm">진료 기록</span>
            </a>
          </li>

          <li>
            <a
              href="#"
              className="flex items-center gap-3 px-3 py-3 text-gray-400 hover:text-white hover:bg-gray-800/50 rounded-xl transition"
            >
              <FaPills size={18} />
              <span className="text-sm flex-1">투약 관리</span>
              <span className="w-5 h-5 bg-red-500 text-white text-[10px] flex items-center justify-center rounded-full font-bold">
                5
              </span>
            </a>
          </li>

          <li>
            <button
              type="button"
              onClick={onOpenNursingJournal}
              className="w-full flex items-center gap-3 px-3 py-3 text-gray-400 hover:text-white hover:bg-gray-800/50 rounded-xl transition"
            >
              <FiFileText size={18} />
              <span className="text-sm flex-1 text-left">간호 일지</span>

              {logCount > 0 && (
                <span className="min-w-5 h-5 px-1 bg-red-500 text-white text-[10px] flex items-center justify-center rounded-full font-bold">
                  {logCount}
                </span>
              )}
            </button>
          </li>

          <li>
            <a
              href="#"
              className="flex items-center gap-3 px-3 py-3 text-gray-400 hover:text-white hover:bg-gray-800/50 rounded-xl transition"
            >
              <FiActivity size={18} />
              <span className="text-sm">센서 관리</span>
            </a>
          </li>

          <li>
            <a
              href="#"
              className="flex items-center gap-3 px-3 py-3 text-gray-400 hover:text-white hover:bg-gray-800/50 rounded-xl transition"
            >
              <FiSettings size={18} />
              <span className="text-sm">환경설정</span>
            </a>
          </li>
        </ul>
      </div>

      <div className="p-3 border-t border-gray-800">
        <button
          type="button"
          onClick={onOpenLogs}
          className="w-full flex items-center gap-3 px-3 py-3 text-gray-300 hover:text-white hover:bg-red-500/10 border border-gray-800 hover:border-red-500/50 rounded-xl transition"
        >
          <FiLock size={18} className="text-red-400" />
          <span className="text-sm flex-1 text-left">로그 내보내기</span>

          {logCount > 0 && (
            <span className="min-w-5 h-5 px-1 bg-red-500 text-white text-[10px] flex items-center justify-center rounded-full font-bold">
              {logCount}
            </span>
          )}
        </button>
      </div>
    </aside>
  );
};

export default Sidebar;
