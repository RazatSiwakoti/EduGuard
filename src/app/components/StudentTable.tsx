import { Download, ExternalLink, ChevronUp, ChevronDown, TrendingUp, TrendingDown, Minus } from "lucide-react";
import { useState, useMemo } from "react";
import { riskConfig, type RiskLevel } from "../data/studentData"; //removed Allstudents import as it is no longer used, now using students from api
import type { StudentOverview } from "../api/students"; //added Student import to use the Student type in the StudentTable component
export type { RiskLevel, StudentOverview };

const barColorMap: Record<RiskLevel, string> = {
  HIGH: "#E24B4A",
  MEDIUM: "#EF9F27",
  LOW: "#97C459",
};

function MiniBar({ value, max, risk }: { value: number; max: number; risk: RiskLevel }) {
  return (
    <div style={{ height: "5px", background: "#F3F4F6", borderRadius: "3px", overflow: "hidden", width: "72px" }}>
      <div style={{ height: "100%", width: `${Math.min((value / max) * 100, 100)}%`, background: barColorMap[risk], borderRadius: "3px" }} />
    </div>
  );
}

function TrendIcon({ trend,
}: {
  trend: StudentOverview["trend"];
}) { //changed trend prop type to use StudentOverview type instead of RiskLevel
  if (trend === "improving") return <TrendingUp size={13} color="#16A34A" />;
  if (trend === "deteriorating") return <TrendingDown size={13} color="#DC2626" />;
  return <Minus size={13} color="#9CA3AF" />;
}

type SortKey = "name" | "attendance" | "gpa"  | "mlScore";
type SortDir = "asc" | "desc";

const PAGE_SIZE = 8;

interface StudentTableProps {
  students?: StudentOverview[]; //added student array prop to StudentTableProps to pass the students data from StudentsPage
  searchQuery: string;
  riskFilter: string;
  subjectFilter?: string;
  onViewStudent: (studentId: number) => void;
}

