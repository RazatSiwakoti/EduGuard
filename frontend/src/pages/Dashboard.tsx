import { useAuth } from "../context/AuthContext";

// TEMPORARY placeholder. This is deliberately generic and gets replaced
// by the real role-specific dashboards (AdminDashboard, SuperAdminDashboard,
// etc.) as those branches are built. Its only job right now is to confirm
// the full login → token → /auth/me → protected route chain actually works.
export default function Dashboard() {
  const { user, logout } = useAuth();

  return (
    <div className="flex min-h-screen items-center justify-center bg-stone-50 px-4">
      <div className="w-full max-w-sm rounded-md border border-stone-200 bg-white p-6 text-center">
        <p className="text-sm text-stone-500">Login successful</p>
        <h1 className="mt-1 text-xl font-semibold text-stone-900">
          Welcome, {user?.full_name}
        </h1>
        <p className="mt-1 text-sm text-stone-500">Role: {user?.role}</p>
        <button
          onClick={logout}
          className="mt-6 w-full rounded border border-stone-300 py-2 text-sm font-medium text-stone-700 transition hover:bg-stone-100"
        >
          Log out
        </button>
      </div>
    </div>
  );
}