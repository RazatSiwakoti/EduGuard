import api from "./api";
import type { LoginRequest, LoginResponse, User } from "../types/auth";

// Calls POST /auth/login with the given credentials.
// Returns the raw token response — does not store anything itself,
// that's AuthContext's job, not this service's.
export async function login(
  credentials: LoginRequest
): Promise<LoginResponse> {
  const response = await api.post<LoginResponse>("/auth/login", credentials);
  return response.data;
}

// Calls GET /auth/me. Relies on the axios interceptor in api.ts to attach
// the JWT automatically — this function doesn't handle tokens directly.
export async function getCurrentUser(): Promise<User> {
  const response = await api.get<User>("/auth/me");
  return response.data;
}