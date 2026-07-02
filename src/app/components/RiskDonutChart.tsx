import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";

const data = [
  { name: "HIGH", value: 14, color: "#E24B4A", bg: "#FEE2E2" },
  { name: "MEDIUM", value: 22, color: "#EF9F27", bg: "#FEF3C7" },
  { name: "LOW", value: 64, color: "#97C459", bg: "#ECFDF5" },
];

const CustomTooltip = ({ active, payload }: { active?: boolean; payload?: Array<{ name: string; value: number; payload: { color: string } }> }) => {
  if (active && payload && payload.length) {
    const item = payload[0];
    return (
      <div
        style={{
          background: "#1A1A2E",
          borderRadius: "8px",
          padding: "8px 12px",
          boxShadow: "0 4px 16px rgba(0,0,0,0.15)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <span
            style={{
              width: "8px",
              height: "8px",
              borderRadius: "50%",
              background: item.payload.color,
              display: "inline-block",
            }}
          />
          <span style={{ color: "#FFFFFF", fontSize: "12px", fontWeight: "600" }}>
            {item.name}: {item.value}%
          </span>
        </div>
      </div>
    );
  }
  return null;
};

export function RiskDonutChart() {
  const totalAtRisk = data.find((d) => d.name === "HIGH")!.value + data.find((d) => d.name === "MEDIUM")!.value;

  return (
    <div
      style={{
        background: "#FFFFFF",
        borderRadius: "12px",
        boxShadow: "0 1px 4px rgba(0,0,0,0.08)",
        padding: "20px",
        display: "flex",
        flexDirection: "column",
        gap: "16px",
      }}
    >
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div>
          <h3 style={{ color: "#1A1A2E", fontSize: "15px", fontWeight: "600", margin: 0 }}>
            Risk Distribution
          </h3>
          <p style={{ color: "#9CA3AF", fontSize: "12px", margin: "2px 0 0 0" }}>
            Current semester overview
          </p>
        </div>
        <span
          style={{
            background: "#F4F6F9",
            color: "#6B7280",
            fontSize: "11px",
            fontWeight: "600",
            padding: "4px 10px",
            borderRadius: "6px",
          }}
        >
          248 total
        </span>
      </div>

      {/* Chart + center label */}
      <div style={{ position: "relative", height: "180px" }}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={55}
              outerRadius={82}
              paddingAngle={3}
              dataKey="value"
              strokeWidth={0}
              startAngle={90}
              endAngle={-270}
            >
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip content={<CustomTooltip />} />
          </PieChart>
        </ResponsiveContainer>

        {/* Center label */}
        <div
          style={{
            position: "absolute",
            top: "50%",
            left: "50%",
            transform: "translate(-50%, -50%)",
            textAlign: "center",
            pointerEvents: "none",
          }}
        >
          <div style={{ color: "#1A1A2E", fontSize: "22px", fontWeight: "700", lineHeight: "1" }}>
            {totalAtRisk}%
          </div>
          <div style={{ color: "#9CA3AF", fontSize: "10px", fontWeight: "500", marginTop: "3px" }}>
            At-Risk
          </div>
        </div>
      </div>

      {/* Legend */}
      <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
        {data.map((item) => (
          <div key={item.name} style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <div
              style={{
                width: "10px",
                height: "10px",
                borderRadius: "50%",
                background: item.color,
                flexShrink: 0,
              }}
            />
            <span style={{ color: "#6B7280", fontSize: "12px", fontWeight: "500", flex: 1 }}>
              {item.name === "HIGH" ? "High Risk" : item.name === "MEDIUM" ? "Medium Risk" : "Low Risk"}
            </span>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <div
                style={{
                  height: "5px",
                  width: "60px",
                  background: "#F3F4F6",
                  borderRadius: "3px",
                  overflow: "hidden",
                }}
              >
                <div
                  style={{
                    height: "100%",
                    width: `${item.value}%`,
                    background: item.color,
                    borderRadius: "3px",
                  }}
                />
              </div>
              <span
                style={{
                  color: item.color,
                  fontSize: "12px",
                  fontWeight: "700",
                  minWidth: "28px",
                  textAlign: "right",
                }}
              >
                {item.value}%
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Divider */}
      <div style={{ height: "1px", background: "#F3F4F6" }} />

      {/* Bottom stats */}
      <div style={{ display: "flex", gap: "12px" }}>
        {data.map((item) => (
          <div
            key={item.name}
            style={{
              flex: 1,
              background: item.bg,
              borderRadius: "8px",
              padding: "10px",
              textAlign: "center",
            }}
          >
            <div style={{ color: item.color, fontSize: "16px", fontWeight: "700" }}>
              {Math.round((item.value / 100) * 248)}
            </div>
            <div style={{ color: item.color, fontSize: "10px", fontWeight: "500", opacity: 0.8 }}>
              {item.name === "HIGH" ? "High" : item.name === "MEDIUM" ? "Medium" : "Low"}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
