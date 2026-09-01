export const STUDENT_EMAIL_DOMAIN = "students.koi.edu.au";

export function studentEmailFor(studentNumber: string): string {
  const id = studentNumber.trim().toLowerCase();
  return id ? `${id}@${STUDENT_EMAIL_DOMAIN}` : "";
}
