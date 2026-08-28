import { Routes, Route, Navigate } from "react-router-dom";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import StudentsPage from "./pages/StudentsPage";
import AlertsPage from "./pages/AlertsPage";
import ReportsPage from "./pages/ReportsPage";
import SuperAdminDashboard from "./pages/SuperAdminDashboard";
import AdminDashboard from "./pages/AdminDashboard";
import AccountPage from "./pages/AccountPage";
import SettingsPage from "./pages/SettingsPage";
import ProtectedRoute from "./components/ProtectedRoute";
import RoleRoute from "./components/RoleRoute";
import UnitsPage from "./pages/UnitsPage";
import UnitWorkspace from "./pages/UnitWorkspace";
import UnitOverviewTab from "./pages/unit/UnitOverviewTab";
import UnitImportTab from "./pages/unit/UnitImportTab";
import UnitAddStudentTab from "./pages/unit/UnitAddStudentTab";


/**
 * Route table.
 *
 * Restructured in Phase 7.2 from a flat list of routes — each wrapping
 * itself in <ProtectedRoute> — into a NESTED layout.
 *
 * The old shape rebuilt the header on every single navigation, because
 * each route rendered its own copy. Now ProtectedRoute is the parent of
 * every signed-in page and renders the shell once; matched children
 * appear through its <Outlet />.
 *
 * Two levels of guard, each doing one job:
 *   ProtectedRoute — is anyone signed in? Renders the shell.
 *   RoleRoute      — is this role allowed here? Renders a bare Outlet,
 *                    so nesting it does not produce a second sidebar.
 */
function App() {
  return (
    <Routes>
      {/* Login sits outside the shell — no sidebar before sign-in. */}
      <Route path="/login" element={<Login />} />

      <Route element={<ProtectedRoute />}>
        {/* Available to every signed-in role. */}
        <Route path="/account" element={<AccountPage />} />
        <Route path="/settings" element={<SettingsPage />} />

        {/* Lecturer workspace — GATED since T5.
            It used to be ungated: any signed-in account could type
            /dashboard and get a page whose every request 403'd, with
            the sidebar as the only thing keeping them out. Now the
            surface is guarded by the same predicate that decides the
            sidebar, so the two can never disagree.

            allowedRoles includes "admin" because an admin who holds a
            unit teaches it; requireTeaching is what stops an admin who
            holds none from getting in on the role alone. */}
        <Route
          element={
            <RoleRoute allowedRoles={["lecturer", "admin"]} requireTeaching />
          }
        >
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/units" element={<UnitsPage />} />

        {/* One unit's workspace. UnitWorkspace is itself a layout: it resolves the unit, renders the header and tab bar, and the active tab appears through its own <Outlet />.

            Tabs are routes rather than useState so the back button
            steps between them, each is bookmarkable, and a refresh
            keeps your place — which matters most for the multi-step
            import wizard landing here next. */}
        <Route path="/units/:unitId" element={<UnitWorkspace />}>
          <Route index element={<UnitOverviewTab />} />
          <Route path="import" element={<UnitImportTab />} />
          <Route path="add-student" element={<UnitAddStudentTab />} />
        </Route>

        <Route path="/students" element={<StudentsPage />} />
        <Route path="/alerts" element={<AlertsPage />} />
        <Route path="/reports" element={<ReportsPage />} />
        </Route>

        {/* Role-gated sections. The nested RoleRoute adds the check
            without re-rendering the shell around it. */}
        <Route element={<RoleRoute allowedRoles={["admin"]} />}>
          <Route path="/admin" element={<AdminDashboard />} />
        </Route>

        <Route element={<RoleRoute allowedRoles={["super_admin"]} />}>
          <Route path="/super-admin" element={<SuperAdminDashboard />} />
        </Route>
      </Route>

      {/* Unknown path. Sending signed-out users to /login is correct;
          a signed-in user hitting a typo is bounced to /login too and
          then immediately redirected onward by the login page's own
          role-based redirect. */}
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}

export default App;