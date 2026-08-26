import { useState, useEffect } from "react";
import { toast } from "sonner";
import { AlertTriangle, Mail, CheckCircle, XCircle, Clock, RefreshCw, Filter, Search, Loader, HelpCircle, ExternalLink, Download } from "lucide-react";
import { useTheme } from "../context/ThemeContext";
import { downloadCSV } from "../utils/csvExport";
import {
  fetchEmailLogs,
  fetchAlertQueue,
  fetchAlertStats,
  sendBulkAlerts,
  sendAlertToStudent,
  type EmailLog,
  type AlertStudent,
  type AlertStats,
} from "../api/alerts";

const statusConfig = {
  Acknowledged: { color: "#16A34A", bg: "#ECFDF5", label: "Acknowledged", icon: <CheckCircle size={12} color="#16A34A" /> },
  Opened: { color: "#16A34A", bg: "#ECFDF5", label: "Acknowledged", icon: <CheckCircle size={12} color="#16A34A" /> },
  Sent: { color: "#185FA5", bg: "#EBF4FF", label: "Awaiting Student Action", icon: <Clock size={12} color="#185FA5" /> },
  Pending: { color: "#6B7280", bg: "#F3F4F6", label: "Pending", icon: <Clock size={12} color="#6B7280" /> },
  Failed: { color: "#E24B4A", bg: "#FEE2E2", label: "Delivery Failed", icon: <XCircle size={12} color="#E24B4A" /> },
};

const riskConfig = {
  HIGH: { color: "#E24B4A", bg: "#FEE2E2", label: "High Risk" },
  MEDIUM: { color: "#D97706", bg: "#FEF3C7", label: "Medium Risk" },
  LOW: { color: "#16A34A", bg: "#ECFDF5", label: "Low Risk" },
};

function formatTimeAgo(dateStr?: string | null): string {
  if (!dateStr || dateStr === "—") return "—";
  try {
    const d = new Date(dateStr.replace(" ", "T"));
    if (isNaN(d.getTime())) return dateStr;
    const diffMs = Date.now() - d.getTime();
    if (diffMs < 0) return "Just now";
    const diffMins = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffDays > 0) {
      return `${diffDays}d ago`;
    } else if (diffHours > 0) {
      return `${diffHours}h ago`;
    } else if (diffMins > 0) {
      return `${diffMins}m ago`;
    } else {
      return "Just now";
    }
  } catch {
    return dateStr;
  }
}

