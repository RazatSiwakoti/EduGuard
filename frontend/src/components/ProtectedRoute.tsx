import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import AppShell from "./layout/AppShell";

/**
 * The authentication gate for every signed-in page.
 *
 * Converted from a wrapper-with-children into a LAYOUT ROUTE. It now
 * takes no props: React Router renders it once as the parent of every
 * protected route, and the matched child page appears through the
 * <Outlet /> inside AppShell.
 *
 * That change is what stops the header and sidebar remounting on every
 * navigation — see the note in AppShell.tsx.
 *
 * Role checks deliberately moved OUT of here and into RoleRoute. This
 * component now answers exactly one question, "is anyone signed in",
 * and nesting a RoleRoute underneath it adds "…and are they allowed
 * here" without a second copy of the shell being rendered.
 */
export default function ProtectedRoute() {
  const { user, isLoading } = useAuth();

  // Returning null rather than a spinner is intentional: AuthContext
  // resolves this in a single request on first load, and flashing a
  // loader for that long looks worse than a brief blank frame.
  if (isLoading) {
    return null;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return <AppShell />;
}
