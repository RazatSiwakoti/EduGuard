import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import type { UserRole } from "../types/auth";
import { getRedirectPath } from "../utils/getRedirectPath";
import { usesLecturerSurface } from "../utils/teaching";

interface RoleRouteProps {
  allowedRoles: UserRole[];
  /**
   * Also require that this account actually uses the lecturer surface
   * — T5. A role check alone is not enough for the lecturer pages: an
   * admin with no units passes `allowedRoles={["lecturer", "admin"]}`
   * and would land on a dashboard whose every endpoint returns empty.
   */
  requireTeaching?: boolean;
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
export default function RoleRoute({
  allowedRoles,
  requireTeaching = false,
}: RoleRouteProps) {
  const { user, isLoading } = useAuth();

  if (isLoading) return null;

  // ProtectedRoute has already handled the signed-out case; this is
  // belt-and-braces in case RoleRoute is ever used somewhere else.
  if (!user) return <Navigate to="/login" replace />;

  if (!allowedRoles.includes(user.role)) {
    return <Navigate to={getRedirectPath(user)} replace />;
  }

  // Second gate, T5. Deliberately AFTER the role check so the two
  // failures stay distinguishable while debugging: the first is "wrong
  // role", this one is "right role, no units".
  //
  // getRedirectPath cannot send a rejected user back here — the only
  // account this rejects is an admin with no units, and it routes them
  // to /admin. No loop.
  if (requireTeaching && !usesLecturerSurface(user)) {
    return <Navigate to={getRedirectPath(user)} replace />;
  }

  return <Outlet />;
}