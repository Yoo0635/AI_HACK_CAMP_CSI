import { useState, useEffect, useCallback, useRef } from "react";
import { FiX } from "react-icons/fi";
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

interface RawBedData {
  id?: number;
  bed_id?: string;
  bedId?: string;
  node_id?: string;
  nodeId?: string;
  nodeID?: string;
  nickname?: string;
  age?: number | string;
  disease?: string;
}

interface BedsApiResponse {
  beds?: RawBedData[];
}

interface AlertWsMessage {
  type?: string;
  bed_id?: string;
  nickname?: string;
  label?: string;
  cnn_timestamp?: number | string;
  sllm_summary?: string;
  risk_score?: number | string;
}

interface FullAlertWsMessage extends AlertWsMessage {
  bed_id: string;
  nickname: string;
  label: string;
  cnn_timestamp: number | string;
  risk_score: number | string;
}

interface DangerLogEntry {
  id: number;
  bed_id: string;
  nickname: string;
  label: string;
  risk_score: number;
  cnn_timestamp: string;
  logged_at: string;
  sllm_summary: string;
  nursing_note: string;
}

type LogModalMode = "admin" | "nursing";

function isBedsApiResponse(data: unknown): data is BedsApiResponse {
  return typeof data === "object" && data !== null && "beds" in data;
}

function isFullAlertMessage(data: AlertWsMessage): data is FullAlertWsMessage {
  return (
    typeof data.bed_id === "string" &&
    data.bed_id.length > 0 &&
    typeof data.nickname === "string" &&
    data.nickname.length > 0 &&
    typeof data.label === "string" &&
    data.label.length > 0 &&
    data.cnn_timestamp !== undefined &&
    data.cnn_timestamp !== null &&
    data.risk_score !== undefined &&
    data.risk_score !== null
  );
}

const ALERT_THRESHOLD = 80;
const ALERT_HISTORY_SIZE = 10;
const ADMIN_PASSWORD = "admin";

function normalizeRiskScore(score: number) {
  return Math.max(0, score);
}

function formatSignalTime(timestamp?: number | string) {
  if (timestamp === undefined || timestamp === null || timestamp === "") {
    return new Date().toLocaleTimeString();
  }

  const numericTimestamp = Number(timestamp);

  if (Number.isNaN(numericTimestamp)) {
    return String(timestamp);
  }

  const timestampMs =
    numericTimestamp < 10_000_000_000
      ? numericTimestamp * 1000
      : numericTimestamp;

  return new Date(timestampMs).toLocaleTimeString();
}

