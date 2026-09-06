import api from "./api";
import type {
  LoginRequest,
  LoginResponse,
  Preferences,
  User,
} from "../types/auth";

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

export async function updateProfile(full_name: string): Promise<User> {
  const response = await api.patch<User>("/auth/me/profile", { full_name });
  return response.data;
}

export async function changePassword(
  current_password: string,
  new_password: string
): Promise<void> {
  await api.post("/auth/me/password", { current_password, new_password });
}

export async function uploadAvatar(data_url: string): Promise<User> {
  const response = await api.put<User>("/auth/me/avatar", { data_url });
  return response.data;
}

export async function deleteAvatar(): Promise<User> {
  const response = await api.delete<User>("/auth/me/avatar");
  return response.data;
}

export async function updatePreferences(
  preferences: Partial<Preferences>
): Promise<User> {
  const response = await api.patch<User>("/auth/me/preferences", preferences);
  return response.data;
}