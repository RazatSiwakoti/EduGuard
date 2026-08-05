import axios from "axios";

// Single shared axios instance for the whole app.
// Every resource-specific service file (authService.ts, studentService.ts, etc.)
// imports THIS instance instead of calling axios directly — keeps the base URL
// and auth header logic defined in exactly one place.
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Runs before every outgoing request.
// If a JWT is stored, attach it as a Bearer token automatically —
// so individual service functions never have to think about auth headers.
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default api;