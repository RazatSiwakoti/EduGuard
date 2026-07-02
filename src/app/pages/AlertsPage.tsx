import { useState } from "react";
import { toast } from "sonner";
import { AlertTriangle, Mail, CheckCircle, XCircle, Clock, RefreshCw, Filter, Search } from "lucide-react";
import { emailLogs, allStudents, riskConfig } from "../data/studentData";
import { useTheme } from "../context/ThemeContext";

const statusConfig = {
  Opened: { color: "#16A34A", bg: "#ECFDF5", icon: <CheckCircle size={12} color="#16A34A" /> },
  Sent: { color: "#185FA5", bg: "#EBF4FF", icon: <Mail size={12} color="#185FA5" /> },
  Failed: { color: "#E24B4A", bg: "#FEE2E2", icon: <XCircle size={12} color="#E24B4A" /> },
};

const alertQueue = allStudents.filter((s) => s.risk === "HIGH" || s.risk === "MEDIUM").slice(0, 8);

export default function AlertsPage() {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("All");
  const [isSending, setIsSending] = useState(false);
  const { isDark } = useTheme();
  const textPrimary = isDark ? "#F1F5F9" : "#1A1A2E";
  const textSecondary = isDark ? "#94A3B8" : "#6B7280";

  const filteredLogs = emailLogs.filter((log) => {
    const matchSearch = log.student.toLowerCase().includes(search.toLowerCase()) || log.subject.toLowerCase().includes(search.toLowerCase());
    const matchStatus = statusFilter === "All" || log.status === statusFilter;
    return matchSearch && matchStatus;
  });

  const handleBulkSend = async () => {
    setIsSending(true);
    toast.loading("Dispatching bulk SMTP alerts…", { id: "bulk" });
    await new Promise((r) => setTimeout(r, 2000));
    setIsSending(false);
    toast.success("Bulk alerts dispatched", {
      id: "bulk",
      description: `${alertQueue.filter((s) => s.risk === "HIGH").length} high-risk + ${alertQueue.filter((s) => s.risk === "MEDIUM").length} medium-risk emails sent via EdGuard SMTP.`,
      duration: 5000,
    });
  };

  const statCounts = {
    total: emailLogs.length,
    opened: emailLogs.filter((l) => l.status === "Opened").length,
    sent: emailLogs.filter((l) => l.status === "Sent").length,
    failed: emailLogs.filter((l) => l.status === "Failed").length,
  };

  return (
    <div style={{ animation: "fadeInUp 0.25s ease" }}>
      {/* Header */}
      <div style={{ marginBottom: "20px", display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "4px" }}>
            <AlertTriangle size={20} color="#E24B4A" />
            <h1 style={{ color: textPrimary, fontSize: "22px", fontWeight: "800", margin: 0, letterSpacing: "-0.02em" }}>
              Alerts & Email Notifications
            </h1>
          </div>
          <p style={{ color: textSecondary, fontSize: "13px", margin: 0 }}>
            SMTP notification log · Semester 1 2025 · {emailLogs.length} emails sent this term
          </p>
        </div>
        <button
          onClick={handleBulkSend}
          disabled={isSending}
          style={{
            display: "flex", alignItems: "center", gap: "7px", padding: "9px 18px",
            background: isSending ? "#7AAED4" : "linear-gradient(135deg, #185FA5, #1A7ABF)",
            border: "none", borderRadius: "9px", color: "#FFFFFF", fontSize: "13px",
            fontWeight: "700", cursor: isSending ? "not-allowed" : "pointer",
            boxShadow: isSending ? "none" : "0 2px 8px rgba(24,95,165,0.35)",
          }}
        >
          {isSending
            ? <RefreshCw size={13} color="#FFFFFF" style={{ animation: "spin 0.8s linear infinite" }} />
            : <Mail size={13} color="#FFFFFF" />
          }
          {isSending ? "Sending…" : "Send Bulk Alerts"}
        </button>
      </div>

      {/* Stat cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "14px", marginBottom: "20px" }}>
        {[
          { label: "Total Sent", value: statCounts.total, color: "#185FA5", bg: "#EBF4FF", icon: <Mail size={18} color="#185FA5" /> },
          { label: "Opened", value: statCounts.opened, color: "#16A34A", bg: "#ECFDF5", icon: <CheckCircle size={18} color="#16A34A" /> },
          { label: "Awaiting Read", value: statCounts.sent, color: "#D97706", bg: "#FEF3C7", icon: <Clock size={18} color="#D97706" /> },
          { label: "Failed", value: statCounts.failed, color: "#E24B4A", bg: "#FEE2E2", icon: <XCircle size={18} color="#E24B4A" /> },
        ].map((card) => (
          <div key={card.label} style={{ background: "#FFFFFF", borderRadius: "12px", padding: "16px 18px", boxShadow: "0 1px 4px rgba(0,0,0,0.07)", borderTop: `3px solid ${card.color}`, display: "flex", alignItems: "center", gap: "12px" }}>
            <div style={{ width: "40px", height: "40px", background: card.bg, borderRadius: "10px", display: "flex", alignItems: "center", justifyContent: "center" }}>
              {card.icon}
            </div>
            <div>
              <div style={{ fontSize: "24px", fontWeight: "800", color: card.color, lineHeight: "1" }}>{card.value}</div>
              <div style={{ fontSize: "12px", color: "#6B7280", marginTop: "2px" }}>{card.label}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Alert Queue */}
      <div style={{ background: "#FFFFFF", borderRadius: "12px", boxShadow: "0 1px 4px rgba(0,0,0,0.07)", marginBottom: "20px", overflow: "hidden" }}>
        <div style={{ padding: "16px 20px", borderBottom: "1px solid #F3F4F6", display: "flex", alignItems: "center", gap: "10px" }}>
          <AlertTriangle size={15} color="#E24B4A" />
          <h2 style={{ color: "#1A1A2E", fontSize: "14px", fontWeight: "700", margin: 0 }}>Pending Alert Queue</h2>
          <span style={{ background: "#FEE2E2", color: "#E24B4A", fontSize: "11px", fontWeight: "700", padding: "2px 8px", borderRadius: "999px" }}>
            {alertQueue.length} students
          </span>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
          {alertQueue.map((student, idx) => {
            const config = riskConfig[student.risk];
            return (
              <div key={student.id} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "12px 20px", background: idx % 2 === 0 ? "#FFFFFF" : "#F9FAFB", borderBottom: "1px solid #F3F4F6" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                  <div style={{ width: "34px", height: "34px", borderRadius: "50%", background: config.bg, display: "flex", alignItems: "center", justifyContent: "center" }}>
                    <span style={{ color: config.color, fontSize: "11px", fontWeight: "700" }}>{student.initials}</span>
                  </div>
                  <div>
                    <div style={{ color: "#1A1A2E", fontSize: "13px", fontWeight: "600" }}>{student.name}</div>
                    <div style={{ color: "#9CA3AF", fontSize: "11px" }}>{student.email} · {student.subject}</div>
                  </div>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                  <span style={{ display: "inline-flex", alignItems: "center", gap: "4px", padding: "3px 10px", borderRadius: "999px", background: config.bg, color: config.color, fontSize: "11px", fontWeight: "700" }}>
                    <span style={{ width: "5px", height: "5px", borderRadius: "50%", background: config.color }} />
                    {config.label}
                  </span>
                  <button
                    onClick={() => toast.success(`Alert sent to ${student.name}`, { description: `Email dispatched to ${student.email}`, duration: 3000 })}
                    style={{ display: "flex", alignItems: "center", gap: "5px", padding: "5px 12px", background: "#185FA5", border: "none", borderRadius: "7px", cursor: "pointer", color: "#FFFFFF", fontSize: "12px", fontWeight: "600" }}
                  >
                    <Mail size={11} color="#FFFFFF" />
                    Send Alert
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Email Log */}
      <div style={{ background: "#FFFFFF", borderRadius: "12px", boxShadow: "0 1px 4px rgba(0,0,0,0.07)", overflow: "hidden" }}>
        <div style={{ padding: "16px 20px", borderBottom: "1px solid #F3F4F6", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <Mail size={15} color="#185FA5" />
            <h2 style={{ color: "#1A1A2E", fontSize: "14px", fontWeight: "700", margin: 0 }}>Email Notification Log</h2>
            <span style={{ background: "#EBF4FF", color: "#185FA5", fontSize: "11px", fontWeight: "700", padding: "2px 8px", borderRadius: "999px" }}>
              {filteredLogs.length} records
            </span>
          </div>
          <div style={{ display: "flex", gap: "8px" }}>
            <div style={{ position: "relative" }}>
              <Search size={12} color="#9CA3AF" style={{ position: "absolute", left: "10px", top: "50%", transform: "translateY(-50%)" }} />
              <input
                type="text" placeholder="Search…" value={search}
                onChange={(e) => setSearch(e.target.value)}
                style={{ padding: "6px 10px 6px 28px", border: "1.5px solid #E5E7EB", borderRadius: "7px", fontSize: "12px", outline: "none", width: "180px" }}
              />
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
              <Filter size={12} color="#9CA3AF" />
              <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}
                style={{ padding: "6px 10px", border: "1.5px solid #E5E7EB", borderRadius: "7px", fontSize: "12px", outline: "none", cursor: "pointer" }}>
                {["All", "Opened", "Sent", "Failed"].map((s) => <option key={s}>{s}</option>)}
              </select>
            </div>
          </div>
        </div>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ background: "#F9FAFB" }}>
              {["Student", "Subject", "Email Type", "Template", "Status", "Sent At", "Opened At"].map((col) => (
                <th key={col} style={{ padding: "10px 16px", textAlign: "left", color: "#6B7280", fontSize: "11px", fontWeight: "600", letterSpacing: "0.05em", textTransform: "uppercase", borderBottom: "1px solid #E5E7EB", whiteSpace: "nowrap" }}>
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filteredLogs.map((log, idx) => {
              const sc = statusConfig[log.status as keyof typeof statusConfig];
              return (
                <tr key={log.id} style={{ background: idx % 2 === 0 ? "#FFFFFF" : "#F9FAFB" }}>
                  <td style={{ padding: "11px 16px", borderBottom: "1px solid #F3F4F6" }}>
                    <div style={{ color: "#1A1A2E", fontSize: "13px", fontWeight: "600" }}>{log.student}</div>
                    <div style={{ color: "#9CA3AF", fontSize: "10px" }}>{log.studentId}</div>
                  </td>
                  <td style={{ padding: "11px 16px", borderBottom: "1px solid #F3F4F6", color: "#6B7280", fontSize: "12px" }}>{log.subject}</td>
                  <td style={{ padding: "11px 16px", borderBottom: "1px solid #F3F4F6", color: "#374151", fontSize: "12px" }}>{log.type}</td>
                  <td style={{ padding: "11px 16px", borderBottom: "1px solid #F3F4F6" }}>
                    <code style={{ background: "#F3F4F6", color: "#6B7280", fontSize: "10px", padding: "2px 6px", borderRadius: "4px" }}>{log.template}</code>
                  </td>
                  <td style={{ padding: "11px 16px", borderBottom: "1px solid #F3F4F6" }}>
                    <span style={{ display: "inline-flex", alignItems: "center", gap: "4px", padding: "3px 9px", borderRadius: "999px", background: sc.bg, color: sc.color, fontSize: "11px", fontWeight: "600" }}>
                      {sc.icon} {log.status}
                    </span>
                  </td>
                  <td style={{ padding: "11px 16px", borderBottom: "1px solid #F3F4F6", color: "#6B7280", fontSize: "12px", whiteSpace: "nowrap" }}>{log.sentAt}</td>
                  <td style={{ padding: "11px 16px", borderBottom: "1px solid #F3F4F6", color: "#6B7280", fontSize: "12px", whiteSpace: "nowrap" }}>{log.openedAt}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <div style={{ height: "32px" }} />
    </div>
  );
}