import { useEffect, useState, Fragment } from "react";
import "./QCHistory.css";

type QCItem = {
  class: string;
  count: number;
  ratio: number;
};

type QCHistory = {
  id_qc: number;
  image_name: string;
  total_count: number;
  status: "PASS" | "FAIL";
  created_at: string;
  items: QCItem[];
};

export default function QCHistory() {
  const [history, setHistory] = useState<QCHistory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [openId, setOpenId] = useState<number | null>(null);

  const [range, setRange] = useState<"day" | "week" | "month"| "year">("day");
  const [date, setDate] = useState(
    new Date().toISOString().slice(0, 10)
  );

  // =========================
  // 🔹 โหลดข้อมูล (ทั้งหมด / ตาม filter)
  // =========================
  const fetchHistory = () => {
    setLoading(true);
    setError(null);

    let url = "http://127.0.0.1:8000/qc/history";

    // ✅ ถ้ามี filter ค่อยส่ง query
    if (range && date) {
      url += `?range=${range}&date=${date}`;
    }

    fetch(url)
      .then(res => {
        if (!res.ok) throw new Error("โหลดข้อมูลไม่สำเร็จ");
        return res.json();
      })
      .then(data => {
        setHistory(Array.isArray(data) ? data : []);
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  };

  // 🔹 โหลดครั้งแรก → ดึงทั้งหมด
  useEffect(() => {
    fetchHistory();
  }, []);

  // 🔹 เมื่อผู้ใช้เปลี่ยน range / date → filter
  useEffect(() => {
    fetchHistory();
  }, [range, date]);

  const formatThaiTime = (utc: string) =>
    new Date(utc).toLocaleString("en-GB", {
      timeZone: "UTC",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });

  if (loading) return <p>⏳ กำลังโหลดประวัติ QC...</p>;
  if (error) return <p style={{ color: "red" }}>❌ {error}</p>;

  return (
    <div className="qc-history">
      <h1>QC History</h1>

      {/* ===== Filter ===== */}
      <div className="qc-filter">
        <select
          value={range}
          onChange={e => setRange(e.target.value as any)}
        >
          <option value="day">รายวัน</option>
          <option value="week">รายสัปดาห์</option>
          <option value="month">รายเดือน</option>
          <option value="year">รายปี</option>
        </select>

        <input
          type="date"
          value={date}
          onChange={e => setDate(e.target.value)}
        />
      </div>

      {history.length === 0 ? (
        <p>ยังไม่มีข้อมูล QC</p>
      ) : (
        <table className="qc-table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Image</th>
              <th>Total count</th>
              <th>Status</th>
              <th>Detail</th>
            </tr>
          </thead>

          <tbody>
            {history.map(row => (
              <Fragment key={row.id_qc}>
                {/* ===== qc_result ===== */}
                <tr>
                  <td>{formatThaiTime(row.created_at)}</td>
                  <td>{row.image_name}</td>
                  <td>{row.total_count}</td>
                  {/* <td>{row.total_count.toFixed(2)}</td> */}
                  <td>
                    <span
                      className={`status ${
                        row.status === "PASS" ? "pass" : "fail"
                      }`}
                    >
                      {row.status}
                    </span>
                  </td>
                  <td>
                    <button
                      className="qc-toggle"
                      onClick={() =>
                        setOpenId(openId === row.id_qc ? null : row.id_qc)
                      }
                    >
                      {openId === row.id_qc ? "ซ่อน" : "ดูรายละเอียด"}
                    </button>
                  </td>
                </tr>

                {/* ===== qc_item ===== */}
                {openId === row.id_qc && (
                  <tr className="qc-item-row">
                    <td colSpan={5}>
                      <table className="qc-item-table">
                        <thead>
                          <tr>
                            <th>Class</th>
                            <th>count</th>
                            <th>Ratio (%)</th>
                          </tr>
                        </thead>
                        <tbody>
                          {row.items.length === 0 ? (
                            <tr>
                              <td colSpan={3}>ไม่มีข้อมูล item</td>
                            </tr>
                          ) : (
                            row.items.map((item, idx) => (
                              <tr key={idx}>
                                <td>{item.class}</td>
                                {/* <td>{item.count.toFixed(2)}</td> */}
                                <td>{item.count}</td>
                                <td>{item.ratio.toFixed(2)}%</td>
                                {/* <td>{(item.ratio * 100).toFixed(1)}</td> */}
                              </tr>
                            ))
                          )}
                        </tbody>
                      </table>
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