export default function AlertsPage() {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("All");
  const [isSending, setIsSending] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  // Data states
  const [emailLogs, setEmailLogs] = useState<EmailLog[]>([]);
  const [alertQueue, setAlertQueue] = useState<AlertStudent[]>([]);
  const [stats, setStats] = useState<AlertStats>({ total: 0, acknowledged: 0, sent: 0, failed: 0 });

  const { isDark } = useTheme();
  const textPrimary = isDark ? "#F1F5F9" : "#1A1A2E";
  const textSecondary = isDark ? "#94A3B8" : "#6B7280";

  // Load data on mount
  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [logs, queue, alertStats] = await Promise.all([
        fetchEmailLogs(),
        fetchAlertQueue(),
        fetchAlertStats(),
      ]);

      setEmailLogs(logs);
      setAlertQueue(queue);
      setStats(alertStats);
    } catch (error) {
      console.error("Error loading alerts data:", error);
      toast.error("Failed to load alerts data");
    } finally {
      setIsLoading(false);
    }
  };

  const filteredLogs = emailLogs.filter((log) => {
    const matchSearch =
      log.student.toLowerCase().includes(search.toLowerCase()) ||
      (log.email && log.email.toLowerCase().includes(search.toLowerCase())) ||
      log.subject.toLowerCase().includes(search.toLowerCase()) ||
      (log.errorMessage && log.errorMessage.toLowerCase().includes(search.toLowerCase()));

    let matchStatus = true;
    if (statusFilter === "Acknowledged") {
      matchStatus = log.status === "Acknowledged" || log.status === "Opened";
    } else if (statusFilter === "Sent") {
      matchStatus = log.status === "Sent" || log.status === "Pending";
    } else if (statusFilter === "Failed") {
      matchStatus = log.status === "Failed";
    }

    return matchSearch && matchStatus;
  });

  const handleBulkSend = async () => {
    setIsSending(true);
    const toastId = "bulk-send";
    toast.loading("Dispatching bulk SMTP alerts…", { id: toastId });

    try {
      const result = await sendBulkAlerts(4); // Week 4

      if (result.success) {
        toast.success("Bulk alerts dispatched", {
          id: toastId,
          description: `${result.sent_count} emails sent. ${result.failed_count > 0 ? `${result.failed_count} failed delivery.` : ""}`,
          duration: 5000,
        });
        await loadData();
      } else {
        toast.error("Failed to send bulk alerts", {
          id: toastId,
          description: result.message,
          duration: 5000,
        });
      }
    } catch (error) {
      console.error("Error sending bulk alerts:", error);
      toast.error("Error sending bulk alerts", { id: toastId });
    } finally {
      setIsSending(false);
    }
  };

  const handleSendAlert = async (studentId: number, studentName: string, studentEmail: string) => {
    const toastId = `send-${studentId}`;
    toast.loading("Sending alert…", { id: toastId });

    try {
      const result = await sendAlertToStudent(studentId);

      if (result.success) {
        toast.success(`Alert sent to ${studentName}`, {
          id: toastId,
          description: `Dispatched to ${studentEmail}`,
          duration: 3000,
        });
        await loadData();
      } else {
        toast.error("Failed to send alert", {
          id: toastId,
          description: result.message,
          duration: 4000,
        });
        await loadData();
      }
    } catch (error) {
      console.error("Error sending alert:", error);
      toast.error("Error sending alert", { id: toastId });
    }
  };

  const handleExportCSV = () => {
    try {
      const headers = [
        "Log ID",
        "Student Name",
        "Student ID",
        "Recipient Email",
        "Subject / Course",
        "Notice Type",
        "Template",
        "Delivery Status",
        "Sent At (AEST)",
        "Acknowledged At (AEST)",
        "Error / Diagnostic Message",
      ];

      const rows = filteredLogs.map((l) => [
        l.id,
        l.student,
        l.studentId,
        l.email || "—",
        l.subject,
        l.type,
        l.template,
        l.status,
        l.sentAt,
        l.acknowledgedAt || l.openedAt || "—",
        l.errorMessage || "None",
      ]);

      downloadCSV("EduGuard_Email_Alerts_Log_2026", headers, rows);
      toast.success("Alert Logs Downloaded", {
        description: `Exported ${rows.length} notification records as CSV.`,
        duration: 3000,
      });
    } catch (error) {
      console.error("Error exporting CSV:", error);
      toast.error("Failed to export alert logs");
    }
  };

  if (isLoading) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "400px" }}>
        <Loader size={24} style={{ animation: "spin 0.8s linear infinite" }} />
      </div>
    );
  }

  const acknowledgedCount = stats.acknowledged ?? stats.opened ?? 0;

  return (
    <div style={{ animation: "fadeInUp 0.25s ease" }}>
      {/* Header */}
      <div style={{ marginBottom: "20px", display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "4px" }}>
            <AlertTriangle size={20} color="#E24B4A" />
            <h1 style={{ color: textPrimary, fontSize: "22px", fontWeight: "800", margin: 0, letterSpacing: "-0.02em" }}>
              Alerts & Student Acknowledgment
            </h1>
          </div>
          <p style={{ color: textSecondary, fontSize: "13px", margin: 0 }}>
            SMTP Notification Engine · Australian Eastern Time (AEST) · {stats.total} total notices dispatched
          </p>
        </div>
        <button
          onClick={handleBulkSend}
          disabled={isSending}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "7px",
            padding: "9px 18px",
            background: isSending ? "#7AAED4" : "linear-gradient(135deg, #185FA5, #1A7ABF)",
            border: "none",
            borderRadius: "9px",
            color: "#FFFFFF",
            fontSize: "13px",
            fontWeight: "700",
            cursor: isSending ? "not-allowed" : "pointer",
            boxShadow: isSending ? "none" : "0 2px 8px rgba(24,95,165,0.35)",
          }}
        >
          {isSending ? (
            <RefreshCw size={13} color="#FFFFFF" style={{ animation: "spin 0.8s linear infinite" }} />
          ) : (
            <Mail size={13} color="#FFFFFF" />
          )}
          {isSending ? "Sending…" : "Send Bulk Alerts"}
        </button>
      </div>

      {/* Stat cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "14px", marginBottom: "20px" }}>
        {[
          {
            label: "Total Dispatched",
            value: stats.total,
            color: "#185FA5",
            bg: "#EBF4FF",
            icon: <Mail size={18} color="#185FA5" />,
          },
          {
            label: "Student Acknowledged",
            value: acknowledgedCount,
            color: "#16A34A",
            bg: "#ECFDF5",
            icon: <CheckCircle size={18} color="#16A34A" />,
          },
          {
            label: "Awaiting Student Action",
            value: stats.sent,
            color: "#D97706",
            bg: "#FEF3C7",
            icon: <Clock size={18} color="#D97706" />,
          },
          {
            label: "Delivery Failed / Bad Email",
            value: stats.failed,
            color: "#E24B4A",
            bg: "#FEE2E2",
            icon: <XCircle size={18} color="#E24B4A" />,
          },
        ].map((card) => (
          <div
            key={card.label}
            style={{
              background: "#FFFFFF",
              borderRadius: "12px",
              padding: "16px 18px",
              boxShadow: "0 1px 4px rgba(0,0,0,0.07)",
              borderTop: `3px solid ${card.color}`,
              display: "flex",
              alignItems: "center",
              gap: "12px",
            }}
          >
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
      {alertQueue.length > 0 && (
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
                <div
                  key={student.id}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "12px 20px",
                    background: idx % 2 === 0 ? "#FFFFFF" : "#F9FAFB",
                    borderBottom: idx < alertQueue.length - 1 ? "1px solid #F3F4F6" : "none",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                    <div style={{ width: "34px", height: "34px", borderRadius: "50%", background: config.bg, display: "flex", alignItems: "center", justifyContent: "center" }}>
                      <span style={{ color: config.color, fontSize: "11px", fontWeight: "700" }}>{student.initials}</span>
                    </div>
                    <div>
                      <div style={{ color: "#1A1A2E", fontSize: "13px", fontWeight: "600" }}>{student.name}</div>
                      <div style={{ color: "#9CA3AF", fontSize: "11px" }}>
                        {student.email} · {student.subject}
                      </div>
                    </div>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                    <span
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "4px",
                        padding: "3px 10px",
                        borderRadius: "999px",
                        background: config.bg,
                        color: config.color,
                        fontSize: "11px",
                        fontWeight: "600",
                      }}
                    >
                      <span style={{ width: "5px", height: "5px", borderRadius: "50%", background: config.color }} />
                      {config.label}
                    </span>
                    <button
                      onClick={() => handleSendAlert(student.id, student.name, student.email)}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "5px",
                        padding: "5px 12px",
                        background: "#185FA5",
                        border: "none",
                        borderRadius: "7px",
                        cursor: "pointer",
                        color: "#FFFFFF",
                        fontSize: "11px",
                        fontWeight: "600",
                      }}
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
      )}

      {/* Email Log */}
      <div style={{ background: "#FFFFFF", borderRadius: "12px", boxShadow: "0 1px 4px rgba(0,0,0,0.07)", overflow: "hidden" }}>
        <div style={{ padding: "16px 20px", borderBottom: "1px solid #F3F4F6", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <Mail size={15} color="#185FA5" />
            <h2 style={{ color: "#1A1A2E", fontSize: "14px", fontWeight: "700", margin: 0 }}>Email Notification & Acknowledgment Log</h2>
            <span style={{ background: "#EBF4FF", color: "#185FA5", fontSize: "11px", fontWeight: "700", padding: "2px 8px", borderRadius: "999px" }}>
              {filteredLogs.length} records
            </span>
          </div>
          <div style={{ display: "flex", gap: "8px" }}>
            <div style={{ position: "relative" }}>
              <Search size={12} color="#9CA3AF" style={{ position: "absolute", left: "10px", top: "50%", transform: "translateY(-50%)" }} />
              <input
                type="text"
                placeholder="Search student, email, reason…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                style={{ padding: "6px 10px 6px 28px", border: "1.5px solid #E5E7EB", borderRadius: "7px", fontSize: "12px", outline: "none", width: "220px" }}
              />
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
              <Filter size={12} color="#9CA3AF" />
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                style={{ padding: "6px 10px", border: "1.5px solid #E5E7EB", borderRadius: "7px", fontSize: "12px", outline: "none", cursor: "pointer" }}
              >
                <option value="All">All Statuses</option>
                <option value="Acknowledged">Acknowledged</option>
                <option value="Sent">Awaiting Action</option>
                <option value="Failed">Delivery Failed</option>
              </select>
            </div>
            <button
              onClick={handleExportCSV}
              title="Download filtered logs as CSV"
              style={{
                display: "flex",
                alignItems: "center",
                gap: "5px",
                padding: "6px 12px",
                background: "#FFFFFF",
                border: "1.5px solid #D1D5DB",
                borderRadius: "7px",
                color: "#374151",
                fontSize: "12px",
                fontWeight: "600",
                cursor: "pointer",
                transition: "all 0.15s ease",
              }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLButtonElement).style.borderColor = "#185FA5";
                (e.currentTarget as HTMLButtonElement).style.color = "#185FA5";
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLButtonElement).style.borderColor = "#D1D5DB";
                (e.currentTarget as HTMLButtonElement).style.color = "#374151";
              }}
            >
              <Download size={13} />
              Export CSV
            </button>
          </div>
        </div>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ background: "#F9FAFB" }}>
              {["Student", "Unit", "Delivery Status", "Sent At (AEST)", "Student Acknowledgment", "Elapsed / Days Tracker"].map((col) => (
                <th
                  key={col}
                  style={{
                    padding: "11px 16px",
                    textAlign: "left",
                    color: "#6B7280",
                    fontSize: "11px",
                    fontWeight: "600",
                    letterSpacing: "0.05em",
                    textTransform: "uppercase",
                    borderBottom: "1px solid #F3F4F6",
                  }}
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filteredLogs.length > 0 ? (
              filteredLogs.map((log, idx) => {
                const sc = statusConfig[log.status as keyof typeof statusConfig] || statusConfig.Pending;
                const isAcked = log.status === "Acknowledged" || log.status === "Opened";
                const isFailed = log.status === "Failed";
                const timeAgo = formatTimeAgo(log.sentAt);

                return (
                  <tr key={log.id} style={{ background: idx % 2 === 0 ? "#FFFFFF" : "#F9FAFB" }}>
                    {/* Student */}
                    <td style={{ padding: "11px 16px", borderBottom: "1px solid #F3F4F6" }}>
                      <div style={{ color: "#1A1A2E", fontSize: "13px", fontWeight: "600" }}>{log.student}</div>
                      <div style={{ color: "#6B7280", fontSize: "11px" }}>{log.email || "No email on record"}</div>
                      <div style={{ color: "#9CA3AF", fontSize: "10px" }}>{log.studentId}</div>
                    </td>

                    {/* Subject / Program */}
                    <td style={{ padding: "11px 16px", borderBottom: "1px solid #F3F4F6", color: "#374151", fontSize: "12px", fontWeight: "500" }}>
                      {log.subject}
                    </td>

                    {/* Delivery Status */}
                    <td style={{ padding: "11px 16px", borderBottom: "1px solid #F3F4F6" }}>
                      <div>
                        <span
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "4px",
                            padding: "3px 9px",
                            borderRadius: "999px",
                            background: sc.bg,
                            color: sc.color,
                            fontSize: "11px",
                            fontWeight: "600",
                          }}
                        >
                          {sc.icon} {isAcked ? "Acknowledged" : isFailed ? "Failed" : "Dispatched"}
                        </span>
                        {isFailed && log.errorMessage && (
                          <div style={{ color: "#DC2626", fontSize: "10px", marginTop: "3px", maxWidth: "220px", lineHeight: "1.3" }}>
                            ⚠️ {log.errorMessage}
                          </div>
                        )}
                      </div>
                    </td>

                    {/* Sent At */}
                    <td style={{ padding: "11px 16px", borderBottom: "1px solid #F3F4F6", color: "#4B5563", fontSize: "12px", whiteSpace: "nowrap" }}>
                      <div>{log.sentAt}</div>
                      <div style={{ color: "#9CA3AF", fontSize: "10px" }}>{timeAgo}</div>
                    </td>

                    {/* Acknowledgment Details */}
                    <td style={{ padding: "11px 16px", borderBottom: "1px solid #F3F4F6", fontSize: "12px", whiteSpace: "nowrap" }}>
                      {isAcked ? (
                        <div>
                          <div style={{ color: "#16A34A", fontWeight: "600", display: "flex", alignItems: "center", gap: "4px" }}>
                            <CheckCircle size={13} color="#16A34A" /> Confirmed by Student
                          </div>
                          <div style={{ color: "#6B7280", fontSize: "11px" }}>
                            {log.acknowledgedAt || log.openedAt || log.sentAt}
                          </div>
                        </div>
                      ) : isFailed ? (
                        <span style={{ color: "#9CA3AF", fontSize: "11px" }}>— (Not delivered)</span>
                      ) : (
                        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                          <span style={{ color: "#D97706", fontSize: "11px", fontWeight: "600", background: "#FEF3C7", padding: "2px 7px", borderRadius: "4px" }}>
                            ⏳ Awaiting Click
                          </span>
                          <a
                            href={`http://localhost:8000/alerts/acknowledge/${log.id}`}
                            target="_blank"
                            rel="noreferrer"
                            title="Test Student Acknowledgment Link"
                            style={{ color: "#185FA5", display: "inline-flex", alignItems: "center", gap: "2px", fontSize: "10px", textDecoration: "none" }}
                          >
                            <ExternalLink size={11} /> Test Ack
                          </a>
                        </div>
                      )}
                    </td>

                    {/* Elapsed / Days Tracker */}
                    <td style={{ padding: "11px 16px", borderBottom: "1px solid #F3F4F6", whiteSpace: "nowrap" }}>
                      {isAcked ? (
                        <span style={{ background: "#ECFDF5", color: "#16A34A", padding: "3px 8px", borderRadius: "6px", fontSize: "11px", fontWeight: "600", display: "inline-flex", alignItems: "center", gap: "4px" }}>
                          🟢 Resolved ({timeAgo})
                        </span>
                      ) : isFailed ? (
                        <span style={{ background: "#FEE2E2", color: "#DC2626", padding: "3px 8px", borderRadius: "6px", fontSize: "11px", fontWeight: "600", display: "inline-flex", alignItems: "center", gap: "4px" }}>
                          ❌ Undelivered
                        </span>
                      ) : (
                        <span style={{ background: "#FEF3C7", color: "#D97706", padding: "3px 8px", borderRadius: "6px", fontSize: "11px", fontWeight: "600", display: "inline-flex", alignItems: "center", gap: "4px" }}>
                          ⏱️ {timeAgo} pending
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })
            ) : (
              <tr>
                <td colSpan={6} style={{ padding: "32px", textAlign: "center", color: "#9CA3AF" }}>
                  No email logs matching the selected filter
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <div style={{ height: "32px" }} />
    </div>
  );
}