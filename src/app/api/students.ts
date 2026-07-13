export interface StudentOverview {
  id: number;
  name: string;
  initials: string;
  studentId: string;
  subject: string | null;
  attendance: number;
  gpa: number;
  mlScore: number;
  confidence: number;
  risk: "HIGH" | "MEDIUM" | "LOW";
  trend: string;

  assignments: {
    done: number;
    total: number;
  };
}



const API_BASE_URL = "http://127.0.0.1:8000";

export async function fetchStudentOverview(): Promise<StudentOverview[]> {
  const response = await fetch(`${API_BASE_URL}/student-overview/`);

  if (!response.ok) {
    throw new Error(
      `Failed to load students: ${response.status} ${response.statusText}`
    );
  }

  return response.json();
}