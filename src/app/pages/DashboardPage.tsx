import { useState, useEffect } from "react";
import { toast } from "sonner";
import { FilterBar } from "../components/FilterBar";
import { MetricCards } from "../components/MetricCards";
import { StudentTable } from "../components/StudentTable";
import { RiskDonutChart } from "../components/RiskDonutChart";
import { AlertsPanel } from "../components/AlertsPanel";
import { ActivityFeed } from "../components/ActivityFeed";
import { StudentDetailModal } from "../components/StudentDetailModal";
import { RiskTrendChart } from "../components/RiskTrendChart";
import { Cpu, RefreshCw, Calendar } from "lucide-react";
import { useTheme } from "../context/ThemeContext";
import {fetchStudentOverview, fetchStudentDetails, type StudentOverview, type StudentDetails} from "../api/students";

export default function DashboardPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [riskFilter, setRiskFilter] = useState("All");
  const [termFilter, setTermFilter] = useState("Semester 1 2026");
  const [subjectGroupCode, setSubjectGroupCode] = useState("All Classes");
  const [selectedStudent, setSelectedStudent] = useState<StudentDetails | null>(null);
  const [isAnalysing, setIsAnalysing] = useState(false);
  const [currentWeek, setCurrentWeek] = useState(8);
  const [students, setStudents] = useState<StudentOverview[]>([]);

const [isLoading, setIsLoading] = useState(true);

const [error, setError] =
useState<string | null>(null);
  const handleImport = () => {
    toast.success("Moodle sync complete", {
      description: "248 student records imported and risk scores updated.",
      duration: 4000,
    });
  };

   //loads all students to the page
