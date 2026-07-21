export interface DashboardSummary {
  total_students: number;
  at_risk_students: number;
  alerts_dispatched: number;
  model_accuracy: number;
}

const API_BASE_URL = "http://127.0.0.1:8000";

export async function fetchDashboardSummary(): Promise<DashboardSummary> {
  const response = await fetch(`${API_BASE_URL}/dashboard`);

  if (!response.ok) {
    throw new Error(
      `Failed to load dashboard summary: ${response.status} ${response.statusText}`
    );
  }

  return response.json();
}