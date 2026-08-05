// Shape of the request body sent to POST /auth/login
export interface LoginRequest {
  email: string;
  password: string;
}

// Shape of the response from POST /auth/login
export interface LoginResponse {
  access_token: string;
  token_type: string;
}

// Shape of the response from GET /auth/me
// Roles are locked to these four per the project's RBAC design
export type UserRole = "student" | "lecturer" | "admin" | "super_admin";

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  last_login: string;
}