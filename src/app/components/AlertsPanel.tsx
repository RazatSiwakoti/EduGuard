import { ArrowRight, BellRing, Clock, X, CheckCheck } from "lucide-react";
import { useState } from "react";

interface Alert {
  id: number;
  studentName: string;
  initials: string;
  message: string;
  time: string;
  severity: "HIGH" | "MEDIUM";
  subject: string;
  reviewed: boolean;
}

const initialAlerts: Alert[] = [
  { id: 1, studentName: "Sarah Johnson", initials: "SJ", message: "Attendance dropped below 50%", time: "2 hours ago", severity: "HIGH", subject: "BSYS301", reviewed: false },
  { id: 2, studentName: "Priya Patel", initials: "PP", message: "GPA below threshold (1.5)", time: "5 hours ago", severity: "HIGH", subject: "BSYS301", reviewed: false },
  { id: 3, studentName: "Michael Chen", initials: "MC", message: "3 assignments missing", time: "Yesterday", severity: "MEDIUM", subject: "BSYS301", reviewed: false },
];

const severityConfig = {
  HIGH: { color: "#E24B4A", bg: "#FEE2E2", border: "#E24B4A", avatarBg: "#FEE2E2" },
  MEDIUM: { color: "#EF9F27", bg: "#FFFBEB", border: "#EF9F27", avatarBg: "#FEF3C7" },
};

interface AlertsPanelProps {
  onViewAll: () => void;
}

