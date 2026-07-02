import {
  X, Mail, Phone, BookOpen, TrendingDown, TrendingUp, AlertTriangle,
  CheckCircle, Calendar, Clock, Brain, Shield, Minus, Zap, BarChart2,
} from "lucide-react";
import { type Student, type RiskLevel, riskConfig as baseRiskConfig } from "../data/studentData";

interface StudentDetailModalProps {
  student: Student | null;
  onClose: () => void;
  onSendAlert: (student: Student) => void;
}

const riskMeta: Record<RiskLevel, { label: string; icon: React.ReactNode }> = {
  HIGH: { label: "HIGH RISK", icon: <AlertTriangle size={14} color="#E24B4A" /> },
  MEDIUM: { label: "AT RISK", icon: <TrendingDown size={14} color="#EF9F27" /> },
  LOW: { label: "SAFE", icon: <CheckCircle size={14} color="#97C459" /> },
};

const trendIcon = (trend: Student["trend"]) => {
  if (trend === "improving") return <TrendingUp size={13} color="#16A34A" />;
  if (trend === "deteriorating") return <TrendingDown size={13} color="#DC2626" />;
  return <Minus size={13} color="#9CA3AF" />;
};

const trendColor = (trend: Student["trend"]) =>
  trend === "improving" ? "#16A34A" : trend === "deteriorating" ? "#DC2626" : "#9CA3AF";

function StatBar({ value, max, color }: { value: number; max: number; color: string }) {
  const pct = Math.min((value / max) * 100, 100);
  return (
    <div style={{ height: "8px", background: "#F3F4F6", borderRadius: "4px", overflow: "hidden", flex: 1 }}>
      <div style={{ height: "100%", width: `${pct}%`, background: color, borderRadius: "4px", transition: "width 0.5s ease" }} />
    </div>
  );
}

function ShapBar({ label, value, color, impact }: { label: string; value: number; color: string; impact: string }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
      <div style={{ width: "10px", height: "10px", background: color, borderRadius: "50%", flexShrink: 0 }} />
      <span style={{ color: "#374151", fontSize: "12px", fontWeight: "500", minWidth: "140px" }}>{label}</span>
      <div style={{ height: "8px", background: "#F3F4F6", borderRadius: "4px", overflow: "hidden", flex: 1 }}>
        <div style={{ height: "100%", width: `${value}%`, background: color, borderRadius: "4px", transition: "width 0.5s ease" }} />
      </div>
      <span style={{ color: color, fontSize: "10px", fontWeight: "600", minWidth: "50px", textAlign: "right" }}>{impact}</span>
    </div>
  );
}

const shapFactors: Record<RiskLevel, { label: string; value: number; color: string; impact: string }[]> = {
  HIGH: [
    { label: "Attendance Rate", value: 85, color: "#E24B4A", impact: "High ↑" },
    { label: "Missed Assessments", value: 72, color: "#E24B4A", impact: "High ↑" },
    { label: "Tutorial Submission", value: 65, color: "#EF9F27", impact: "Medium ↑" },
    { label: "GPA Decline Trend", value: 48, color: "#EF9F27", impact: "Medium ↑" },
  ],
  MEDIUM: [
    { label: "Tutorial Submission", value: 68, color: "#EF9F27", impact: "Medium ↑" },
    { label: "Attendance Rate", value: 55, color: "#EF9F27", impact: "Medium ↑" },
    { label: "Assignment Completion", value: 42, color: "#97C459", impact: "Low ↑" },
    { label: "Forum Participation", value: 28, color: "#97C459", impact: "Low ↑" },
  ],
  LOW: [
    { label: "Consistent Attendance", value: 35, color: "#97C459", impact: "Positive" },
    { label: "Strong GPA Trend", value: 28, color: "#97C459", impact: "Positive" },
    { label: "Complete Submissions", value: 22, color: "#97C459", impact: "Positive" },
    { label: "Active Engagement", value: 15, color: "#97C459", impact: "Positive" },
  ],
};

