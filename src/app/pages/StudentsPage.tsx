//import { useState } from "react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { StudentDetailModal } from "../components/StudentDetailModal";
import { StudentTable } from "../components/StudentTable";
//import { allStudents, riskConfig, type Student, type RiskLevel } from "../data/studentData"; note allstudents are now students
import { riskConfig, type Student, type RiskLevel } from "../data/studentData";
import {
  fetchStudentOverview,
  type StudentOverview,
} from "../api/students";
import { Users, UserCheck, UserX, Search, Mail, Filter } from "lucide-react";
import { useTheme } from "../context/ThemeContext";

const subjects = ["All Subjects", "BSYS301", "BSYS201", "BSYS401", "INFO101"];

export default function StudentsPage() {
  const [selectedStudent, setSelectedStudent] = useState<Student | null>(null);

  // added for integration
  const [students, setStudents] = useState<StudentOverview[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [searchQuery, setSearchQuery] = useState("");
  const [riskFilter, setRiskFilter] = useState("All");
  const [subjectFilter, setSubjectFilter] = useState("All Subjects");
  const [activeTab, setActiveTab] = useState<"all" | RiskLevel>("all");
  
  
  //loads all students to the page
  useEffect(() => {
  async function loadStudents() {
    try {
      setIsLoading(true);

      const data = await fetchStudentOverview();

      setStudents(data);
      setError(null);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to load students."
      );
    } finally {
      setIsLoading(false);
    }
  }

  loadStudents();
}, []);

  const handleSendAlert = (student: Student) => {
    setSelectedStudent(null);
    toast.success("SMTP Alert Dispatched", {
      description: `Email sent to ${student.email}`,
      duration: 4000,
    });
  };

  const riskCounts = {
    HIGH: students.filter(s => s.risk === "HIGH").length,
    MEDIUM: students.filter(s => s.risk === "MEDIUM").length,
    LOW: students.filter(s => s.risk === "LOW").length,
  };

  const effectiveRiskFilter = activeTab === "all" ? riskFilter : activeTab;

  const { isDark } = useTheme();
  const textPrimary = isDark ? "#F1F5F9" : "#1A1A2E";
  const textSecondary = isDark ? "#94A3B8" : "#6B7280";
  const textMuted = isDark ? "#64748B" : "#9CA3AF";
  
  //exception handling
  if (isLoading) {
  return <div>Loading students...</div>;
}

if (error) {
  return <div>Unable to load students: {error}</div>;
}


  return (
    <div style={{ animation: "fadeInUp 0.25s ease" }}>
      {/* Header */}
      <div style={{ marginBottom: "20px" }}>
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "4px" }}>
              <Users size={20} color="#185FA5" />
              <h1 style={{ color: textPrimary, fontSize: "22px", fontWeight: "800", margin: 0, letterSpacing: "-0.02em" }}>
                Student Management
              </h1>
            </div>
            <p style={{ color: textSecondary, fontSize: "13px", margin: 0 }}>
              Semester 1 2025 · {students.length} enrolled students across 4 subjects
            </p>
          </div>
          <button onClick={() => toast.info("Bulk email drafted for all high-risk students", { duration: 3000 })}
            style={{ display: "flex", alignItems: "center", gap: "7px", padding: "9px 16px", background: "#185FA5", border: "none", borderRadius: "9px", color: "#FFFFFF", fontSize: "13px", fontWeight: "700", cursor: "pointer", transition: "opacity 0.15s", boxShadow: "0 2px 8px rgba(24,95,165,0.3)" }}
            onMouseEnter={e => ((e.currentTarget as HTMLButtonElement).style.opacity = "0.9")}
            onMouseLeave={e => ((e.currentTarget as HTMLButtonElement).style.opacity = "1")}>
            <Mail size={14} color="#FFFFFF" />
            Email All At-Risk
          </button>
        </div>
      </div>

      {/* Summary cards */}
      <div style={{ display: "flex", gap: "14px", marginBottom: "18px" }}>
        {[
          { label: "Total Students", value: students.length, icon: <Users size={18} color="#185FA5" />, bg: "#EBF4FF", color: "#185FA5", accentColor: "#185FA5" },
          { label: "High Risk", value: riskCounts.HIGH, icon: <UserX size={18} color="#E24B4A" />, bg: "#FEE2E2", color: "#E24B4A", accentColor: "#E24B4A" },
          { label: "At Risk (Medium)", value: riskCounts.MEDIUM, icon: <UserCheck size={18} color="#D97706" />, bg: "#FEF3C7", color: "#D97706", accentColor: "#EF9F27" },
          { label: "Safe (Low Risk)", value: riskCounts.LOW, icon: <UserCheck size={18} color="#16A34A" />, bg: "#ECFDF5", color: "#16A34A", accentColor: "#97C459" },
        ].map(card => (
          <div key={card.label} style={{
            flex: 1, background: "#FFFFFF", borderRadius: "12px", padding: "16px 18px",
            boxShadow: "0 1px 4px rgba(0,0,0,0.07)", borderTop: `3px solid ${card.accentColor}`,
            display: "flex", alignItems: "center", gap: "12px",
          }}>
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

      {/* Risk filter tabs */}
      <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "16px", background: "#FFFFFF", padding: "6px", borderRadius: "12px", boxShadow: "0 1px 4px rgba(0,0,0,0.07)", width: "fit-content" }}>
        {([
          { id: "all", label: "All Students", count: students.length, color: "#185FA5", bg: "#EBF4FF" },
          { id: "HIGH", label: "High Risk", count: riskCounts.HIGH, color: riskConfig.HIGH.color, bg: riskConfig.HIGH.bg },
          { id: "MEDIUM", label: "At Risk", count: riskCounts.MEDIUM, color: riskConfig.MEDIUM.color, bg: riskConfig.MEDIUM.bg },
          { id: "LOW", label: "Safe", count: riskCounts.LOW, color: riskConfig.LOW.color, bg: riskConfig.LOW.bg },
        ] as const).map(tab => (
          <button key={tab.id}
            onClick={() => { setActiveTab(tab.id as "all" | RiskLevel); setRiskFilter("All"); }}
            style={{
              display: "flex", alignItems: "center", gap: "7px", padding: "7px 14px",
              borderRadius: "8px", border: "none", cursor: "pointer", transition: "all 0.15s",
              background: activeTab === tab.id ? tab.bg : "transparent",
              fontWeight: activeTab === tab.id ? "700" : "400",
              color: activeTab === tab.id ? tab.color : "#6B7280", fontSize: "13px",
            }}>
            {tab.label}
            <span style={{ background: activeTab === tab.id ? tab.color : "#E5E7EB", color: activeTab === tab.id ? "#FFFFFF" : "#6B7280", fontSize: "10px", fontWeight: "700", padding: "1px 7px", borderRadius: "999px" }}>
              {tab.count}
            </span>
          </button>
        ))}
      </div>

      {/* Filters row */}
      <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "16px" }}>
        <div style={{ position: "relative", flex: 1, maxWidth: "320px" }}>
          <Search size={14} color="#9CA3AF" style={{ position: "absolute", left: "12px", top: "50%", transform: "translateY(-50%)", pointerEvents: "none" }} />
          <input type="text" placeholder="Search by name, ID or subject…" value={searchQuery} onChange={e => setSearchQuery(e.target.value)}
            style={{ width: "100%", padding: "9px 12px 9px 34px", background: "#FFFFFF", border: "1.5px solid #E5E7EB", borderRadius: "9px", fontSize: "13px", color: "#1A1A2E", outline: "none", boxSizing: "border-box" }}
            onFocus={e => (e.target.style.borderColor = "#185FA5")}
            onBlur={e => (e.target.style.borderColor = "#E5E7EB")} />
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <Filter size={14} color="#6B7280" />
          <select value={subjectFilter} onChange={e => setSubjectFilter(e.target.value)}
            style={{ padding: "9px 28px 9px 12px", background: "#FFFFFF", border: "1.5px solid #E5E7EB", borderRadius: "9px", fontSize: "13px", color: "#1A1A2E", cursor: "pointer", outline: "none", appearance: "none", WebkitAppearance: "none", backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%239CA3AF' stroke-width='2'%3E%3Cpolyline points='6 9 12 15 18 9'%3E%3C/polyline%3E%3C/svg%3E")`, backgroundRepeat: "no-repeat", backgroundPosition: "right 10px center" }}>
            {subjects.map(s => <option key={s}>{s}</option>)}
          </select>
        </div>
        <span style={{ color: textMuted, fontSize: "12px" }}>
          {activeTab === "all" ? students.length : students.filter(s => s.risk === activeTab).length} results
        </span>
      </div>

      <StudentTable
        students={students} //added students prop to StudentTable to pass the students data from StudentsPage
        searchQuery={searchQuery}
        riskFilter={activeTab === "all" ? riskFilter : activeTab}
        subjectFilter={subjectFilter === "All Subjects" ? "All" : subjectFilter}
       // onViewStudent={setSelectedStudent}
      />
      <div style={{ height: "32px" }} />
      <StudentDetailModal student={selectedStudent} onClose={() => setSelectedStudent(null)} onSendAlert={handleSendAlert} />
    </div>
  );
}