export function AlertsPanel({ onViewAll }: AlertsPanelProps) {
  const [alerts, setAlerts] = useState<Alert[]>(initialAlerts);

  const handleReview = (id: number) => {
    setAlerts((prev) => prev.map((a) => (a.id === id ? { ...a, reviewed: true } : a)));
  };

  const handleDismiss = (id: number) => {
    setAlerts((prev) => prev.filter((a) => a.id !== id));
  };

  const unreviewed = alerts.filter((a) => !a.reviewed).length;

  return (
    <div style={{ background: "#FFFFFF", borderRadius: "12px", boxShadow: "0 1px 4px rgba(0,0,0,0.08)", display: "flex", flexDirection: "column", overflow: "hidden" }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "18px 20px", borderBottom: "1px solid #F3F4F6" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <div style={{ width: "28px", height: "28px", background: "#FEF2F2", borderRadius: "7px", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <BellRing size={14} color="#E24B4A" />
          </div>
          <h3 style={{ color: "#1A1A2E", fontSize: "15px", fontWeight: "600", margin: 0 }}>Recent Alerts</h3>
        </div>
        {unreviewed > 0 && (
          <span style={{ background: "#FEE2E2", color: "#E24B4A", fontSize: "11px", fontWeight: "700", padding: "3px 8px", borderRadius: "999px" }}>
            {unreviewed} new
          </span>
        )}
      </div>

      {/* Alert items */}
      <div style={{ display: "flex", flexDirection: "column" }}>
        {alerts.length === 0 ? (
          <div style={{ padding: "32px 20px", textAlign: "center" }}>
            <CheckCheck size={28} color="#97C459" style={{ marginBottom: "8px" }} />
            <p style={{ color: "#6B7280", fontSize: "13px", margin: 0 }}>All alerts reviewed!</p>
          </div>
        ) : (
          alerts.map((alert, idx) => {
            const config = severityConfig[alert.severity];
            return (
              <div
                key={alert.id}
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  gap: "12px",
                  padding: "14px 16px 14px 20px",
                  borderLeft: `3.5px solid ${alert.reviewed ? "#D1D5DB" : config.border}`,
                  borderBottom: idx < alerts.length - 1 ? "1px solid #F9FAFB" : "none",
                  background: alert.reviewed ? "#FAFAFA" : "#FFFFFF",
                  opacity: alert.reviewed ? 0.65 : 1,
                  transition: "all 0.2s",
                }}
              >
                {/* Avatar */}
                <div style={{ width: "34px", height: "34px", borderRadius: "50%", background: alert.reviewed ? "#F3F4F6" : config.avatarBg, border: `1.5px solid ${alert.reviewed ? "#E5E7EB" : config.color + "30"}`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                  <span style={{ color: alert.reviewed ? "#9CA3AF" : config.color, fontSize: "11px", fontWeight: "700" }}>
                    {alert.initials}
                  </span>
                </div>

                {/* Content */}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "2px" }}>
                    <span style={{ color: "#1A1A2E", fontSize: "13px", fontWeight: "700" }}>{alert.studentName}</span>
                    {!alert.reviewed && (
                      <span style={{ background: config.bg, color: config.color, fontSize: "10px", fontWeight: "600", padding: "1px 6px", borderRadius: "999px" }}>
                        {alert.severity}
                      </span>
                    )}
                    {alert.reviewed && (
                      <span style={{ background: "#ECFDF5", color: "#97C459", fontSize: "10px", fontWeight: "600", padding: "1px 6px", borderRadius: "999px", display: "flex", alignItems: "center", gap: "3px" }}>
                        <CheckCheck size={9} color="#97C459" /> Reviewed
                      </span>
                    )}
                  </div>
                  <p style={{ color: "#6B7280", fontSize: "12px", margin: "0 0 4px 0", lineHeight: "1.4" }}>{alert.message}</p>
                  <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                    <Clock size={10} color="#9CA3AF" />
                    <span style={{ color: "#9CA3AF", fontSize: "11px" }}>{alert.time}</span>
                    <span style={{ color: "#E5E7EB", margin: "0 2px" }}>·</span>
                    <span style={{ color: "#9CA3AF", fontSize: "11px" }}>{alert.subject}</span>
                  </div>
                </div>

                {/* Actions */}
                <div style={{ display: "flex", flexDirection: "column", gap: "4px", flexShrink: 0 }}>
                  {!alert.reviewed ? (
                    <button
                      onClick={() => handleReview(alert.id)}
                      style={{ padding: "4px 10px", background: config.bg, border: `1px solid ${config.color}20`, borderRadius: "6px", color: config.color, fontSize: "11px", fontWeight: "600", cursor: "pointer", whiteSpace: "nowrap", transition: "opacity 0.15s" }}
                      onMouseEnter={(e) => ((e.currentTarget as HTMLButtonElement).style.opacity = "0.75")}
                      onMouseLeave={(e) => ((e.currentTarget as HTMLButtonElement).style.opacity = "1")}
                    >
                      ✓ Review
                    </button>
                  ) : null}
                  <button
                    onClick={() => handleDismiss(alert.id)}
                    style={{ width: "24px", height: "24px", borderRadius: "6px", border: "1px solid #E5E7EB", background: "transparent", display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", alignSelf: "flex-end" }}
                    title="Dismiss"
                    onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.background = "#FEE2E2"; (e.currentTarget as HTMLButtonElement).style.borderColor = "#E24B4A"; }}
                    onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.background = "transparent"; (e.currentTarget as HTMLButtonElement).style.borderColor = "#E5E7EB"; }}
                  >
                    <X size={11} color="#9CA3AF" />
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Footer */}
      <div style={{ padding: "14px 20px", borderTop: "1px solid #F3F4F6", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <span style={{ color: "#9CA3AF", fontSize: "12px" }}>Automated alerts via ML model</span>
        <button
          onClick={onViewAll}
          style={{ display: "flex", alignItems: "center", gap: "4px", background: "transparent", border: "none", cursor: "pointer", padding: 0 }}
          onMouseEnter={(e) => ((e.currentTarget as HTMLButtonElement).style.textDecoration = "underline")}
          onMouseLeave={(e) => ((e.currentTarget as HTMLButtonElement).style.textDecoration = "none")}
        >
          <span style={{ color: "#185FA5", fontSize: "13px", fontWeight: "600" }}>View all alerts</span>
          <ArrowRight size={13} color="#185FA5" />
        </button>
      </div>
    </div>
  );
}
