import { useState } from "react";
import { BarChart2, Download, FileText, Database, TrendingUp, Users } from "lucide-react";
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis,
  CartesianGrid, Tooltip, Legend,
} from "recharts";
import { subjectRiskData, allStudents, weeklyRiskData } from "../data/studentData";
import { useTheme } from "../context/ThemeContext";

const reportTypes = [
  { id: "full", label: "Full Risk Report", desc: "All 20 students with scores, trends and SHAP", icon: <FileText size={18} color="#185FA5" />, color: "#185FA5", bg: "#EBF4FF" },
  { id: "high", label: "High-Risk Summary", desc: "High-risk students with action recommendations", icon: <TrendingUp size={18} color="#E24B4A" />, color: "#E24B4A", bg: "#FEE2E2" },
  { id: "subject", label: "Subject Analytics", desc: "Risk breakdown per subject/unit", icon: <BarChart2 size={18} color="#7C3AED" />, color: "#7C3AED", bg: "#F5F3FF" },
  { id: "moodle", label: "Moodle Import Log", desc: "Last sync details and record counts", icon: <Database size={18} color="#0891B2" />, color: "#0891B2", bg: "#ECFEFF" },
  { id: "semester", label: "Semester Summary", desc: "Semester 1 2025 cohort-level overview", icon: <Users size={18} color="#16A34A" />, color: "#16A34A", bg: "#ECFDF5" },
  { id: "shap", label: "SHAP Analysis Export", desc: "XAI feature importance data CSV", icon: <Download size={18} color="#D97706" />, color: "#D97706", bg: "#FEF3C7" },
];

const subjectChartData = subjectRiskData.map((d) => ({
  name: d.subject,
  risk: d.high + d.medium,
  safe: d.low,
}));

const semesterStats = [
  { label: "Total Students", value: allStudents.length, color: "#185FA5" },
  { label: "High Risk", value: allStudents.filter((s) => s.risk === "HIGH").length, color: "#E24B4A" },
  { label: "At Risk (Med)", value: allStudents.filter((s) => s.risk === "MEDIUM").length, color: "#EF9F27" },
  { label: "Safe (Low)", value: allStudents.filter((s) => s.risk === "LOW").length, color: "#97C459" },
  { label: "Avg Attendance", value: `${Math.round(allStudents.reduce((a, b) => a + b.attendance, 0) / allStudents.length)}%`, color: "#185FA5" },
  { label: "Avg GPA", value: (allStudents.reduce((a, b) => a + b.gpa, 0) / allStudents.length).toFixed(2), color: "#7C3AED" },
];

const handleExport = (label: string) => {
  toast.success(`${label} exported`, {
    description: "CSV file generated and downloaded.",
    duration: 3000,
  });
};

