import { useAuth } from "../context/AuthContext";
import UserManagementPanel from "../components/UserManagementPanel";
import {
  useAdminsList,
  useCreateAdmin,
  useDeactivateAdmin,
  useReactivateAdmin,
  useDeleteAdmin,
} from "../hooks/useAdmins";

export default function SuperAdminDashboard() {
  const { user,  logout } = useAuth();
   return (
    <div className="min-h-screen bg-stone-50 px-6 py-8">
      <div className="mx-auto max-w-4xl">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <p className="text-sm text-stone-500">{user?.full_name}</p>
            <h1 className="text-xl font-semibold text-stone-900">
              Super Admin Panel
            </h1>
          </div>
          <button
            onClick={logout}
            className="rounded border border-stone-300 px-3 py-1.5 text-sm font-medium text-stone-700 transition hover:bg-stone-100"
          >
            Log out
          </button>
        </div>

        <UserManagementPanel
          title="Manage Admins"
          subtitle="Create, deactivate, and remove admin accounts"
          createButtonLabel="+ New Admin"
          emptyStateLabel="No admins found."
          hooks={{
            useList: useAdminsList,
            useCreate: useCreateAdmin,
            useDeactivate: useDeactivateAdmin,
            useReactivate: useReactivateAdmin,
            useDelete: useDeleteAdmin,
          }}
        />
      </div>
    </div>
  );
}