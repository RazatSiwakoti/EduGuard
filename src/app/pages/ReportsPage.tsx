import { useState } from "react";
import { toast } from "sonner";
import { BarChart2, Download, FileText, Database, TrendingUp, Users, Mail, CheckCircle2, Eye, Sparkles } from "lucide-react";
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis,
  CartesianGrid, Tooltip, Legend,
} from "recharts";
import { subjectRiskData, allStudents, weeklyRiskData } from "../data/studentData";
import { fetchEmailLogs } from "../api/alerts";
import { useTheme } from "../context/ThemeContext";
import { downloadCSV } from "../utils/csvExport";

const reportTypes = [
  {
    id: "full",
    label: "Full Risk Report",
    desc: "All 20 students with scores, trends and metrics",
    icon: <FileText size={18} color="#185FA5" />,
    color: "#185FA5",
    bg: "#EBF4FF",
    recordsCount: `${allStudents.length} students`,
  },
  {
    id: "high",
    label: "High-Risk Summary",
    desc: "High-risk students with action recommendations",
    icon: <TrendingUp size={18} color="#E24B4A" />,
    color: "#E24B4A",
    bg: "#FEE2E2",
    recordsCount: `${allStudents.filter((s) => s.risk === "HIGH").length} students`,
  },
  {
    id: "subject",
    label: "Subject Analytics",
    desc: "Risk breakdown and enrollment per subject/unit",
    icon: <BarChart2 size={18} color="#7C3AED" />,
    color: "#7C3AED",
    bg: "#F5F3FF",
    recordsCount: `${subjectRiskData.length} subjects`,
  },
  {
    id: "moodle",
    label: "Moodle Import Log",
    desc: "Last sync details, LMS submissions and record counts",
    icon: <Database size={18} color="#0891B2" />,
    color: "#0891B2",
    bg: "#ECFEFF",
    recordsCount: "8 sync cycles",
  },
  {
    id: "semester",
    label: "Semester Summary",
    desc: "Semester 1 2025 cohort-level overview and KPIs",
    icon: <Users size={18} color="#16A34A" />,
    color: "#16A34A",
    bg: "#ECFDF5",
    recordsCount: "6 KPI metrics",
  },
  {
    id: "shap",
    label: "SHAP Analysis Export",
    desc: "XAI feature importance data and correlation weights",
    icon: <Sparkles size={18} color="#D97706" />,
    color: "#D97706",
    bg: "#FEF3C7",
    recordsCount: "5 feature weights",
  },
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

export default function ReportsPage() {
  const { isDark } = useTheme();
  const [isExporting, setIsExporting] = useState<string | null>(null);

  const textPrimary = isDark ? "#F1F5F9" : "#1A1A2E";
  const textSecondary = isDark ? "#94A3B8" : "#6B7280";

  const handleExportReport = async (reportId: string, label: string) => {
    setIsExporting(reportId);
    try {
      if (reportId === "full") {
        const headers = [
          "Student ID",
          "Full Name",
          "Subject / Unit",
          "Program",
          "Risk Status",
          "Risk Trend",
          "ML Risk Score (0-1)",
          "Confidence (%)",
          "Attendance Rate (%)",
          "GPA",
          "Assignments Done",
          "Assignments Total",
          "Tutorial Submission (%)",
          "Forum Posts",
          "Alerts Sent",
          "Email Address",
          "Phone Number",
          "Enrollment Date",
          "Last LMS Activity",
        ];

        const rows = allStudents.map((s) => [
          s.studentId,
          s.name,
          s.subject,
          s.program,
          s.risk,
          s.trend,
          s.mlScore.toFixed(2),
          `${s.confidence}%`,
          `${s.attendance}%`,
          s.gpa.toFixed(2),
          s.assignments.done,
          s.assignments.total,
          `${s.tutorialSubmission}%`,
          s.forumActivity,
          s.emailsSent,
          s.email,
          s.phone,
          s.enrolled,
          s.lastLogin,
        ]);

        downloadCSV("EduGuard_Full_Cohort_Risk_Report_2026", headers, rows);
        toast.success(`Full Cohort Risk Report Downloaded`, {
          description: `Exported ${rows.length} student records successfully.`,
          duration: 3500,
        });
      } else if (reportId === "high") {
        const highRiskList = allStudents.filter((s) => s.risk === "HIGH");
        const headers = [
          "Student ID",
          "Student Name",
          "Subject Code",
          "Program",
          "ML Risk Score",
          "Confidence",
          "Attendance (%)",
          "GPA",
          "Assignments Missing",
          "Recommended Action",
          "Intervention Status",
          "Email",
          "Phone",
        ];

        const rows = highRiskList.map((s) => [
          s.studentId,
          s.name,
          s.subject,
          s.program,
          s.mlScore.toFixed(2),
          `${s.confidence}%`,
          `${s.attendance}%`,
          s.gpa.toFixed(2),
          s.assignments.total - s.assignments.done,
          s.attendance < 50
            ? "Mandatory attendance interview & welfare check"
            : "Urgent tutorial catch-up & assessment extension review",
          s.emailsSent > 0 ? `Alert Dispatched (${s.emailsSent} sent)` : "Pending Outreach",
          s.email,
          s.phone,
        ]);

        downloadCSV("EduGuard_High_Risk_Intervention_Summary_2026", headers, rows);
        toast.success(`High-Risk Summary Downloaded`, {
          description: `Exported ${rows.length} urgent intervention cases.`,
          duration: 3500,
        });
      } else if (reportId === "subject") {
        const headers = [
          "Subject Code",
          "Total Enrolled",
          "High Risk Count",
          "Medium Risk Count",
          "Low Risk (Safe) Count",
          "At-Risk Rate (%)",
        ];

        const rows = subjectRiskData.map((d) => [
          d.subject,
          d.total,
          d.high,
          d.medium,
          d.low,
          `${Math.round(((d.high + d.medium) / d.total) * 100)}%`,
        ]);

        downloadCSV("EduGuard_Subject_Risk_Analytics_2026", headers, rows);
        toast.success(`Subject Analytics Downloaded`, {
          description: `Exported risk metrics for ${rows.length} subjects.`,
          duration: 3500,
        });
      } else if (reportId === "moodle") {
        const headers = [
          "Sync ID",
          "Academic Week",
          "LMS Source",
          "Sync Timestamp",
          "Students Synchronized",
          "Attendance Records",
          "Assessment Submissions",
          "Forum Logs",
          "Sync Status",
        ];

        const rows = [
          ["SYNC-108", "Week 8", "Moodle LMS v4.2", "2026-08-26 14:00 (AEST)", 20, 160, 48, 112, "Success (100%)"],
          ["SYNC-107", "Week 7", "Moodle LMS v4.2", "2026-08-19 14:00 (AEST)", 20, 160, 44, 105, "Success (100%)"],
          ["SYNC-106", "Week 6", "Moodle LMS v4.2", "2026-08-12 14:00 (AEST)", 20, 160, 40, 98, "Success (100%)"],
          ["SYNC-105", "Week 5", "Moodle LMS v4.2", "2026-08-05 14:00 (AEST)", 20, 160, 36, 89, "Success (100%)"],
          ["SYNC-104", "Week 4", "Moodle LMS v4.2", "2026-07-29 14:00 (AEST)", 20, 160, 32, 81, "Success (100%)"],
          ["SYNC-103", "Week 3", "Moodle LMS v4.2", "2026-07-22 14:00 (AEST)", 20, 160, 28, 70, "Success (100%)"],
          ["SYNC-102", "Week 2", "Moodle LMS v4.2", "2026-07-15 14:00 (AEST)", 20, 160, 20, 55, "Success (100%)"],
          ["SYNC-101", "Week 1", "Moodle LMS v4.2", "2026-07-08 14:00 (AEST)", 20, 160, 12, 38, "Success (100%)"],
        ];

        downloadCSV("EduGuard_Moodle_LMS_Import_Log_2026", headers, rows);
        toast.success(`Moodle Import Log Downloaded`, {
          description: `Exported ${rows.length} LMS synchronization cycles.`,
          duration: 3500,
        });
      } else if (reportId === "semester") {
        const headers = ["KPI Metric", "Cohort Value", "Benchmark Target", "Status Assessment"];
        const avgAtt = Math.round(allStudents.reduce((a, b) => a + b.attendance, 0) / allStudents.length);
        const avgGpa = (allStudents.reduce((a, b) => a + b.gpa, 0) / allStudents.length).toFixed(2);
        const highCount = allStudents.filter((s) => s.risk === "HIGH").length;

        const rows = [
          ["Total Enrolled Cohort", `${allStudents.length} Students`, "20 Students", "Active"],
          ["High Risk Students (Urgent)", `${highCount} Students (${Math.round((highCount / allStudents.length) * 100)}%)`, "< 10%", "Requires Intervention"],
          ["Average Cohort Attendance", `${avgAtt}%`, "> 75%", avgAtt >= 75 ? "On Track" : "Below Benchmark"],
          ["Average Cohort GPA", avgGpa, "> 2.50", Number(avgGpa) >= 2.5 ? "Good" : "Attention Needed"],
          ["Overall Retention Probability", "91.4%", "> 90%", "Target Achieved"],
          ["Early Intervention Checkpoint", "Week 4 Completed", "Week 4", "Active Phase"],
        ];

        downloadCSV("EduGuard_Semester1_Cohort_Summary_2026", headers, rows);
        toast.success(`Semester Summary Downloaded`, {
          description: "Exported cohort metrics and benchmarks.",
          duration: 3500,
        });
      } else if (reportId === "shap") {
        const headers = [
          "Feature Name",
          "Feature Category",
          "Mean |SHAP Value| (Impact)",
          "Importance Rank",
          "Impact Direction",
          "Description",
        ];

        const rows = [
          ["attendance_rate", "Class Engagement", "+0.428", "1", "Negative (Lower attendance increases risk)", "Percentage of scheduled tutorials & lectures attended"],
          ["assignment_completion_rate", "Assessments", "+0.342", "2", "Negative (Missing assignments increases risk)", "Proportion of required coursework submitted on time"],
          ["lms_login_frequency", "Digital Engagement", "+0.215", "3", "Negative (Lower LMS logins increases risk)", "Weekly active sessions on Moodle learning portal"],
          ["cumulative_gpa", "Prior Academic Performance", "+0.187", "4", "Negative (Lower GPA increases risk)", "Historic weighted average grade point average"],
          ["forum_interaction_count", "Peer Collaboration", "+0.094", "5", "Negative (Low participation increases risk)", "Discussion forum replies and question posts"],
        ];

        downloadCSV("EduGuard_SHAP_XAI_Feature_Importance_2026", headers, rows);
        toast.success(`SHAP Analysis Exported`, {
          description: "Exported Explainable AI feature weights.",
          duration: 3500,
        });
      }
    } catch (err) {
      console.error("Export error:", err);
      toast.error(`Failed to export ${label}`);
    } finally {
      setIsExporting(null);
    }
  };

  const handleExportAlertsLog = async () => {
    try {
      const logs = await fetchEmailLogs();
      const headers = [
        "Log ID",
        "Student Name",
        "Student ID",
        "Recipient Email",
        "Unit / Subject",
        "Notice Type",
        "Template",
        "Delivery Status",
        "Sent At (AEST)",
        "Acknowledged At (AEST)",
        "Error / Diagnostic Notes",
      ];

      const rows = logs.map((l) => [
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

      downloadCSV("EduGuard_Email_Alerts_Acknowledgment_Log_2026", headers, rows);
      toast.success("Email & Acknowledgment Log Downloaded", {
        description: `Exported ${rows.length} notification audit records.`,
        duration: 3500,
      });
    } catch (err) {
      toast.error("Failed to download alert logs");
    }
  };

  return (
    <div style={{ animation: "fadeInUp 0.25s ease" }}>
      {/* Header */}
      <div style={{ marginBottom: "20px", display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "4px" }}>
            <BarChart2 size={20} color="#185FA5" />
            <h1 style={{ color: textPrimary, fontSize: "22px", fontWeight: "800", margin: 0, letterSpacing: "-0.02em" }}>
              Reports & Academic Analytics
            </h1>
          </div>
          <p style={{ color: textSecondary, fontSize: "13px", margin: 0 }}>
            Semester 1 2025 · Export compliant CSV reports, cohort trends, and audit logs
          </p>
        </div>
        <button
          onClick={handleExportAlertsLog}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "7px",
            padding: "9px 16px",
            background: "#FFFFFF",
            border: "1.5px solid #D1D5DB",
            borderRadius: "9px",
            color: "#374151",
            fontSize: "13px",
            fontWeight: "700",
            cursor: "pointer",
            boxShadow: "0 1px 3px rgba(0,0,0,0.05)",
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
          <Mail size={14} color="#185FA5" />
          Export Alert Audit Log (CSV)
        </button>
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
              <Bar dataKey="risk" name="Risk (High + Med)" fill="#E24B4A" radius={[4, 4, 0, 0]} />
              <Bar dataKey="safe" name="Safe (Low Risk)" fill="#97C459" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Risk over time mini table */}
      <div style={{ background: "#FFFFFF", borderRadius: "14px", boxShadow: "0 1px 4px rgba(0,0,0,0.07)", padding: "20px", marginBottom: "20px" }}>
        <h3 style={{ color: "#1A1A2E", fontSize: "15px", fontWeight: "700", margin: "0 0 16px 0" }}>Weekly Cohort Risk Trend Summary</h3>
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
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px" }}>
          <h3 style={{ color: textPrimary, fontSize: "15px", fontWeight: "700", margin: 0 }}>
            Standard CSV Exports & Audit Reports
          </h3>
          <span style={{ fontSize: "12px", color: "#6B7280" }}>6 reports available</span>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "14px" }}>
          {reportTypes.map((report) => (
            <div
              key={report.id}
              style={{
                background: "#FFFFFF",
                borderRadius: "12px",
                padding: "18px 20px",
                boxShadow: "0 1px 4px rgba(0,0,0,0.07)",
                border: "1px solid #F3F4F6",
                display: "flex",
                flexDirection: "column",
                justifyContent: "space-between",
                gap: "14px",
              }}
            >
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                  <div style={{ width: "40px", height: "40px", background: report.bg, borderRadius: "10px", display: "flex", alignItems: "center", justifyContent: "center" }}>
                    {report.icon}
                  </div>
                  <div>
                    <div style={{ color: "#1A1A2E", fontSize: "14px", fontWeight: "700" }}>{report.label}</div>
                    <span style={{ display: "inline-block", background: report.bg, color: report.color, fontSize: "10px", fontWeight: "700", padding: "1px 6px", borderRadius: "4px", marginTop: "2px" }}>
                      {report.recordsCount}
                    </span>
                  </div>
                </div>
                <div style={{ color: "#6B7280", fontSize: "12px", marginTop: "10px", lineHeight: "1.4" }}>
                  {report.desc}
                </div>
              </div>

              <button
                onClick={() => handleExportReport(report.id, report.label)}
                disabled={isExporting === report.id}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: "6px",
                  padding: "9px",
                  background: isExporting === report.id ? "#F3F4F6" : report.bg,
                  border: `1.5px solid ${report.color}40`,
                  borderRadius: "8px",
                  cursor: isExporting === report.id ? "not-allowed" : "pointer",
                  color: report.color,
                  fontSize: "12px",
                  fontWeight: "700",
                  transition: "all 0.15s ease",
                }}
                onMouseEnter={(e) => {
                  if (isExporting !== report.id) {
                    (e.currentTarget as HTMLButtonElement).style.background = report.color;
                    (e.currentTarget as HTMLButtonElement).style.color = "#FFFFFF";
                  }
                }}
                onMouseLeave={(e) => {
                  if (isExporting !== report.id) {
                    (e.currentTarget as HTMLButtonElement).style.background = report.bg;
                    (e.currentTarget as HTMLButtonElement).style.color = report.color;
                  }
                }}
              >
                <Download size={14} />
                {isExporting === report.id ? "Generating CSV…" : "Download CSV"}
              </button>
            </div>
          ))}
        </div>
      </div>

      <div style={{ height: "32px" }} />
    </div>
  );
}