useEffect(() => {
    async function loadStudents() {
        try {
            setIsLoading(true);

            const data =
                await fetchStudentOverview();

            setStudents(data);
            setError(null);

        } catch (err) {
            setError(
                err instanceof Error
                ? err.message
                : "Failed to load students."
            );

        } finally {
            setIsLoading(false);
        }
    }

    loadStudents();
}, []);

  // Function to handle viewing student details
  const [loadingStudent, setLoadingStudent] = useState(false); //added for loading state when fetching student details

  const handleViewStudent = async (studentId: number) => {
    try {
      setLoadingStudent(true);
  
      const student = await fetchStudentDetails(studentId);
  
      console.log(student);
  
      setSelectedStudent(student);
  
    } catch (error) {
      console.error(error);
      toast.error("Unable to load student details.");
    } finally {
      setLoadingStudent(false);
    }
  };

  const handleRunAnalysis = async () => {
    if (isAnalysing) return;
    setIsAnalysing(true);
    toast.loading("Running hybrid analysis (Learning Model + Rule-Based ML Engine)…", { id: "analysis" });
    await new Promise(r => setTimeout(r, 2400));
    setIsAnalysing(false);
    toast.success("Analysis complete", {
      id: "analysis",
      description: "Risk scores updated for 248 students. Learning Model F1: 0.74 · Confidence: 92%",
      duration: 5000,
    });
  };

  // // const handleSendAlert = (student: Student) => {
  // //   setSelectedStudent(null);
  // //   toast.success("SMTP Alert Dispatched", {
  // //     description: `Email sent to ${student.email} via EdGuard notification system.`,
  // //     duration: 4000,
  // //   });
  // };

  const handleViewAllAlerts = () => {
    toast.info("Opening Alerts Management", { description: "Navigate to Alerts in the sidebar.", duration: 3000 });
  };

  const { isDark } = useTheme();
  const textPrimary = isDark ? "#F1F5F9" : "#0F172A";
  const textSecondary = isDark ? "#94A3B8" : "#6B7280";
  const textMono = isDark ? "#64748B" : "#9CA3AF";

  return (
    <div style={{ animation: "fadeInUp 0.25s ease" }}>
      {/* Page header */}
      <div style={{ marginBottom: "22px" }}>
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
          <div>
            
            <div style={{ display: "flex", alignItems: "baseline", gap: "12px", marginBottom: "6px" }}>
              <h1 style={{
                color: textPrimary,
                fontSize: "34px",
                fontWeight: 700,
                margin: 0,
                letterSpacing: "-0.035em",
                lineHeight: 1.05,
              }}>
                Risk <span style={{ fontFamily: "'Instrument Serif', serif", fontStyle: "italic", fontWeight: 400, color: "#185FA5" }}>Monitoring</span>
              </h1>
            </div>
            <p style={{ color: textSecondary, fontSize: "13px", margin: 0, fontFamily: "'Instrument Serif', serif", fontStyle: "italic", letterSpacing: "0.005em" }}>
              {termFilter} · Week {currentWeek}
            </p>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            {/* ML status */}
            <div style={{ display: "flex", alignItems: "center", gap: "6px", background: "#F0FDF4", padding: "7px 12px", borderRadius: "8px", border: "1px solid #BBF7D0" }}>
              <span style={{ width: "7px", height: "7px", background: "#22C55E", borderRadius: "50%", animation: "pulse 2s infinite" }} />
              <span style={{ color: "#16A34A", fontSize: "11px", fontWeight: "700" }}>Hybrid ML</span>
            </div>

            {/* Run analysis button */}
            <button onClick={handleRunAnalysis} disabled={isAnalysing}
              style={{
                padding: "8px 18px",
                background: isAnalysing
                  ? "linear-gradient(135deg, #7AAED4, #5A9EC4)"
                  : "linear-gradient(135deg, #185FA5 0%, #1A7ABF 100%)",
                color: "#FFFFFF", border: "none", borderRadius: "9px", fontSize: "13px",
                fontWeight: "700", cursor: isAnalysing ? "not-allowed" : "pointer",
                display: "flex", alignItems: "center", gap: "7px", transition: "opacity 0.2s",
                boxShadow: isAnalysing ? "none" : "0 2px 8px rgba(24,95,165,0.35)",
              }}
              onMouseEnter={e => { if (!isAnalysing) (e.currentTarget as HTMLButtonElement).style.opacity = "0.9"; }}
              onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.opacity = "1"; }}>
              {isAnalysing
                ? <RefreshCw size={13} color="#FFFFFF" style={{ animation: "spin 0.8s linear infinite" }} />
                : <Cpu size={13} color="#FFFFFF" />
              }
              {isAnalysing ? "Analysing…" : "Run Analysis"}
            </button>
          </div>
        </div>
      </div>

      {/* Filter bar */}
      <div style={{ marginBottom: "18px" }}>
        <FilterBar
          searchQuery={searchQuery} onSearchChange={setSearchQuery}
          riskFilter={riskFilter} onRiskFilterChange={setRiskFilter}
          termFilter={termFilter} onTermFilterChange={setTermFilter}
          subjectGroupCode={subjectGroupCode} onSubjectGroupCodeChange={setSubjectGroupCode}
          onImport={handleImport}
        />
      </div>

      {/* Metric cards */}
      <div style={{ marginBottom: "18px" }}>
        <MetricCards />
      </div>

      {/* Risk trend chart */}
      <div style={{ marginBottom: "18px" }}>
        <RiskTrendChart currentWeek={currentWeek} />
      </div>

      {/* Main 2-column layout */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 0.58fr", gap: "18px", alignItems: "start" }}>
        <StudentTable students={students} searchQuery={searchQuery} riskFilter={riskFilter} onViewStudent={handleViewStudent} />
        <div style={{ display: "flex", flexDirection: "column", gap: "18px" }}>
          <RiskDonutChart />
          <AlertsPanel onViewAll={handleViewAllAlerts} />
          <ActivityFeed />
        </div>
      </div>

      <div style={{ height: "32px" }} />

      <StudentDetailModal student={selectedStudent} onClose={() => setSelectedStudent(null)} />
    </div>
  );
}