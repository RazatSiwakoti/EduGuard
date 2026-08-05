import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

interface ProtectedRouteProps {
  children: ReactNode;
}

// Wraps any page that requires a logged-in user.
// Redirects to /login if there's no valid session.
// Renders nothing while the session restore check is still running,
// to avoid a flash of the login redirect before we actually know
// whether the user is authenticated.
export default function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return null;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}