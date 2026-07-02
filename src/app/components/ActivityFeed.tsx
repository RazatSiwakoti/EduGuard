import { TrendingDown, TrendingUp, Activity, Mail } from "lucide-react";

const activities = [
  {
    id: 1,
    type: "risk_up",
    text: "Sarah Johnson moved to HIGH risk",
    time: "2h ago",
    color: "#E24B4A",
  },
  {
    id: 2,
    type: "email",
    text: "SMTP: 12 automated alerts dispatched",
    time: "4h ago",
    color: "#185FA5",
  },
  {
    id: 3,
    type: "alert",
    text: "Week 8 checkpoint analysis completed",
    time: "6h ago",
    color: "#EF9F27",
  },
  {
    id: 4,
    type: "risk_down",
    text: "Tom Nguyen improved to LOW risk",
    time: "1d ago",
    color: "#97C459",
  },
  {
    id: 5,
    type: "import",
    text: "Moodle data sync completed (248 records)",
    time: "2d ago",
    color: "#185FA5",
  },
];

export function ActivityFeed() {
  return (
    <div
      style={{
        background: "#FFFFFF",
        borderRadius: "12px",
        boxShadow: "0 1px 4px rgba(0,0,0,0.08)",
        padding: "20px",
        display: "flex",
        flexDirection: "column",
        gap: "14px",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
        <Activity size={15} color="#185FA5" />
        <h3 style={{ color: "#1A1A2E", fontSize: "14px", fontWeight: "600", margin: 0 }}>
          Recent Activity
        </h3>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "0" }}>
        {activities.map((act, idx) => (
          <div
            key={act.id}
            style={{
              display: "flex",
              alignItems: "flex-start",
              gap: "10px",
              paddingBottom: idx < activities.length - 1 ? "12px" : "0",
              paddingTop: idx > 0 ? "12px" : "0",
              borderBottom: idx < activities.length - 1 ? "1px solid #F3F4F6" : "none",
            }}
          >
            {/* Icon */}
            <div
              style={{
                width: "28px",
                height: "28px",
                borderRadius: "50%",
                background: `${act.color}15`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
                marginTop: "1px",
              }}
            >
              {act.type === "risk_up" ? (
                <TrendingDown size={12} color={act.color} />
              ) : act.type === "risk_down" ? (
                <TrendingUp size={12} color={act.color} />
              ) : act.type === "email" ? (
                <Mail size={12} color={act.color} />
              ) : (
                <Activity size={12} color={act.color} />
              )}
            </div>
            <div style={{ flex: 1 }}>
              <p style={{ color: "#1A1A2E", fontSize: "12px", margin: "0 0 2px 0", lineHeight: "1.4" }}>
                {act.text}
              </p>
              <span style={{ color: "#9CA3AF", fontSize: "11px" }}>{act.time}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}