function App() {
  const [beds, setBeds] = useState<BedData[]>([]);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<string>("업데이트 전");

  const [isModalOpen, setIsModalOpen] = useState(false);

  const [newBed, setNewBed] = useState<BedData>({
    bed_id: "",
    node_id: "",
    nickname: "",
    age: 0,
    disease: "",
  });

  const [alertData, setAlertData] = useState<AlertData | null>(null);
  const [alertRiskHistory, setAlertRiskHistory] = useState<number[]>([]);
  const [dangerLogs, setDangerLogs] = useState<DangerLogEntry[]>([]);

  const [nursingNoteDrafts, setNursingNoteDrafts] = useState<
    Record<number, string>
  >({});

  const [isLogModalOpen, setIsLogModalOpen] = useState(false);
  const [logModalMode, setLogModalMode] = useState<LogModalMode>("admin");
  const [adminPassword, setAdminPassword] = useState("");
  const [isLogUnlocked, setIsLogUnlocked] = useState(false);
  const [passwordError, setPasswordError] = useState("");

  const lastAlertInfoRef = useRef<AlertData | null>(null);

  const pushAlertRiskScore = useCallback((score: number) => {
    const safeScore = normalizeRiskScore(score);

    setAlertRiskHistory((prev) => {
      const nextHistory = [...prev, safeScore];
      return nextHistory.slice(-ALERT_HISTORY_SIZE);
    });
  }, []);

  const saveDangerLog = useCallback(
    (riskScore: number, alertInfo: AlertData | null) => {
      if (!alertInfo) {
        console.warn("위험 로그를 저장할 상세 환자 정보가 없습니다.");
        return;
      }

      const safeScore = normalizeRiskScore(riskScore);

      if (safeScore < ALERT_THRESHOLD) {
        return;
      }

      const now = new Date();

      const newLog: DangerLogEntry = {
        id: now.getTime(),
        bed_id: alertInfo.bed_id,
        nickname: alertInfo.nickname,
        label: alertInfo.label,
        risk_score: safeScore,
        cnn_timestamp: alertInfo.cnn_timestamp,
        logged_at: now.toLocaleString(),
        sllm_summary: alertInfo.sllm_summary,
        nursing_note: "",
      };

      setDangerLogs((prev) => {
        const lastLog = prev[prev.length - 1];

        if (
          lastLog &&
          lastLog.bed_id === newLog.bed_id &&
          lastLog.risk_score === newLog.risk_score &&
          lastLog.cnn_timestamp === newLog.cnn_timestamp
        ) {
          return prev;
        }

        return [...prev, newLog];
      });
    },
    [],
  );

  const handleOpenLogModal = () => {
    setLogModalMode("admin");
    setIsLogModalOpen(true);
    setAdminPassword("");
    setIsLogUnlocked(false);
    setPasswordError("");
  };

  const handleOpenNursingJournal = () => {
    setLogModalMode("nursing");
    setIsLogModalOpen(true);
    setAdminPassword("");
    setIsLogUnlocked(true);
    setPasswordError("");
  };

  const handleCloseLogModal = () => {
    setIsLogModalOpen(false);
    setLogModalMode("admin");
    setAdminPassword("");
    setIsLogUnlocked(false);
    setPasswordError("");
  };

  const handleCheckAdminPassword = (e: React.FormEvent) => {
    e.preventDefault();

    if (adminPassword === ADMIN_PASSWORD) {
      setIsLogUnlocked(true);
      setPasswordError("");
      return;
    }

    setPasswordError("관리자 암호가 올바르지 않습니다.");
  };

  const handleClearDangerLogs = () => {
    const confirmed = window.confirm("저장된 위험 로그를 모두 삭제할까요?");

    if (!confirmed) {
      return;
    }

    setDangerLogs([]);
    setNursingNoteDrafts({});
  };

  const handleNursingNoteChange = (logId: number, value: string) => {
    setNursingNoteDrafts((prev) => ({
      ...prev,
      [logId]: value,
    }));
  };

  const handleSaveNursingNote = (logId: number) => {
    const note = nursingNoteDrafts[logId] ?? "";

    setDangerLogs((prev) =>
      prev.map((log) =>
        log.id === logId
          ? {
              ...log,
              nursing_note: note,
            }
          : log,
      ),
    );

    alert("간호내용이 저장되었습니다.");
  };

  useEffect(() => {
    const alertWs = new WebSocket(`ws://${window.location.host}/ws/alert`);

    alertWs.onopen = () => {
      console.log("🚨 전체 알람 웹소켓 연결됨!");
    };

    alertWs.onmessage = (event) => {
      try {
        console.log("🚨 알람 원본 메시지:", event.data);

        const data = JSON.parse(event.data) as AlertWsMessage;
        console.log("🚨 알람 파싱 결과:", data);

        if (data.risk_score === undefined || data.risk_score === null) {
          console.warn("알림 메시지에 risk_score가 없습니다:", data);
          return;
        }

        const riskScore = Number(data.risk_score);

        if (Number.isNaN(riskScore)) {
          console.warn("알림 risk_score가 숫자가 아닙니다:", data.risk_score);
          return;
        }

        const signalTime = formatSignalTime(data.cnn_timestamp);

        pushAlertRiskScore(riskScore);

        const safeRiskScore = normalizeRiskScore(riskScore);
        const isDanger = safeRiskScore >= ALERT_THRESHOLD;

        if (isFullAlertMessage(data)) {
          const fullAlertData: AlertData = {
            bed_id: data.bed_id,
            nickname: data.nickname,
            label: data.label,
            cnn_timestamp: signalTime,
            sllm_summary:
              data.sllm_summary && data.sllm_summary !== "none"
                ? data.sllm_summary
                : "위험 상황이 감지되었습니다.",
            risk_score: safeRiskScore,
          };

          lastAlertInfoRef.current = fullAlertData;

          if (!isDanger) {
            return;
          }

          saveDangerLog(safeRiskScore, fullAlertData);
          setAlertData(fullAlertData);
          return;
        }

        setAlertData((prev) => {
          const storedAlertInfo = lastAlertInfoRef.current;

          const updatedAlertInfo = storedAlertInfo
            ? {
                ...storedAlertInfo,
                risk_score: safeRiskScore,
                cnn_timestamp: signalTime,
              }
            : null;

          if (updatedAlertInfo) {
            lastAlertInfoRef.current = updatedAlertInfo;
          }

          if (isDanger) {
            saveDangerLog(safeRiskScore, prev ?? updatedAlertInfo);
          }

          if (prev) {
            if (!isDanger) {
              return null;
            }

            return {
              ...prev,
              risk_score: safeRiskScore,
              cnn_timestamp: signalTime,
            };
          }

          if (!isDanger) {
            return null;
          }

          return updatedAlertInfo;
        });
      } catch (e) {
        console.error("알람 데이터 파싱 에러:", e);
        console.error("문제가 된 원본 데이터:", event.data);
      }
    };

    alertWs.onerror = (error) => {
      console.error("❌ 전체 알람 웹소켓 에러:", error);
    };

    alertWs.onclose = (event) => {
      console.warn(
        "⚠️ 전체 알람 웹소켓 연결 종료",
        "code:",
        event.code,
        "reason:",
        event.reason,
      );
    };

    return () => {
      alertWs.close();
    };
  }, [pushAlertRiskScore, saveDangerLog]);

  const fetchBeds = useCallback(async () => {
    setIsRefreshing(true);

    try {
      const response = await fetch("/api/beds");

      if (response.ok) {
        const data: unknown = await response.json();

        const rawBedList: RawBedData[] = Array.isArray(data)
          ? data
          : isBedsApiResponse(data)
            ? (data.beds ?? [])
            : [];

        const normalizedBeds: BedData[] = rawBedList.map((bed) => ({
          id: bed.id,
          bed_id: bed.bed_id ?? bed.bedId ?? "",
          node_id: bed.node_id ?? bed.nodeId ?? bed.nodeID ?? "",
          nickname: bed.nickname ?? "",
          age: Number(bed.age ?? 0),
          disease: bed.disease ?? "",
        }));

        setBeds(normalizedBeds);
        setLastUpdated(new Date().toLocaleTimeString());
      } else {
        console.warn(
          "목록을 불러오는 데 실패했습니다. 상태 코드:",
          response.status,
        );
      }
    } catch (error) {
      console.error("데이터 로드 실패:", error);
    } finally {
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void fetchBeds();
    }, 0);

    return () => {
      window.clearTimeout(timer);
    };
  }, [fetchBeds]);

  const handleAddBedSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const requestBody: BedData = {
      ...newBed,
      bed_id: newBed.bed_id.trim(),
      node_id: newBed.node_id.trim(),
      nickname: newBed.nickname.trim(),
      age: Number(newBed.age) || 0,
      disease: newBed.disease.trim(),
    };

    if (!requestBody.bed_id) {
      alert("병상 번호를 입력해주세요.");
      return;
    }

    if (!requestBody.node_id) {
      alert("노드 ID를 입력해주세요. 예: NODE01");
      return;
    }

    if (!requestBody.nickname) {
      alert("환자명을 입력해주세요.");
      return;
    }

    try {
      const response = await fetch("/api/beds", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestBody),
      });

      if (response.ok) {
        alert("🎉 성공적으로 등록되었습니다!");

        setIsModalOpen(false);

        setNewBed({
          bed_id: "",
          node_id: "",
          nickname: "",
          age: 0,
          disease: "",
        });

        await fetchBeds();
      } else {
        alert(`❌ 등록 실패! 상태 코드: ${response.status}`);
      }
    } catch (error) {
      console.error("침대 등록 중 에러:", error);
      alert("❌ 서버와 연결할 수 없습니다!");
    }
  };

  return (
    <div className="flex min-h-screen bg-[#0B0E14] text-white font-sans relative">
      {alertData && (
        <AlertPopup
          data={alertData}
          riskHistory={alertRiskHistory}
          historySize={ALERT_HISTORY_SIZE}
          onClose={() => setAlertData(null)}
        />
      )}

      {isLogModalOpen && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-[60] p-4">
          <div className="bg-[#151821] border border-gray-700 rounded-2xl w-full max-w-6xl p-6 shadow-2xl relative">
            <button
              onClick={handleCloseLogModal}
              className="absolute top-4 right-4 text-gray-400 hover:text-white transition"
            >
              <FiX size={24} />
            </button>

            <h2 className="text-xl font-bold mb-2">
              {logModalMode === "nursing" ? "간호 일지" : "위험 로그 조회"}
            </h2>

            <p className="text-sm text-gray-400 mb-6">
              {logModalMode === "nursing"
                ? "Risk Score 0.7 이상 발생 시각, 환자 이름, LLM 결과값, 간호내용을 기록합니다."
                : "관리자만 열람 가능합니다."}
            </p>

            {!isLogUnlocked ? (
              <form onSubmit={handleCheckAdminPassword} className="space-y-4">
                <div>
                  <label className="block text-xs text-gray-500 mb-1">
                    관리자 암호를 입력하세요
                  </label>
                  <input
                    type="password"
                    value={adminPassword}
                    onChange={(e) => setAdminPassword(e.target.value)}
                    placeholder="암호를 입력하세요"
                    className="w-full bg-[#0B0E14] border border-gray-700 rounded-lg px-4 py-3 focus:border-red-500 outline-none"
                    autoFocus
                  />
                </div>

                {passwordError && (
                  <p className="text-sm text-red-400">{passwordError}</p>
                )}

                <button
                  type="submit"
                  className="w-full px-4 py-3 bg-red-500 text-white font-bold rounded-lg hover:bg-red-400 transition"
                >
                  로그 확인하기
                </button>
              </form>
            ) : (
              <div>
                <div className="flex items-center justify-between mb-4">
                  <p className="text-sm text-gray-400">
                    저장된 위험 로그:{" "}
                    <span className="text-red-400 font-bold">
                      {dangerLogs.length}건
                    </span>
                  </p>

                  {logModalMode === "admin" && (
                    <button
                      onClick={handleClearDangerLogs}
                      className="px-3 py-2 bg-gray-800 text-gray-300 text-sm rounded-lg hover:bg-red-500 hover:text-white transition"
                    >
                      로그 전체 삭제
                    </button>
                  )}
                </div>

                {dangerLogs.length === 0 ? (
                  <div className="border border-dashed border-gray-700 rounded-xl py-12 text-center text-gray-500">
                    아직 저장된 위험 로그가 없습니다.
                  </div>
                ) : (
                  <div className="max-h-[480px] overflow-y-auto overflow-x-auto rounded-xl border border-gray-700">
                    <table
                      className={`w-full table-fixed text-sm ${
                        logModalMode === "nursing"
                          ? "min-w-[1100px]"
                          : "min-w-[760px]"
                      }`}
                    >
                      <thead className="sticky top-0 bg-[#0B0E14] text-gray-400">
                        <tr>
                          <th className="w-[130px] text-left px-4 py-3">
                            전송 시간
                          </th>
                          <th className="w-[90px] text-left px-4 py-3">병상</th>
                          <th className="w-[100px] text-left px-4 py-3">
                            환자 이름
                          </th>
                          <th className="w-[80px] text-left px-4 py-3">Risk</th>
                          <th className="w-[260px] text-left px-4 py-3">
                            LLM 결과값
                          </th>

                          {logModalMode === "nursing" && (
                            <>
                              <th className="w-[360px] text-left px-4 py-3">
                                간호내용
                              </th>
                              <th className="w-[90px] text-left px-4 py-3">
                                저장
                              </th>
                            </>
                          )}
                        </tr>
                      </thead>

                      <tbody>
                        {[...dangerLogs].reverse().map((log) => {
                          const draftValue =
                            nursingNoteDrafts[log.id] ?? log.nursing_note;

                          return (
                            <tr
                              key={log.id}
                              className="border-t border-gray-800 hover:bg-gray-800/40 align-top"
                            >
                              <td className="px-4 py-3 text-gray-300">
                                {log.cnn_timestamp}
                              </td>

                              <td className="px-4 py-3 font-bold text-white">
                                {log.bed_id}
                              </td>

                              <td className="px-4 py-3 text-gray-300">
                                {log.nickname}
                              </td>

                              <td className="px-4 py-3 font-black text-red-400">
                                {log.risk_score.toFixed(2)}
                              </td>

                              <td className="px-4 py-3 text-gray-300 break-keep">
                                {log.sllm_summary || "LLM 결과값 없음"}
                              </td>

                              {logModalMode === "nursing" && (
                                <>
                                  <td className="px-4 py-3">
                                    <textarea
                                      value={draftValue}
                                      onChange={(e) =>
                                        handleNursingNoteChange(
                                          log.id,
                                          e.target.value,
                                        )
                                      }
                                      placeholder="간호내용을 입력하세요."
                                      className="w-full min-h-[80px] resize-y bg-[#0B0E14] border border-gray-700 rounded-lg px-3 py-2 text-gray-200 focus:border-green-500 outline-none"
                                    />
                                    {log.nursing_note && (
                                      <p className="text-[11px] text-green-400 mt-1">
                                        저장된 내용 있음
                                      </p>
                                    )}
                                  </td>

                                  <td className="px-4 py-3">
                                    <button
                                      type="button"
                                      onClick={() =>
                                        handleSaveNursingNote(log.id)
                                      }
                                      className="px-3 py-2 bg-green-500 text-black text-xs font-bold rounded-lg hover:bg-green-400 transition"
                                    >
                                      저장
                                    </button>
                                  </td>
                                </>
                              )}
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      <Sidebar
        onOpenLogs={handleOpenLogModal}
        onOpenNursingJournal={handleOpenNursingJournal}
        logCount={dangerLogs.length}
      />

      <div className="flex-1 flex flex-col overflow-hidden">
        <Header
          lastUpdated={lastUpdated}
          isRefreshing={isRefreshing}
          onFetchBeds={fetchBeds}
          onAddBed={() => setIsModalOpen(true)}
        />

        <main className="flex-1 p-8 overflow-y-auto">
          <StatsOverview
            totalBeds={beds.length}
            normalCount={alertData ? Math.max(beds.length - 1, 0) : beds.length}
            warningCount={alertData ? 1 : 0}
          />

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {beds.length > 0 ? (
              beds.map((bed, index) => (
                <BedCard
                  key={bed.id ?? bed.node_id ?? bed.bed_id ?? index}
                  bed={bed}
                />
              ))
            ) : (
              <div className="col-span-full text-center py-20 text-gray-500 border-2 border-dashed border-gray-800 rounded-xl">
                등록된 병상이 없습니다. 상단 '+ 침대 추가' 버튼을 눌러주세요.
              </div>
            )}
          </div>
        </main>
      </div>

      {isModalOpen && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="bg-[#151821] border border-gray-700 rounded-2xl w-full max-w-md p-6 shadow-2xl">
            <h2 className="text-xl font-bold mb-6">신규 병상 등록</h2>

            <form onSubmit={handleAddBedSubmit} className="space-y-4">
              <div>
                <label className="block text-xs text-gray-500 mb-1">
                  병상 번호
                </label>
                <input
                  value={newBed.bed_id}
                  className="w-full bg-[#0B0E14] border border-gray-700 rounded-lg px-4 py-2 focus:border-green-500 outline-none"
                  onChange={(e) =>
                    setNewBed({ ...newBed, bed_id: e.target.value })
                  }
                  required
                />
              </div>

              <div>
                <label className="block text-xs text-gray-500 mb-1">
                  노드 ID
                </label>
                <input
                  value={newBed.node_id}
                  placeholder="NODE01"
                  className="w-full bg-[#0B0E14] border border-gray-700 rounded-lg px-4 py-2 focus:border-green-500 outline-none"
                  onChange={(e) =>
                    setNewBed({ ...newBed, node_id: e.target.value })
                  }
                  required
                />
              </div>

              <div>
                <label className="block text-xs text-gray-500 mb-1">
                  환자명
                </label>
                <input
                  value={newBed.nickname}
                  className="w-full bg-[#0B0E14] border border-gray-700 rounded-lg px-4 py-2 focus:border-green-500 outline-none"
                  onChange={(e) =>
                    setNewBed({ ...newBed, nickname: e.target.value })
                  }
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <input
                  type="number"
                  value={newBed.age || ""}
                  placeholder="나이"
                  className="w-full bg-[#0B0E14] border border-gray-700 rounded-lg px-4 py-2 focus:border-green-500 outline-none"
                  onChange={(e) =>
                    setNewBed({
                      ...newBed,
                      age: parseInt(e.target.value) || 0,
                    })
                  }
                />

                <input
                  value={newBed.disease}
                  placeholder="질환명"
                  className="w-full bg-[#0B0E14] border border-gray-700 rounded-lg px-4 py-2 focus:border-green-500 outline-none"
                  onChange={(e) =>
                    setNewBed({ ...newBed, disease: e.target.value })
                  }
                />
              </div>

              <div className="flex gap-3 mt-8">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="flex-1 px-4 py-2 bg-gray-800 rounded-lg font-bold hover:bg-gray-700 transition"
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
