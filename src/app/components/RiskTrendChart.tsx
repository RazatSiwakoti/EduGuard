import { useState } from "react";
import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis,
  CartesianGrid, Tooltip, Legend,
} from "recharts";
import { weeklyRiskData } from "../data/studentData";
import { TrendingUp } from "lucide-react";

const CustomTooltip = ({ active, payload, label }: { active?: boolean; payload?: Array<{ name: string; value: number; color: string }>; label?: string }) => {
  if (active && payload && payload.length) {
    return (
      <div style={{
        background: "#1A1A2E", borderRadius: "10px", padding: "12px 16px",
        boxShadow: "0 8px 24px rgba(0,0,0,0.2)", border: "1px solid #374151",
        minWidth: "140px",
      }}>
        <p style={{ color: "#9CA3AF", fontSize: "11px", fontWeight: "600", margin: "0 0 8px 0", textTransform: "uppercase", letterSpacing: "0.05em" }}>{label}</p>
        {payload.reverse().map(p => (
          <div key={p.name} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "12px", marginBottom: "4px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: p.color, display: "inline-block" }} />
              <span style={{ color: "#D1D5DB", fontSize: "11px" }}>{p.name}</span>
            </div>
            <span style={{ color: "#FFFFFF", fontSize: "12px", fontWeight: "700" }}>{p.value}%</span>
          </div>
        ))}
      </div>
    );
  }
  return null;
};

type ViewMode = "area" | "line";

export function RiskTrendChart({ currentWeek = 8 }: { currentWeek?: number }) {
  const [viewMode, setViewMode] = useState<ViewMode>("area");

  const filteredData = weeklyRiskData.slice(0, currentWeek);

  const weekChange = filteredData.length >= 2
    ? filteredData[filteredData.length - 1].high - filteredData[0].high
    : 0;

  return (
    <div style={{
      background: "#FFFFFF", borderRadius: "14px",
      boxShadow: "0 1px 4px rgba(0,0,0,0.07)", padding: "20px",
      display: "flex", flexDirection: "column", gap: "16px",
    }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <TrendingUp size={16} color="#185FA5" />
            <h3 style={{ color: "#1A1A2E", fontSize: "15px", fontWeight: "700", margin: 0 }}>
              Risk Trend — Semester Overview
            </h3>
          </div>
          <p style={{ color: "#9CA3AF", fontSize: "12px", margin: "4px 0 0 0" }}>
            Weekly risk level distribution · Weeks 1–{currentWeek}
          </p>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          {/* High risk delta */}
          {weekChange > 0 && (
            <div style={{ background: "#FEE2E2", color: "#DC2626", fontSize: "11px", fontWeight: "700", padding: "4px 10px", borderRadius: "20px", display: "flex", alignItems: "center", gap: "4px" }}>
              ↑ {weekChange}% High Risk increase
            </div>
          )}
          {/* View toggle */}
          <div style={{ display: "flex", background: "#F4F6F9", borderRadius: "8px", padding: "3px", gap: "2px" }}>
            {(["area", "line"] as ViewMode[]).map(m => (
              <button key={m} onClick={() => setViewMode(m)}
                style={{
                  padding: "4px 10px", borderRadius: "6px", border: "none",
                  background: viewMode === m ? "#FFFFFF" : "transparent",
                  color: viewMode === m ? "#185FA5" : "#6B7280",
                  fontSize: "11px", fontWeight: "600", cursor: "pointer",
                  boxShadow: viewMode === m ? "0 1px 3px rgba(0,0,0,0.1)" : "none",
                  transition: "all 0.15s", textTransform: "capitalize",
                }}>
                {m}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Chart */}
      <div style={{ height: "200px" }}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={filteredData} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
            <defs>
              {[
                { id: "high", color: "#E24B4A" },
                { id: "medium", color: "#EF9F27" },
                { id: "low", color: "#97C459" },
              ].map(({ id, color }) => (
                <linearGradient key={id} id={`grad-${id}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={color} stopOpacity={viewMode === "area" ? 0.3 : 0} />
                  <stop offset="100%" stopColor={color} stopOpacity={0.02} />
                </linearGradient>
              ))}
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" vertical={false} />
            <XAxis dataKey="week" tick={{ fontSize: 11, fill: "#9CA3AF", fontWeight: 500 }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 11, fill: "#9CA3AF" }} axisLine={false} tickLine={false} tickFormatter={v => `${v}%`} domain={[0, 100]} />
            <Tooltip content={<CustomTooltip />} />
            <Area type="monotone" dataKey="high" name="High Risk" stroke="#E24B4A" strokeWidth={2.5} fill="url(#grad-high)" dot={{ fill: "#E24B4A", strokeWidth: 0, r: 3 }} activeDot={{ r: 5, fill: "#E24B4A" }} />
            <Area type="monotone" dataKey="medium" name="At Risk" stroke="#EF9F27" strokeWidth={2.5} fill="url(#grad-medium)" dot={{ fill: "#EF9F27", strokeWidth: 0, r: 3 }} activeDot={{ r: 5, fill: "#EF9F27" }} />
            <Area type="monotone" dataKey="low" name="Safe" stroke="#97C459" strokeWidth={2.5} fill="url(#grad-low)" dot={{ fill: "#97C459", strokeWidth: 0, r: 3 }} activeDot={{ r: 5, fill: "#97C459" }} />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Legend stats */}
      <div style={{ display: "flex", gap: "12px" }}>
        {[
          { label: "High Risk", key: "high", color: "#E24B4A", bg: "#FEE2E2" },
          { label: "At Risk", key: "medium", color: "#EF9F27", bg: "#FEF3C7" },
          { label: "Safe", key: "low", color: "#97C459", bg: "#ECFDF5" },
        ].map(item => {
          const current = filteredData[filteredData.length - 1];
          const prev = filteredData[filteredData.length - 2];
          const val = current ? (current as Record<string, number>)[item.key] : 0;
          const delta = prev ? val - (prev as Record<string, number>)[item.key] : 0;
          return (
            <div key={item.key} style={{ flex: 1, background: item.bg, borderRadius: "10px", padding: "10px 12px", border: `1px solid ${item.color}20` }}>
              <div style={{ display: "flex", alignItems: "center", gap: "5px", marginBottom: "4px" }}>
                <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: item.color }} />
                <span style={{ color: item.color, fontSize: "10px", fontWeight: "700", textTransform: "uppercase", letterSpacing: "0.04em" }}>{item.label}</span>
              </div>
              <div style={{ color: item.color, fontSize: "20px", fontWeight: "800" }}>{val}%</div>
              <div style={{ color: item.color, fontSize: "10px", opacity: 0.75 }}>
                {delta > 0 ? `↑ ${delta}% from last week` : delta < 0 ? `↓ ${Math.abs(delta)}% from last week` : "No change"}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
