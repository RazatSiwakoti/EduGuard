import {
  createContext,
  useContext,
  useState,
  useEffect,
  type ReactNode,
} from "react";
import type { User } from "../types/auth";
import { getCurrentUser } from "../services/authService";

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  login: (accessToken: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // On first app load, if a token already exists in localStorage
  // (e.g. from a previous session), try to restore that session by
  // fetching the profile. This is what keeps a user logged in across
  // a page refresh instead of being bounced back to /login every time.
  useEffect(() => {
    async function restoreSession() {
      const existingToken = localStorage.getItem("access_token");
      if (existingToken) {
        try {
          const currentUser = await getCurrentUser();
          setUser(currentUser);
        } catch {
          // Token expired or invalid — clear it and treat as logged out.
          localStorage.removeItem("access_token");
        }
      }
      setIsLoading(false);
    }
    restoreSession();
  }, []);

  // Called by the Login page after POST /auth/login succeeds.
  // Stores the token, then immediately fetches the full profile
  // (role, full_name, etc.) since the login response itself only
  // contains the token, not user details.
  async function login(accessToken: string) {
    localStorage.setItem("access_token", accessToken);
    const currentUser = await getCurrentUser();
    setUser(currentUser);
  }

  function logout() {
    localStorage.removeItem("access_token");
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

// Note: this file exports both a component (AuthProvider) and a hook
// (useAuth) — oxlint's only-export-components rule may flag this.
// It's an intentional, standard React pattern (context + its accessor
// hook belong together); the warning is expected and safe to ignore here.
export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}