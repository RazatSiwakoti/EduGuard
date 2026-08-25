import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import type { UserRole } from "../types/auth";
import { getRedirectPath } from "../utils/getRedirectPath";

interface RoleRouteProps {
  allowedRoles: UserRole[];
}

/**
 * Role gate, nested inside ProtectedRoute.
 *
 * Renders a bare <Outlet /> and no layout of its own, so wrapping a
 * route in this adds an authorisation check WITHOUT rendering a second
 * sidebar and header inside the first.
 *
 * A rejected user is sent to their own role's landing page rather than
 * hardcoded to /dashboard. An admin who lands on a lecturer-only URL
 * belongs on the admin panel, and getRedirectPath already owns that
 * mapping — duplicating it here would be a second source of truth.
 */
export default function RoleRoute({ allowedRoles }: RoleRouteProps) {
  const { user, isLoading } = useAuth();

  if (isLoading) return null;

  // ProtectedRoute has already handled the signed-out case; this is
  // belt-and-braces in case RoleRoute is ever used somewhere else.
  if (!user) return <Navigate to="/login" replace />;

  if (!allowedRoles.includes(user.role)) {
    return <Navigate to={getRedirectPath(user.role)} replace />;
  }

  return <Outlet />;
}