export function StudentTable({ students = [], searchQuery, riskFilter, subjectFilter, onViewStudent }: StudentTableProps) {  //added student array prop to StudentTableProps to pass the students data from StudentsPage
  const [sortKey, setSortKey] = useState<SortKey>("attendance");
  const [sortDir, setSortDir] = useState<SortDir>("asc");
  const [page, setPage] = useState(1);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
    setPage(1);
  };

  const filtered = useMemo(() => {
    let list = [...(students ?? [])];//changed from allStudents to students to use the data fetched from the API 
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      list = list.filter(
        (s) =>
          s.name.toLowerCase().includes(q) ||
          (s.subject ?? "").toLowerCase().includes(q) || //added nullish coalescing operator to handle cases where subject is undefined
          s.studentId.toLowerCase().includes(q)
          // s.program.toLowerCase().includes(q) removed program filter as it is no longer needed
      );
    }
    if (riskFilter !== "All") {
      list = list.filter((s) => s.risk === riskFilter);
    }
    if (subjectFilter && subjectFilter !== "All") {
      list = list.filter((s) => s.subject === subjectFilter);
    }
  //   list.sort((a, b) => {
  //     let av: number, bv: number;
  //     if (sortKey === "name") { av = a.name.charCodeAt(0); bv = b.name.charCodeAt(0); }
  //     else if (sortKey === "attendance") { av = a.attendance; bv = b.attendance; }
  //     else if (sortKey === "gpa") { av = a.gpa; bv = b.gpa; }
  //     else if (sortKey === "mlScore") { av = a.mlScore; bv = b.mlScore; }
  //     else { av = a.mlScore; bv = b.mlScore; } //changed assignemnt to MLScore for now, as it is the only remaining sortable column, and to avoid TypeScript error
  //     return sortDir === "asc" ? av - bv : bv - av;
  //   });
  //   return list;
  // }, [searchQuery, riskFilter, subjectFilter, sortKey, sortDir]);

  //temp? sort list?
  list.sort((a, b) => {
  let av: number;
  let bv: number;

  if (sortKey === "name") {
    av = a.name.charCodeAt(0);
    bv = b.name.charCodeAt(0);
  } else if (sortKey === "attendance") {
    av = a.attendance;
    bv = b.attendance;
  } else if (sortKey === "gpa") {
    av = a.gpa;
    bv = b.gpa;
  } else {
    av = a.mlScore;
    bv = b.mlScore;
  }

  return sortDir === "asc" ? av - bv : bv - av;
});return list;
  }, [students, searchQuery, riskFilter, subjectFilter, sortKey, sortDir]);

  const handleExportCSV = () => {
    const headers = ["Name", "Student ID", "Subject",  "Attendance %", "GPA", "Risk", "Trend", "ML Score", "Confidence"]; //removed Program header as it is no longer needed so is assignments is is work in progress
    const rows = filtered.map((s) => [
      s.name, s.studentId, s.subject ?? "", s.attendance, s.gpa,//removed nullish coalescing operator to handle cases where subject is undefined
       s.risk, s.trend,//`${s.assignments.done}/${s.assignments.total}`, removed for now as assignments is still in progress, and to avoid confusion with the other columns
      s.mlScore.toFixed(2), `${s.confidence}%`,
    ]);
    const csv = [headers, ...rows].map((r) => r.join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "edguard_student_risk_report.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const paginated = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  const SortIcon = ({ col }: { col: SortKey }) => (
    <span style={{ display: "inline-flex", flexDirection: "column", marginLeft: "3px", opacity: sortKey === col ? 1 : 0.3 }}>
      <ChevronUp size={8} color={sortKey === col && sortDir === "asc" ? "#185FA5" : "#6B7280"} style={{ marginBottom: "-2px" }} />
      <ChevronDown size={8} color={sortKey === col && sortDir === "desc" ? "#185FA5" : "#6B7280"} />
    </span>
  );

  const columns: { label: string; sortKey?: SortKey }[] = [
    { label: "Student", sortKey: "name" },
    { label: "Attendance", sortKey: "attendance" },
    { label: "GPA", sortKey: "gpa" },
    { label: "Assignments" },//removed sortKey for assignments as it is still in progress
    { label: "ML Score", sortKey: "mlScore" },
    { label: "Risk Level" },
    { label: "Trend" },
    { label: "Action" },
  ];

  return (
    <div style={{ background: "#FFFFFF", borderRadius: "12px", boxShadow: "0 1px 4px rgba(0,0,0,0.08)", overflow: "hidden", display: "flex", flexDirection: "column" }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "18px 20px", borderBottom: "1px solid #F3F4F6" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <h2 style={{ color: "#1A1A2E", fontSize: "15px", fontWeight: "600", margin: 0 }}>Student Overview</h2>
          <span style={{ background: "#EBF4FF", color: "#185FA5", fontSize: "11px", fontWeight: "600", padding: "2px 8px", borderRadius: "999px" }}>
            {filtered.length} {filtered.length === 1 ? "student" : "students"}
          </span>
        </div>
        <button
          onClick={handleExportCSV}
          style={{ display: "flex", alignItems: "center", gap: "6px", padding: "7px 14px", background: "#185FA5", border: "none", borderRadius: "8px", cursor: "pointer" }}
          onMouseEnter={(e) => ((e.currentTarget as HTMLButtonElement).style.background = "#1250A0")}
          onMouseLeave={(e) => ((e.currentTarget as HTMLButtonElement).style.background = "#185FA5")}
        >
          <Download size={13} color="#FFFFFF" />
          <span style={{ color: "#FFFFFF", fontSize: "12px", fontWeight: "600" }}>Export CSV</span>
        </button>
      </div>

      {/* Table */}
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ background: "#F9FAFB" }}>
              {columns.map((col) => (
                <th
                  key={col.label}
                  onClick={() => col.sortKey && handleSort(col.sortKey)}
                  style={{
                    padding: "11px 16px",
                    textAlign: "left",
                    color: col.sortKey && sortKey === col.sortKey ? "#185FA5" : "#6B7280",
                    fontSize: "11px",
                    fontWeight: "600",
                    letterSpacing: "0.05em",
                    textTransform: "uppercase",
                    borderBottom: "1px solid #E5E7EB",
                    whiteSpace: "nowrap",
                    cursor: col.sortKey ? "pointer" : "default",
                    userSelect: "none",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center" }}>
                    {col.label}
                    {col.sortKey && <SortIcon col={col.sortKey} />}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {paginated.length === 0 ? (
              <tr>
                <td colSpan={8} style={{ padding: "40px 16px", textAlign: "center", color: "#9CA3AF", fontSize: "13px" }}>
                  No students match your filters.
                </td>
              </tr>
            ) : (
              paginated.map((student, idx) => {
                const config = riskConfig[student.risk];
                const isEven = idx % 2 === 0;
                return (
                  <tr
                    key={student.id}
                    style={{ background: isEven ? "#FFFFFF" : "#F9FAFB", transition: "background 0.1s" }}
                    onMouseEnter={(e) => ((e.currentTarget as HTMLTableRowElement).style.background = "#EBF4FF")}
                    onMouseLeave={(e) => ((e.currentTarget as HTMLTableRowElement).style.background = isEven ? "#FFFFFF" : "#F9FAFB")}
                  >
                    {/* Student */}
                    <td style={{ padding: "12px 16px", borderBottom: "1px solid #F3F4F6" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                        <div style={{ width: "32px", height: "32px", borderRadius: "50%", background: config.bg, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                          <span style={{ color: config.color, fontSize: "11px", fontWeight: "700" }}>{student.initials}</span>
                        </div>
                        <div>
                          <div style={{ color: "#1A1A2E", fontSize: "13px", fontWeight: "600" }}>{student.name}</div>
                          <div style={{ color: "#9CA3AF", fontSize: "10px" }}>{student.studentId} · {student.subject}</div>
                        </div>
                      </div>
                    </td>

                    {/* Attendance */}
                    <td style={{ padding: "12px 16px", borderBottom: "1px solid #F3F4F6" }}>
                      <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                        <span style={{ color: student.attendance < 50 ? "#E24B4A" : "#1A1A2E", fontSize: "13px", fontWeight: "500" }}>
                          {student.attendance}%
                          {student.attendance < 50 && <span style={{ fontSize: "10px", marginLeft: "3px" }}>⚠</span>}
                        </span>
                        <MiniBar value={student.attendance} max={100} risk={student.risk} />
                      </div>
                    </td>

                    {/* GPA */}
                    <td style={{ padding: "12px 16px", borderBottom: "1px solid #F3F4F6" }}>
                      <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                        <span style={{ color: student.gpa < 2.0 ? "#E24B4A" : "#1A1A2E", fontSize: "13px", fontWeight: "500" }}>
                          {student.gpa.toFixed(1)}
                        </span>
                        <MiniBar value={student.gpa} max={4} risk={student.risk} />
                      </div>
                    </td>

                    {/* Assignments old*/}
                    {/* <td style={{ padding: "12px 16px", borderBottom: "1px solid #F3F4F6" }}>
                      <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                        <span style={{ color: "#1A1A2E", fontSize: "13px", fontWeight: "500" }}>
                          {student.assignments.done}/{student.assignments.total}
                        </span>
                        <MiniBar value={student.assignments.done} max={student.assignments.total} risk={student.risk} />
                      </div>
                    </td> */}

                      {/* Assignments */}
                    <td style={{ padding: "12px 16px", borderBottom: "1px solid #F3F4F6" }}>
                      <span
                      title="Assessment integration not connected yet"
                      style={{
                        color: "#9CA3AF",
                        fontSize: "13px",
                        fontWeight: "600",
                      }}
                          >
                            ??
                          </span>
                        </td>

                    {/* ML Score */}
                    <td style={{ padding: "12px 16px", borderBottom: "1px solid #F3F4F6" }}>
                      <div style={{ display: "flex", flexDirection: "column", gap: "3px" }}>
                        <span style={{ color: config.color, fontSize: "13px", fontWeight: "700" }}>
                          {student.mlScore.toFixed(2)}
                        </span>
                        <span style={{ color: "#9CA3AF", fontSize: "10px" }}>{student.confidence}% conf.</span>
                      </div>
                    </td>

                    {/* Risk badge */}
                    <td style={{ padding: "12px 16px", borderBottom: "1px solid #F3F4F6" }}>
                      <span style={{ display: "inline-flex", alignItems: "center", gap: "4px", padding: "3px 10px", borderRadius: "999px", background: config.bg, color: config.color, fontSize: "11px", fontWeight: "700", letterSpacing: "0.04em" }}>
                        <span style={{ width: "5px", height: "5px", borderRadius: "50%", background: config.color }} />
                        {config.label}
                      </span>
                    </td>

                    {/* Trend */}
                    <td style={{ padding: "12px 16px", borderBottom: "1px solid #F3F4F6" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                        <TrendIcon trend={student.trend} />
                        <span style={{ fontSize: "11px", color: student.trend === "improving" ? "#16A34A" : student.trend === "deteriorating" ? "#DC2626" : "#9CA3AF", textTransform: "capitalize" }}>
                          {student.trend}
                        </span>
                      </div>
                    </td>

                    {/* Action */}
                    <td style={{ padding: "12px 16px", borderBottom: "1px solid #F3F4F6" }}>
                      <button
                        onClick={() => onViewStudent(student.id)}
                        style={{ display: "flex", alignItems: "center", gap: "5px", padding: "5px 12px", background: "transparent", border: "1.5px solid #E5E7EB", borderRadius: "7px", cursor: "pointer", color: "#185FA5", fontSize: "12px", fontWeight: "600", whiteSpace: "nowrap", transition: "all 0.15s" }}
                        //style={{display: "flex", alignItems: "center", gap: "5px", padding: "5px 12px", background: "#F3F4F6", border: "1.5px solid #E5E7EB", borderRadius: "7px", cursor: "not-allowed", color: "#9CA3AF", fontSize: "12px", fontWeight: "600", whiteSpace: "nowrap",}}
                        onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.borderColor = "#185FA5"; (e.currentTarget as HTMLButtonElement).style.background = "#EBF4FF"; }}
                       // onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.borderColor = "#E5E7EB"; (e.currentTarget as HTMLButtonElement).style.background = "transparent"; }}
                      >
                        <ExternalLink size={11} color="#185FA5" />
                        
                        View
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination footer */}
      <div style={{ padding: "12px 20px", display: "flex", alignItems: "center", justifyContent: "space-between", borderTop: "1px solid #F3F4F6" }}>
        <span style={{ color: "#9CA3AF", fontSize: "12px" }}>
          Showing {filtered.length === 0 ? 0 : Math.min((page - 1) * PAGE_SIZE + 1, filtered.length)}–{Math.min(page * PAGE_SIZE, filtered.length)} of {filtered.length} students
        </span>
        <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            style={{ padding: "4px 10px", borderRadius: "6px", border: "1.5px solid #E5E7EB", background: "transparent", color: page === 1 ? "#D1D5DB" : "#6B7280", fontSize: "12px", cursor: page === 1 ? "not-allowed" : "pointer" }}
          >
            ‹ Prev
          </button>
          {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
            <button
              key={p}
              onClick={() => setPage(p)}
              style={{ width: "28px", height: "28px", borderRadius: "6px", border: p === page ? "1.5px solid #185FA5" : "1.5px solid #E5E7EB", background: p === page ? "#185FA5" : "transparent", color: p === page ? "#FFFFFF" : "#6B7280", fontSize: "12px", fontWeight: "500", cursor: "pointer" }}
            >
              {p}
            </button>
          ))}
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            style={{ padding: "4px 10px", borderRadius: "6px", border: "1.5px solid #E5E7EB", background: "transparent", color: page === totalPages ? "#D1D5DB" : "#6B7280", fontSize: "12px", cursor: page === totalPages ? "not-allowed" : "pointer" }}
          >
            Next ›
          </button>
        </div>
      </div>
    </div>
  );
}
