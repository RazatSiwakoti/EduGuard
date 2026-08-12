const API_BASE_URL = "http://127.0.0.1:8000";

export interface EmailLog {
  id: string;
  student: string;
  studentId: string;
  subject: string;
  type: string;
  template: string;
  status: "Opened" | "Sent" | "Failed";
  sentAt: string;
  openedAt: string;
}

export interface AlertStudent {
  id: number;
  name: string;
  initials: string;
  studentId: string;
  email: string;
  subject: string;
  risk: "HIGH" | "MEDIUM" | "LOW";
}

export interface AlertStats {
  total: number;
  opened: number;
  sent: number;
  failed: number;
}

export interface BulkSendResponse {
  success: boolean;
  message: string;
  sent_count: number;
  failed_count: number;
  skipped_count: number;
}

/**
 * Fetch email notification logs from backend
 */
export async function fetchEmailLogs(): Promise<EmailLog[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/alerts/logs`);

    if (!response.ok) {
      throw new Error(
        `Failed to load email logs: ${response.status} ${response.statusText}`
      );
    }

    return response.json();
  } catch (error) {
    console.error("Error fetching email logs:", error);
    return [];
  }
}

/**
 * Fetch pending alert queue (at-risk students to notify)
 */
export async function fetchAlertQueue(): Promise<AlertStudent[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/alerts/queue`);

    if (!response.ok) {
      throw new Error(
        `Failed to load alert queue: ${response.status} ${response.statusText}`
      );
    }

    return response.json();
  } catch (error) {
    console.error("Error fetching alert queue:", error);
    return [];
  }
}

/**
 * Fetch alert statistics
 */
export async function fetchAlertStats(): Promise<AlertStats> {
  try {
    const response = await fetch(`${API_BASE_URL}/alerts/stats`);

    if (!response.ok) {
      throw new Error(
        `Failed to load alert stats: ${response.status} ${response.statusText}`
      );
    }

    return response.json();
  } catch (error) {
    console.error("Error fetching alert stats:", error);
    return { total: 0, opened: 0, sent: 0, failed: 0 };
  }
}

/**
 * Send a single alert to a student
 */
export async function sendAlertToStudent(studentId: number): Promise<{ success: boolean; message: string }> {
  try {
    const response = await fetch(`${API_BASE_URL}/alerts/send/${studentId}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      throw new Error(
        `Failed to send alert: ${response.status} ${response.statusText}`
      );
    }

    return response.json();
  } catch (error) {
    console.error("Error sending alert:", error);
    return { success: false, message: "Failed to send alert" };
  }
}

/**
 * Send bulk alerts to all pending at-risk students
 */
export async function sendBulkAlerts(week: number = 4): Promise<BulkSendResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/alerts/send-bulk`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ week }),
    });

    if (!response.ok) {
      throw new Error(
        `Failed to send bulk alerts: ${response.status} ${response.statusText}`
      );
    }

    return response.json();
  } catch (error) {
    console.error("Error sending bulk alerts:", error);
    return {
      success: false,
      message: "Failed to send bulk alerts",
      sent_count: 0,
      failed_count: 0,
      skipped_count: 0,
    };
  }
}

/**
 * Retry failed emails
 */
export async function retryFailedAlerts(): Promise<BulkSendResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/alerts/retry-failed`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      throw new Error(
        `Failed to retry failed alerts: ${response.status} ${response.statusText}`
      );
    }

    return response.json();
  } catch (error) {
    console.error("Error retrying failed alerts:", error);
    return {
      success: false,
      message: "Failed to retry failed alerts",
      sent_count: 0,
      failed_count: 0,
      skipped_count: 0,
    };
  }
}