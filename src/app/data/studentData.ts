export type RiskLevel = "HIGH" | "MEDIUM" | "LOW";
export type RiskTrend = "improving" | "stable" | "deteriorating";

export interface Student {
  id: number;
  name: string;
  initials: string;
  studentId: string;
  subject: string;
  program: string;
  attendance: number;
  gpa: number;
  assignments: { done: number; total: number };
  risk: RiskLevel;
  trend: RiskTrend;
  weeklyAttendance: number[]; // Weeks 1–8
  email: string;
  phone: string;
  enrolled: string;
  lastLogin: string;
  notes: string[];
  emailsSent: number;
  tutorialSubmission: number; // %
  forumActivity: number; // posts
  mlScore: number; // 0–1
  confidence: number; // %
}

export const allStudents: Student[] = [
  // ── BSYS301 Business Systems ──────────────────────────────────────────
  {
    id: 1, name: "Sarah Johnson", initials: "SJ", studentId: "KOI-2025-001",
    subject: "BSYS301", program: "Bachelor of Business",
    attendance: 45, gpa: 1.8, assignments: { done: 3, total: 10 },
    risk: "HIGH", trend: "deteriorating",
    weeklyAttendance: [80, 72, 65, 58, 52, 48, 46, 45],
    email: "s.johnson@student.koi.edu.au", phone: "+61 412 345 678",
    enrolled: "Feb 2024", lastLogin: "3 days ago",
    notes: ["Missed 6 consecutive classes", "Has not submitted Assignment 4–10", "Requested extension twice"],
    emailsSent: 3, tutorialSubmission: 30, forumActivity: 2,
    mlScore: 0.87, confidence: 92,
  },
  {
    id: 2, name: "Michael Chen", initials: "MC", studentId: "KOI-2025-002",
    subject: "BSYS301", program: "Bachelor of Business",
    attendance: 58, gpa: 2.1, assignments: { done: 5, total: 10 },
    risk: "MEDIUM", trend: "stable",
    weeklyAttendance: [70, 68, 65, 62, 60, 59, 58, 58],
    email: "m.chen@student.koi.edu.au", phone: "+61 423 456 789",
    enrolled: "Jul 2024", lastLogin: "Yesterday",
    notes: ["Attendance declining over last 3 weeks", "Struggling with Group Project B", "Replied to last email"],
    emailsSent: 1, tutorialSubmission: 50, forumActivity: 8,
    mlScore: 0.54, confidence: 78,
  },
  {
    id: 3, name: "Emma Davis", initials: "ED", studentId: "KOI-2025-003",
    subject: "BSYS301", program: "Bachelor of Business",
    attendance: 52, gpa: 2.4, assignments: { done: 4, total: 10 },
    risk: "MEDIUM", trend: "deteriorating",
    weeklyAttendance: [75, 72, 68, 62, 58, 55, 53, 52],
    email: "e.davis@student.koi.edu.au", phone: "+61 434 567 890",
    enrolled: "Feb 2024", lastLogin: "2 days ago",
    notes: ["Borderline attendance — approaching threshold", "GPA dropped from 2.9 this term", "Active on discussion board"],
    emailsSent: 1, tutorialSubmission: 45, forumActivity: 14,
    mlScore: 0.61, confidence: 80,
  },
  {
    id: 4, name: "James Wilson", initials: "JW", studentId: "KOI-2025-004",
    subject: "BSYS301", program: "Bachelor of Business",
    attendance: 88, gpa: 3.7, assignments: { done: 9, total: 10 },
    risk: "LOW", trend: "improving",
    weeklyAttendance: [85, 87, 86, 88, 90, 89, 88, 88],
    email: "j.wilson@student.koi.edu.au", phone: "+61 445 678 901",
    enrolled: "Feb 2023", lastLogin: "Today",
    notes: ["Consistently strong performer", "On track for HD grade", "Peer tutor candidate"],
    emailsSent: 0, tutorialSubmission: 90, forumActivity: 32,
    mlScore: 0.12, confidence: 95,
  },
  {
    id: 5, name: "Priya Patel", initials: "PP", studentId: "KOI-2025-005",
    subject: "BSYS301", program: "Bachelor of Business",
    attendance: 41, gpa: 1.5, assignments: { done: 2, total: 10 },
    risk: "HIGH", trend: "deteriorating",
    weeklyAttendance: [82, 70, 60, 52, 48, 44, 42, 41],
    email: "p.patel@student.koi.edu.au", phone: "+61 456 789 012",
    enrolled: "Jul 2024", lastLogin: "5 days ago",
    notes: ["Critical: GPA at minimum threshold", "No contact response in 2 weeks", "Welfare check recommended"],
    emailsSent: 4, tutorialSubmission: 20, forumActivity: 1,
    mlScore: 0.91, confidence: 94,
  },
  {
    id: 6, name: "Tom Nguyen", initials: "TN", studentId: "KOI-2025-006",
    subject: "BSYS301", program: "Bachelor of Business",
    attendance: 79, gpa: 3.2, assignments: { done: 8, total: 10 },
    risk: "LOW", trend: "stable",
    weeklyAttendance: [78, 80, 79, 81, 78, 79, 80, 79],
    email: "t.nguyen@student.koi.edu.au", phone: "+61 467 890 123",
    enrolled: "Feb 2024", lastLogin: "Today",
    notes: ["Improved significantly from last term", "Active participation in tutorials", "On track to pass"],
    emailsSent: 0, tutorialSubmission: 80, forumActivity: 19,
    mlScore: 0.18, confidence: 88,
  },
  {
    id: 7, name: "Aisha Rahman", initials: "AR", studentId: "KOI-2025-007",
    subject: "BSYS301", program: "Bachelor of Business",
    attendance: 62, gpa: 2.6, assignments: { done: 6, total: 10 },
    risk: "MEDIUM", trend: "stable",
    weeklyAttendance: [64, 65, 63, 62, 61, 62, 63, 62],
    email: "a.rahman@student.koi.edu.au", phone: "+61 478 901 234",
    enrolled: "Feb 2024", lastLogin: "Yesterday",
    notes: ["Stable attendance but borderline", "Submitted all group assignments", "Could benefit from mentoring"],
    emailsSent: 1, tutorialSubmission: 60, forumActivity: 11,
    mlScore: 0.47, confidence: 75,
  },
  {
    id: 8, name: "Lucas Bennett", initials: "LB", studentId: "KOI-2025-008",
    subject: "BSYS301", program: "Bachelor of Business",
    attendance: 91, gpa: 3.9, assignments: { done: 10, total: 10 },
    risk: "LOW", trend: "improving",
    weeklyAttendance: [88, 90, 89, 91, 92, 91, 90, 91],
    email: "l.bennett@student.koi.edu.au", phone: "+61 489 012 345",
    enrolled: "Feb 2023", lastLogin: "Today",
    notes: ["Consistently strong performer", "On track for HD grade", "Peer tutor candidate"],
    emailsSent: 0, tutorialSubmission: 100, forumActivity: 45,
    mlScore: 0.08, confidence: 97,
  },
  // ── BSYS201 Data Analytics ────────────────────────────────────────────
  {
    id: 9, name: "Fatima Al-Hassan", initials: "FA", studentId: "KOI-2025-009",
    subject: "BSYS201", program: "Bachelor of IT",
    attendance: 38, gpa: 1.3, assignments: { done: 1, total: 10 },
    risk: "HIGH", trend: "deteriorating",
    weeklyAttendance: [78, 65, 55, 48, 42, 40, 39, 38],
    email: "f.alhassan@student.koi.edu.au", phone: "+61 412 234 567",
    enrolled: "Feb 2025", lastLogin: "8 days ago",
    notes: ["No response to multiple emails", "Missed mid-term assessment", "International student — possible visa stress"],
    emailsSent: 5, tutorialSubmission: 10, forumActivity: 0,
    mlScore: 0.94, confidence: 96,
  },
  {
    id: 10, name: "Daniel Park", initials: "DP", studentId: "KOI-2025-010",
    subject: "BSYS201", program: "Bachelor of IT",
    attendance: 73, gpa: 3.0, assignments: { done: 7, total: 10 },
    risk: "LOW", trend: "stable",
    weeklyAttendance: [72, 74, 73, 75, 72, 73, 74, 73],
    email: "d.park@student.koi.edu.au", phone: "+61 423 345 678",
    enrolled: "Jul 2024", lastLogin: "Today",
    notes: ["On track to pass", "Good engagement in tutorials", "Minor late submissions but all completed"],
    emailsSent: 0, tutorialSubmission: 70, forumActivity: 16,
    mlScore: 0.22, confidence: 85,
  },
  {
    id: 11, name: "Chloe Martinez", initials: "CM", studentId: "KOI-2025-011",
    subject: "BSYS201", program: "Bachelor of IT",
    attendance: 55, gpa: 2.2, assignments: { done: 4, total: 10 },
    risk: "MEDIUM", trend: "stable",
    weeklyAttendance: [60, 58, 56, 55, 55, 54, 55, 55],
    email: "c.martinez@student.koi.edu.au", phone: "+61 434 456 789",
    enrolled: "Feb 2024", lastLogin: "2 days ago",
    notes: ["Attendance just above minimum threshold", "Participation is low in tutorials", "Self-reported family issues"],
    emailsSent: 2, tutorialSubmission: 40, forumActivity: 6,
    mlScore: 0.58, confidence: 77,
  },
  {
    id: 12, name: "Omar Khalid", initials: "OK", studentId: "KOI-2025-012",
    subject: "BSYS201", program: "Bachelor of IT",
    attendance: 48, gpa: 1.9, assignments: { done: 3, total: 10 },
    risk: "HIGH", trend: "stable",
    weeklyAttendance: [55, 52, 50, 49, 48, 48, 49, 48],
    email: "o.khalid@student.koi.edu.au", phone: "+61 445 567 890",
    enrolled: "Jul 2024", lastLogin: "4 days ago",
    notes: ["Below attendance threshold", "Replied to support email — citing work commitments", "Part-time employment conflict"],
    emailsSent: 2, tutorialSubmission: 30, forumActivity: 4,
    mlScore: 0.79, confidence: 87,
  },
  // ── BSYS401 Project Management ────────────────────────────────────────
  {
    id: 13, name: "Zara Ahmed", initials: "ZA", studentId: "KOI-2025-013",
    subject: "BSYS401", program: "Bachelor of Business",
    attendance: 83, gpa: 3.5, assignments: { done: 9, total: 10 },
    risk: "LOW", trend: "improving",
    weeklyAttendance: [78, 80, 82, 83, 84, 84, 83, 83],
    email: "z.ahmed@student.koi.edu.au", phone: "+61 456 678 901",
    enrolled: "Feb 2023", lastLogin: "Today",
    notes: ["Excellent attendance trend", "Group project leader", "Strong academic performance"],
    emailsSent: 0, tutorialSubmission: 90, forumActivity: 28,
    mlScore: 0.15, confidence: 92,
  },
  {
    id: 14, name: "Ryan O'Brien", initials: "RO", studentId: "KOI-2025-014",
    subject: "BSYS401", program: "Bachelor of Business",
    attendance: 61, gpa: 2.3, assignments: { done: 5, total: 10 },
    risk: "MEDIUM", trend: "deteriorating",
    weeklyAttendance: [78, 75, 70, 67, 63, 62, 61, 61],
    email: "r.obrien@student.koi.edu.au", phone: "+61 467 789 012",
    enrolled: "Feb 2024", lastLogin: "3 days ago",
    notes: ["Sharp attendance drop in last 4 weeks", "Mental health concerns raised", "Referred to student wellbeing team"],
    emailsSent: 2, tutorialSubmission: 50, forumActivity: 7,
    mlScore: 0.63, confidence: 82,
  },
  {
    id: 15, name: "Lin Wei", initials: "LW", studentId: "KOI-2025-015",
    subject: "BSYS401", program: "Master of Business",
    attendance: 35, gpa: 1.2, assignments: { done: 1, total: 8 },
    risk: "HIGH", trend: "deteriorating",
    weeklyAttendance: [72, 60, 50, 42, 38, 36, 35, 35],
    email: "l.wei@student.koi.edu.au", phone: "+61 478 890 123",
    enrolled: "Jul 2024", lastLogin: "10 days ago",
    notes: ["Critical risk — academic probation imminent", "No submission in 4 weeks", "International student — contact parent advised"],
    emailsSent: 6, tutorialSubmission: 12, forumActivity: 0,
    mlScore: 0.96, confidence: 98,
  },
  {
    id: 16, name: "Mei Tanaka", initials: "MT", studentId: "KOI-2025-016",
    subject: "BSYS401", program: "Master of Business",
    attendance: 76, gpa: 3.3, assignments: { done: 7, total: 8 },
    risk: "LOW", trend: "stable",
    weeklyAttendance: [74, 76, 77, 75, 76, 77, 76, 76],
    email: "m.tanaka@student.koi.edu.au", phone: "+61 489 901 234",
    enrolled: "Feb 2024", lastLogin: "Today",
    notes: ["Solid academic progress", "Engaged in all seminars", "One missed assignment — explained"],
    emailsSent: 0, tutorialSubmission: 87, forumActivity: 21,
    mlScore: 0.19, confidence: 90,
  },
  // ── INFO101 Info Systems ──────────────────────────────────────────────
  {
    id: 17, name: "Alex Thompson", initials: "AT", studentId: "KOI-2025-017",
    subject: "INFO101", program: "Bachelor of IT",
    attendance: 42, gpa: 1.7, assignments: { done: 2, total: 8 },
    risk: "HIGH", trend: "deteriorating",
    weeklyAttendance: [75, 68, 60, 53, 47, 44, 43, 42],
    email: "a.thompson@student.koi.edu.au", phone: "+61 412 567 890",
    enrolled: "Feb 2025", lastLogin: "6 days ago",
    notes: ["First-year student struggling to adapt", "Did not attend orientation week", "Referred to academic support services"],
    emailsSent: 3, tutorialSubmission: 25, forumActivity: 3,
    mlScore: 0.88, confidence: 91,
  },
  {
    id: 18, name: "Sophie Laurent", initials: "SL", studentId: "KOI-2025-018",
    subject: "INFO101", program: "Bachelor of IT",
    attendance: 68, gpa: 2.8, assignments: { done: 6, total: 8 },
    risk: "MEDIUM", trend: "improving",
    weeklyAttendance: [60, 62, 64, 66, 67, 68, 68, 68],
    email: "s.laurent@student.koi.edu.au", phone: "+61 423 678 901",
    enrolled: "Feb 2025", lastLogin: "Yesterday",
    notes: ["Improving trend — responded well to early intervention", "Attended study skills workshop", "Participating more in class"],
    emailsSent: 1, tutorialSubmission: 75, forumActivity: 13,
    mlScore: 0.42, confidence: 72,
  },
  {
    id: 19, name: "Carlos Rivera", initials: "CR", studentId: "KOI-2025-019",
    subject: "INFO101", program: "Bachelor of IT",
    attendance: 85, gpa: 3.6, assignments: { done: 8, total: 8 },
    risk: "LOW", trend: "stable",
    weeklyAttendance: [83, 85, 86, 84, 85, 86, 85, 85],
    email: "c.rivera@student.koi.edu.au", phone: "+61 434 789 012",
    enrolled: "Feb 2025", lastLogin: "Today",
    notes: ["Top performer in cohort", "Excellent assignment quality", "Recommended for scholarship consideration"],
    emailsSent: 0, tutorialSubmission: 100, forumActivity: 38,
    mlScore: 0.09, confidence: 96,
  },
  {
    id: 20, name: "Nina Kowalski", initials: "NK", studentId: "KOI-2025-020",
    subject: "INFO101", program: "Bachelor of IT",
    attendance: 54, gpa: 2.0, assignments: { done: 3, total: 8 },
    risk: "MEDIUM", trend: "stable",
    weeklyAttendance: [58, 56, 54, 54, 55, 54, 53, 54],
    email: "n.kowalski@student.koi.edu.au", phone: "+61 445 890 123",
    enrolled: "Feb 2025", lastLogin: "4 days ago",
    notes: ["Attendance hovering at borderline", "English is second language — additional support may help", "Attending tutoring sessions"],
    emailsSent: 1, tutorialSubmission: 37, forumActivity: 5,
    mlScore: 0.57, confidence: 76,
  },
];

