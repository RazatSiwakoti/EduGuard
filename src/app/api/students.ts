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
export interface StudentDetails {
  student_id: number;
  first_name: string;
  last_name: string;
  age: number | null;
  gender: string | null;
  email: string | null;
  phone: string | null;
  program: string | null;
  student_number: string;
  is_emailed: boolean;
  status_description: "HIGH" | "MEDIUM" | "LOW";
}

export async function fetchStudentDetails(
  studentId: number
): Promise<StudentDetails> {
  const response = await fetch(`${API_BASE_URL}/students/${studentId}`);

  if (!response.ok) {
    throw new Error(
      `Failed to load student details: ${response.status} ${response.statusText}`
    );
  }

  return response.json();
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