export function StudentDetailModal({ student, onClose, onSendAlert }: StudentDetailModalProps) {
  if (!student) return null;

  const config = baseRiskConfig[student.risk];
  const meta = riskMeta[student.risk];

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={onClose}
        style={{
          position: "fixed", inset: 0,
          background: "rgba(26,26,46,0.45)",
          zIndex: 100, backdropFilter: "blur(2px)",
        }}
      />

      {/* Modal */}
      <div
        style={{
          position: "fixed", top: "50%", left: "50%",
          transform: "translate(-50%, -50%)",
          width: "620px",
          maxWidth: "calc(100vw - 32px)",
          maxHeight: "calc(100vh - 64px)",
          overflowY: "auto",
          background: "#FFFFFF", borderRadius: "16px",
          boxShadow: "0 24px 64px rgba(0,0,0,0.18)",
          zIndex: 101,
        }}
      >
        {/* Header */}
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", padding: "24px 24px 20px 24px", borderBottom: "1px solid #F3F4F6" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
            <div style={{ width: "54px", height: "54px", borderRadius: "50%", background: config.bg, border: `2px solid ${config.color}30`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
              <span style={{ color: config.color, fontSize: "17px", fontWeight: "700" }}>{student.initials}</span>
            </div>
            <div>
              <h2 style={{ color: "#1A1A2E", fontSize: "18px", fontWeight: "700", margin: "0 0 5px 0" }}>{student.name}</h2>
              <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
                <span style={{ display: "inline-flex", alignItems: "center", gap: "4px", padding: "3px 10px", borderRadius: "999px", background: config.bg, color: config.color, fontSize: "11px", fontWeight: "700" }}>
                  {meta.icon} {meta.label}
                </span>
                <span style={{ color: "#6B7280", fontSize: "12px" }}>{student.subject}</span>
                <span style={{ color: "#6B7280", fontSize: "12px" }}>·</span>
                <span style={{ color: "#9CA3AF", fontSize: "12px" }}>{student.studentId}</span>
                <span style={{ color: "#9CA3AF", fontSize: "12px" }}>·</span>
                <span style={{ color: "#9CA3AF", fontSize: "12px" }}>{student.program}</span>
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            style={{ width: "32px", height: "32px", borderRadius: "8px", border: "1px solid #E5E7EB", background: "transparent", display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", flexShrink: 0 }}
          >
            <X size={16} color="#6B7280" />
          </button>
        </div>

        {/* Body */}
        <div style={{ padding: "20px 24px", display: "flex", flexDirection: "column", gap: "20px" }}>

          {/* Contact info row */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
            {[
              { icon: <Mail size={13} color="#6B7280" />, label: student.email },
              { icon: <Phone size={13} color="#6B7280" />, label: student.phone },
              { icon: <Calendar size={13} color="#6B7280" />, label: `Enrolled: ${student.enrolled}` },
              { icon: <Clock size={13} color="#6B7280" />, label: `Last active: ${student.lastLogin}` },
            ].map((item, i) => (
              <div key={i} style={{ display: "flex", alignItems: "center", gap: "6px", padding: "8px 10px", background: "#F9FAFB", borderRadius: "8px" }}>
                {item.icon}
                <span style={{ color: "#6B7280", fontSize: "12px" }}>{item.label}</span>
              </div>
            ))}
          </div>

          {/* Engagement stats row */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "10px" }}>
            {[
              { label: "Emails Sent", value: student.emailsSent, icon: <Mail size={13} color="#185FA5" />, color: "#185FA5", bg: "#EBF4FF" },
              { label: "Tutorial Sub.", value: `${student.tutorialSubmission}%`, icon: <BookOpen size={13} color="#7C3AED" />, color: "#7C3AED", bg: "#F5F3FF" },
              { label: "Forum Posts", value: student.forumActivity, icon: <BarChart2 size={13} color="#0891B2" />, color: "#0891B2", bg: "#ECFEFF" },
            ].map((stat) => (
              <div key={stat.label} style={{ padding: "10px 12px", background: stat.bg, borderRadius: "8px", display: "flex", alignItems: "center", gap: "10px" }}>
                {stat.icon}
                <div>
                  <div style={{ color: stat.color, fontSize: "16px", fontWeight: "800", lineHeight: "1" }}>{stat.value}</div>
                  <div style={{ color: stat.color, fontSize: "10px", opacity: 0.8, marginTop: "2px" }}>{stat.label}</div>
                </div>
              </div>
            ))}
          </div>

          {/* Performance metrics */}
          <div>
            <h4 style={{ color: "#1A1A2E", fontSize: "13px", fontWeight: "600", margin: "0 0 12px 0" }}>Performance Metrics</h4>
            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
                  <span style={{ color: "#6B7280", fontSize: "12px", fontWeight: "500" }}>Attendance</span>
                  <span style={{ color: config.color, fontSize: "12px", fontWeight: "700" }}>
                    {student.attendance}%
                    {student.attendance < 50 && <span style={{ color: "#E24B4A", marginLeft: "6px", fontSize: "11px" }}>⚠ Below threshold</span>}
                  </span>
                </div>
                <StatBar value={student.attendance} max={100} color={config.color} />
              </div>
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
                  <span style={{ color: "#6B7280", fontSize: "12px", fontWeight: "500" }}>GPA</span>
                  <span style={{ color: config.color, fontSize: "12px", fontWeight: "700" }}>
                    {student.gpa.toFixed(1)} / 4.0
                    {student.gpa < 2.0 && <span style={{ color: "#E24B4A", marginLeft: "6px", fontSize: "11px" }}>⚠ Probation risk</span>}
                  </span>
                </div>
                <StatBar value={student.gpa} max={4} color={config.color} />
              </div>
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
                  <span style={{ color: "#6B7280", fontSize: "12px", fontWeight: "500" }}>Assignments Submitted</span>
                  <span style={{ color: config.color, fontSize: "12px", fontWeight: "700" }}>
                    {student.assignments.done} / {student.assignments.total}
                  </span>
                </div>
                <StatBar value={student.assignments.done} max={student.assignments.total} color={config.color} />
              </div>
            </div>
          </div>

          {/* Weekly attendance sparkline */}
          <div>
            <h4 style={{ color: "#1A1A2E", fontSize: "13px", fontWeight: "600", margin: "0 0 10px 0" }}>
              Weekly Attendance Trend (Weeks 1–8)
            </h4>
            <div style={{ display: "flex", alignItems: "flex-end", gap: "5px", height: "48px", padding: "0 4px" }}>
              {student.weeklyAttendance.map((val, i) => (
                <div key={i} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: "4px" }}>
                  <div
                    style={{
                      width: "100%",
                      height: `${(val / 100) * 40}px`,
                      background: val < 50 ? "#FCA5A5" : val < 70 ? "#FCD34D" : "#86EFAC",
                      borderRadius: "3px 3px 0 0",
                      minHeight: "3px",
                    }}
                  />
                  <span style={{ color: "#9CA3AF", fontSize: "9px" }}>W{i + 1}</span>
                </div>
              ))}
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "6px", marginTop: "8px" }}>
              {trendIcon(student.trend)}
              <span style={{ color: trendColor(student.trend), fontSize: "11px", fontWeight: "600", textTransform: "capitalize" }}>
                {student.trend}
              </span>
              <span style={{ color: "#9CA3AF", fontSize: "11px" }}>trend over the semester</span>
            </div>
          </div>

          {/* Lecturer notes */}
          <div>
            <h4 style={{ color: "#1A1A2E", fontSize: "13px", fontWeight: "600", margin: "0 0 10px 0" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                <BookOpen size={13} color="#185FA5" />
                Lecturer Notes & Risk Indicators
              </div>
            </h4>
            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              {student.notes.map((note, i) => (
                <div
                  key={i}
                  style={{
                    display: "flex", alignItems: "flex-start", gap: "8px",
                    padding: "8px 12px",
                    background: student.risk === "LOW" ? "#F3FAE8" : student.risk === "HIGH" ? "#FFF1F1" : "#FFF8F0",
                    borderRadius: "8px",
                    borderLeft: `3px solid ${config.color}`,
                  }}
                >
                  <span style={{ color: config.color, fontSize: "12px", marginTop: "1px" }}>•</span>
                  <span style={{ color: "#374151", fontSize: "12px", lineHeight: "1.4" }}>{note}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Risk score + confidence */}
          <div style={{ padding: "14px", background: "#F9FAFB", borderRadius: "10px", border: "1px solid #E5E7EB" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "10px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                <Zap size={13} color="#185FA5" />
                <span style={{ color: "#6B7280", fontSize: "12px", fontWeight: "600" }}>Hybrid Detection Score</span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                <span style={{ color: config.color, fontSize: "20px", fontWeight: "800" }}>
                  {student.mlScore.toFixed(2)}
                </span>
                <span style={{ color: "#9CA3AF", fontSize: "12px" }}>/ 1.00</span>
              </div>
            </div>
            <StatBar value={student.mlScore * 100} max={100} color={config.color} />
            <div style={{ display: "flex", gap: "8px", marginTop: "10px" }}>
              <div style={{ flex: 1, padding: "6px 8px", background: "#EBF4FF", borderRadius: "6px", display: "flex", alignItems: "center", gap: "4px" }}>
                <Brain size={11} color="#185FA5" />
                <span style={{ color: "#185FA5", fontSize: "10px", fontWeight: "600" }}>Learning Model</span>
              </div>
              <div style={{ flex: 1, padding: "6px 8px", background: "#F3FAE8", borderRadius: "6px", display: "flex", alignItems: "center", gap: "4px" }}>
                <Shield size={11} color="#2D8B4E" />
                <span style={{ color: "#2D8B4E", fontSize: "10px", fontWeight: "600" }}>Rule-Based Engine</span>
              </div>
              <div style={{ flex: 1, padding: "6px 8px", background: "#F5F3FF", borderRadius: "6px", display: "flex", alignItems: "center", gap: "4px" }}>
                <BarChart2 size={11} color="#7C3AED" />
                <span style={{ color: "#7C3AED", fontSize: "10px", fontWeight: "600" }}>Confidence: {student.confidence}%</span>
              </div>
            </div>
            <p style={{ color: "#9CA3AF", fontSize: "11px", margin: "8px 0 0 0" }}>
              SHAP explainability · Last model run: Today at 8:00 AM
            </p>
          </div>

          {/* SHAP analysis */}
          <div>
            <h4 style={{ color: "#1A1A2E", fontSize: "13px", fontWeight: "600", margin: "0 0 10px 0" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                <Brain size={13} color="#185FA5" />
                SHAP Feature Impact Analysis
              </div>
            </h4>
            <p style={{ color: "#6B7280", fontSize: "11px", marginBottom: "12px" }}>
              Top contributing factors to this student's risk classification (XAI explainability)
            </p>
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              {shapFactors[student.risk].map((f) => (
                <ShapBar key={f.label} {...f} />
              ))}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div style={{ display: "flex", gap: "10px", padding: "16px 24px", borderTop: "1px solid #F3F4F6" }}>
          <button
            onClick={onClose}
            style={{ flex: 1, padding: "9px", background: "transparent", border: "1.5px solid #E5E7EB", borderRadius: "8px", color: "#6B7280", fontSize: "13px", fontWeight: "600", cursor: "pointer" }}
          >
            Close
          </button>
          <button
            onClick={() => onSendAlert(student)}
            style={{
              flex: 2, padding: "9px",
              background: student.risk === "HIGH" ? "#E24B4A" : student.risk === "MEDIUM" ? "#EF9F27" : "#185FA5",
              border: "none", borderRadius: "8px", color: "#FFFFFF", fontSize: "13px",
              fontWeight: "600", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: "6px",
              boxShadow: "0 2px 8px rgba(0,0,0,0.2)",
            }}
          >
            <Mail size={14} color="#FFFFFF" />
            Send SMTP Alert Email
          </button>
        </div>
      </div>
    </>
  );
}