// Weekly risk distribution data (Weeks 1–8 for current semester)
export const weeklyRiskData = [
  { week: "Wk 1", high: 6,  medium: 14, low: 80 },
  { week: "Wk 2", high: 7,  medium: 16, low: 77 },
  { week: "Wk 3", high: 9,  medium: 18, low: 73 },
  { week: "Wk 4", high: 10, medium: 20, low: 70 },
  { week: "Wk 5", high: 12, medium: 21, low: 67 },
  { week: "Wk 6", high: 13, medium: 22, low: 65 },
  { week: "Wk 7", high: 14, medium: 22, low: 64 },
  { week: "Wk 8", high: 14, medium: 22, low: 64 },
];

// Subject-level risk breakdown
export const subjectRiskData = [
  { subject: "BSYS301", high: 2, medium: 3, low: 3, total: 8 },
  { subject: "BSYS201", high: 2, medium: 1, low: 1, total: 4 },
  { subject: "BSYS401", high: 1, medium: 1, low: 2, total: 4 },
  { subject: "INFO101", high: 1, medium: 2, low: 1, total: 4 },
];

// Email log data
export const emailLogs = [
  { id: 1, student: "Sarah Johnson", studentId: "KOI-2025-001", subject: "BSYS301", type: "High Risk Alert", status: "Opened", sentAt: "Today, 8:02 AM", openedAt: "Today, 9:14 AM", template: "high-risk-v2" },
  { id: 2, student: "Priya Patel", studentId: "KOI-2025-005", subject: "BSYS301", type: "High Risk Alert", status: "Sent", sentAt: "Today, 8:02 AM", openedAt: "—", template: "high-risk-v2" },
  { id: 3, student: "Lin Wei", studentId: "KOI-2025-015", subject: "BSYS401", type: "Critical Risk — Welfare Check", status: "Sent", sentAt: "Today, 8:02 AM", openedAt: "—", template: "critical-welfare" },
  { id: 4, student: "Fatima Al-Hassan", studentId: "KOI-2025-009", subject: "BSYS201", type: "High Risk Alert", status: "Failed", sentAt: "Today, 8:02 AM", openedAt: "—", template: "high-risk-v2" },
  { id: 5, student: "Michael Chen", studentId: "KOI-2025-002", subject: "BSYS301", type: "Medium Risk Notice", status: "Opened", sentAt: "Yesterday, 8:00 AM", openedAt: "Yesterday, 10:22 AM", template: "medium-risk-v1" },
  { id: 6, student: "Omar Khalid", studentId: "KOI-2025-012", subject: "BSYS201", type: "Medium Risk Notice", status: "Opened", sentAt: "Yesterday, 8:00 AM", openedAt: "Yesterday, 3:45 PM", template: "medium-risk-v1" },
  { id: 7, student: "Alex Thompson", studentId: "KOI-2025-017", subject: "INFO101", type: "High Risk Alert", status: "Sent", sentAt: "2 days ago, 8:00 AM", openedAt: "—", template: "high-risk-v2" },
  { id: 8, student: "Chloe Martinez", studentId: "KOI-2025-011", subject: "BSYS201", type: "Medium Risk Notice", status: "Opened", sentAt: "3 days ago, 8:05 AM", openedAt: "3 days ago, 11:30 AM", template: "medium-risk-v1" },
  { id: 9, student: "Ryan O'Brien", studentId: "KOI-2025-014", subject: "BSYS401", type: "Medium Risk Notice", status: "Opened", sentAt: "3 days ago, 8:05 AM", openedAt: "3 days ago, 6:00 PM", template: "medium-risk-v1" },
  { id: 10, student: "Lin Wei", studentId: "KOI-2025-015", subject: "BSYS401", type: "High Risk Alert", status: "Sent", sentAt: "4 days ago, 8:00 AM", openedAt: "—", template: "high-risk-v2" },
  { id: 11, student: "Sarah Johnson", studentId: "KOI-2025-001", subject: "BSYS301", type: "Attendance Warning", status: "Opened", sentAt: "5 days ago, 8:00 AM", openedAt: "5 days ago, 2:15 PM", template: "attendance-warning" },
  { id: 12, student: "Priya Patel", studentId: "KOI-2025-005", subject: "BSYS301", type: "Attendance Warning", status: "Sent", sentAt: "5 days ago, 8:00 AM", openedAt: "—", template: "attendance-warning" },
];

export const riskConfig: Record<RiskLevel, { color: string; bg: string; border: string; label: string }> = {
  HIGH:   { color: "#E24B4A", bg: "#FEE2E2", border: "#FCA5A5", label: "High Risk" },
  MEDIUM: { color: "#EF9F27", bg: "#FEF3C7", border: "#FCD34D", label: "At Risk" },
  LOW:    { color: "#97C459", bg: "#ECFDF5", border: "#86EFAC", label: "Safe" },
};
