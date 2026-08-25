import UserManagementPanel from "../components/UserManagementPanel";
import {
  useAdminsList,
  useCreateAdmin,
  useDeactivateAdmin,
  useReactivateAdmin,
  useDeleteAdmin,
} from "../hooks/useAdmins";

export default function SuperAdminDashboard() {
  return (
    <div className="min-h-screen bg-stone-50 px-6 py-8">
      <div className="mx-auto max-w-4xl">
        <h1 className="mb-6 text-xl font-semibold text-stone-900">
          Super Admin Panel
        </h1>

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