export default function ReportsPage() {
  const { isDark } = useTheme();
  const textPrimary = isDark ? "#F1F5F9" : "#1A1A2E";
  const textSecondary = isDark ? "#94A3B8" : "#6B7280";
  return (
    <div style={{ animation: "fadeInUp 0.25s ease" }}>
      {/* Header */}
      <div style={{ marginBottom: "20px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "4px" }}>
          <BarChart2 size={20} color="#185FA5" />
          <h1 style={{ color: textPrimary, fontSize: "22px", fontWeight: "800", margin: 0, letterSpacing: "-0.02em" }}>
            Reports & Analytics
          </h1>
        </div>
        <p style={{ color: textSecondary, fontSize: "13px", margin: 0 }}>
          Semester 1 2025 · Export, analyse and download EdGuard reports
        </p>
      </div>

      {/* Semester summary stats */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: "12px", marginBottom: "20px" }}>
        {semesterStats.map((stat) => (
          <div key={stat.label} style={{ background: "#FFFFFF", borderRadius: "10px", padding: "14px 16px", boxShadow: "0 1px 4px rgba(0,0,0,0.07)", textAlign: "center" }}>
            <div style={{ fontSize: "22px", fontWeight: "800", color: stat.color }}>{stat.value}</div>
            <div style={{ fontSize: "11px", color: "#6B7280", marginTop: "3px" }}>{stat.label}</div>
          </div>
        ))}
      </div>

      {/* Subject breakdown chart */}
      <div style={{ background: "#FFFFFF", borderRadius: "14px", boxShadow: "0 1px 4px rgba(0,0,0,0.07)", padding: "20px", marginBottom: "20px" }}>
        <div style={{ marginBottom: "16px" }}>
          <h3 style={{ color: "#1A1A2E", fontSize: "15px", fontWeight: "700", margin: "0 0 4px 0" }}>Risk Breakdown by Subject</h3>
          <p style={{ color: "#9CA3AF", fontSize: "12px", margin: 0 }}>Student risk distribution across all 4 subjects this semester</p>
        </div>
        <div style={{ height: "220px" }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={subjectChartData} margin={{ top: 4, right: 16, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" vertical={false} />
              <XAxis dataKey="name" tick={{ fontSize: 12, fill: "#6B7280" }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 11, fill: "#9CA3AF" }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ background: "#1A1A2E", border: "none", borderRadius: "8px", color: "#FFFFFF" }} />
              <Legend wrapperStyle={{ fontSize: "12px" }} />
              <Bar dataKey="risk" name="Risk" fill="#E24B4A" radius={[4, 4, 0, 0]} />
              <Bar dataKey="safe" name="Safe" fill="#97C459" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Risk over time mini table */}
      <div style={{ background: "#FFFFFF", borderRadius: "14px", boxShadow: "0 1px 4px rgba(0,0,0,0.07)", padding: "20px", marginBottom: "20px" }}>
        <h3 style={{ color: "#1A1A2E", fontSize: "15px", fontWeight: "700", margin: "0 0 16px 0" }}>Weekly Risk Trend Summary</h3>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ background: "#F9FAFB" }}>
                {["Week", "High Risk %", "At Risk %", "Safe %"].map((col) => (
                  <th key={col} style={{ padding: "10px 16px", textAlign: "left", color: "#6B7280", fontSize: "11px", fontWeight: "600", letterSpacing: "0.05em", textTransform: "uppercase", borderBottom: "1px solid #E5E7EB" }}>
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {weeklyRiskData.map((row, idx) => (
                <tr key={row.week} style={{ background: idx % 2 === 0 ? "#FFFFFF" : "#F9FAFB" }}>
                  <td style={{ padding: "10px 16px", borderBottom: "1px solid #F3F4F6", color: "#374151", fontSize: "13px", fontWeight: "600" }}>{row.week}</td>
                  <td style={{ padding: "10px 16px", borderBottom: "1px solid #F3F4F6" }}>
                    <span style={{ color: "#E24B4A", fontWeight: "700", fontSize: "13px" }}>{row.high}%</span>
                  </td>
                  <td style={{ padding: "10px 16px", borderBottom: "1px solid #F3F4F6" }}>
                    <span style={{ color: "#EF9F27", fontWeight: "700", fontSize: "13px" }}>{row.medium}%</span>
                  </td>
                  <td style={{ padding: "10px 16px", borderBottom: "1px solid #F3F4F6" }}>
                    <span style={{ color: "#97C459", fontWeight: "700", fontSize: "13px" }}>{row.low}%</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Report export cards */}
      <div>
        <h3 style={{ color: textPrimary, fontSize: "15px", fontWeight: "700", margin: "0 0 14px 0" }}>Export Reports</h3>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "14px" }}>
          {reportTypes.map((report) => (
            <div key={report.id} style={{ background: "#FFFFFF", borderRadius: "12px", padding: "18px 20px", boxShadow: "0 1px 4px rgba(0,0,0,0.07)", border: "1px solid #F3F4F6", display: "flex", flexDirection: "column", gap: "12px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                <div style={{ width: "40px", height: "40px", background: report.bg, borderRadius: "10px", display: "flex", alignItems: "center", justifyContent: "center" }}>
                  {report.icon}
                </div>
                <div>
                  <div style={{ color: "#1A1A2E", fontSize: "13px", fontWeight: "700" }}>{report.label}</div>
                  <div style={{ color: "#9CA3AF", fontSize: "11px", marginTop: "2px" }}>{report.desc}</div>
                </div>
              </div>
              <button
                onClick={() => handleExport(report.label)}
                style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "6px", padding: "8px", background: report.bg, border: `1px solid ${report.color}30`, borderRadius: "8px", cursor: "pointer", color: report.color, fontSize: "12px", fontWeight: "600", transition: "opacity 0.15s" }}
                onMouseEnter={(e) => ((e.currentTarget as HTMLButtonElement).style.opacity = "0.8")}
                onMouseLeave={(e) => ((e.currentTarget as HTMLButtonElement).style.opacity = "1")}
              >
                <Download size={13} color={report.color} />
                Download CSV
              </button>
            </div>
          ))}
        </div>
      </div>

      <div style={{ height: "32px" }} />
    </div>
  );
}