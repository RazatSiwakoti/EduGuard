import { useState } from "react";
import * as AlertDialog from "@radix-ui/react-alert-dialog";
import * as Dialog from "@radix-ui/react-dialog";
import {
  useAdminsList,
  useCreateAdmin,
  useDeactivateAdmin,
  useReactivateAdmin,
  useDeleteAdmin,
} from "../hooks/useAdmins";
import { useAuth } from "../context/AuthContext";

export default function SuperAdminDashboard() {
  const [showInactive, setShowInactive] = useState(false);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [deleteTargetId, setDeleteTargetId] = useState<number | null>(null);

  const { logout } = useAuth();
  const { data: admins, isLoading, isError } = useAdminsList(showInactive);
  const createAdmin = useCreateAdmin();
  const deactivateAdmin = useDeactivateAdmin();
  const reactivateAdmin = useReactivateAdmin();
  const deleteAdmin = useDeleteAdmin();

  function handleCreateSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    createAdmin.mutate(
      {
        email: form.get("email") as string,
        full_name: form.get("full_name") as string,
        password: form.get("password") as string,
      },
      {
        onSuccess: () => setIsCreateOpen(false),
      }
    );
  }

  function confirmDelete() {
    if (deleteTargetId !== null) {
      deleteAdmin.mutate(deleteTargetId);
      setDeleteTargetId(null);
    }
  }

  return (
    <div className="min-h-screen bg-stone-50 px-6 py-8">
      <div className="mx-auto max-w-4xl">
        {/* Header */}
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-stone-900">
              Manage Admins
            </h1>
            <p className="mt-0.5 text-sm text-stone-500">
              Create, deactivate, and remove admin accounts
            </p>
          </div>
          <button
            onClick={logout}
            className="rounded border border-stone-300 px-3 py-1.5 text-sm font-medium text-stone-700 transition hover:bg-stone-100"
          >
            Log out
          </button>
        </div>

        {/* Controls */}
        <div className="mb-4 flex items-center justify-between">
          <label className="flex items-center gap-2 text-sm text-stone-600">
            <input
              type="checkbox"
              checked={showInactive}
              onChange={(e) => setShowInactive(e.target.checked)}
              className="h-4 w-4 rounded border-stone-300"
            />
            Show inactive admins
          </label>

          <button
            onClick={() => setIsCreateOpen(true)}
            className="rounded bg-stone-900 px-3 py-1.5 text-sm font-medium text-white transition hover:bg-stone-800"
          >
            + New Admin
          </button>
        </div>

        {/* Table */}
        <div className="overflow-hidden rounded-md border border-stone-200 bg-white">
          {isLoading && (
            <p className="p-6 text-sm text-stone-500">Loading admins…</p>
          )}
          {isError && (
            <p className="p-6 text-sm text-red-600">
              Failed to load admins. Try refreshing.
            </p>
          )}
          {admins && admins.length === 0 && (
            <p className="p-6 text-sm text-stone-500">No admins found.</p>
          )}
          {admins && admins.length > 0 && (
            <table className="w-full text-left text-sm">
              <thead className="border-b border-stone-200 bg-stone-50 text-stone-500">
                <tr>
                  <th className="px-4 py-2 font-medium">Name</th>
                  <th className="px-4 py-2 font-medium">Email</th>
                  <th className="px-4 py-2 font-medium">Status</th>
                  <th className="px-4 py-2 font-medium">Last login</th>
                  <th className="px-4 py-2 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {admins.map((admin) => (
                  <tr
                    key={admin.id}
                    className="border-b border-stone-100 last:border-0"
                  >
                    <td className="px-4 py-2.5 text-stone-900">
                      {admin.full_name}
                    </td>
                    <td className="px-4 py-2.5 text-stone-600">
                      {admin.email}
                    </td>
                    <td className="px-4 py-2.5">
                      <span
                        className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                          admin.is_active
                            ? "bg-green-50 text-green-700"
                            : "bg-stone-100 text-stone-500"
                        }`}
                      >
                        {admin.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-stone-500">
                      {admin.last_login
                        ? new Date(admin.last_login).toLocaleString()
                        : "Never"}
                    </td>
                    <td className="px-4 py-2.5">
                      <div className="flex gap-2">
                        {admin.is_active ? (
                          <button
                            onClick={() => deactivateAdmin.mutate(admin.id)}
                            className="text-xs font-medium text-stone-600 hover:underline"
                          >
                            Deactivate
                          </button>
                        ) : (
                          <button
                            onClick={() => reactivateAdmin.mutate(admin.id)}
                            className="text-xs font-medium text-stone-600 hover:underline"
                          >
                            Reactivate
                          </button>
                        )}
                        <button
                          onClick={() => setDeleteTargetId(admin.id)}
                          className="text-xs font-medium text-red-600 hover:underline"
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Create Admin modal */}
      <Dialog.Root open={isCreateOpen} onOpenChange={setIsCreateOpen}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 bg-black/30" />
          <Dialog.Content className="fixed left-1/2 top-1/2 w-full max-w-sm -translate-x-1/2 -translate-y-1/2 rounded-md bg-white p-6 shadow-lg">
            <Dialog.Title className="text-base font-semibold text-stone-900">
              Create New Admin
            </Dialog.Title>
            <form onSubmit={handleCreateSubmit} className="mt-4 space-y-3">
              <div>
                <label className="mb-1 block text-sm font-medium text-stone-700">
                  Full name
                </label>
                <input
                  name="full_name"
                  required
                  className="w-full rounded border border-stone-300 px-3 py-2 text-sm outline-none focus:border-stone-500"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-stone-700">
                  Email
                </label>
                <input
                  name="email"
                  type="email"
                  required
                  className="w-full rounded border border-stone-300 px-3 py-2 text-sm outline-none focus:border-stone-500"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-stone-700">
                  Password
                </label>
                <input
                  name="password"
                  type="password"
                  required
                  minLength={8}
                  className="w-full rounded border border-stone-300 px-3 py-2 text-sm outline-none focus:border-stone-500"
                />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <Dialog.Close asChild>
                  <button
                    type="button"
                    className="rounded border border-stone-300 px-3 py-1.5 text-sm font-medium text-stone-700 hover:bg-stone-100"
                  >
                    Cancel
                  </button>
                </Dialog.Close>
                <button
                  type="submit"
                  disabled={createAdmin.isPending}
                  className="rounded bg-stone-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-stone-800 disabled:opacity-50"
                >
                  {createAdmin.isPending ? "Creating…" : "Create"}
                </button>
              </div>
            </form>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>

      {/* Delete confirmation */}
      <AlertDialog.Root
        open={deleteTargetId !== null}
        onOpenChange={(open) => !open && setDeleteTargetId(null)}
      >
        <AlertDialog.Portal>
          <AlertDialog.Overlay className="fixed inset-0 bg-black/30" />
          <AlertDialog.Content className="fixed left-1/2 top-1/2 w-full max-w-sm -translate-x-1/2 -translate-y-1/2 rounded-md bg-white p-6 shadow-lg">
            <AlertDialog.Title className="text-base font-semibold text-stone-900">
              Delete this admin?
            </AlertDialog.Title>
            <AlertDialog.Description className="mt-2 text-sm text-stone-500">
              This permanently removes the admin account. This cannot be
              undone.
            </AlertDialog.Description>
            <div className="mt-4 flex justify-end gap-2">
              <AlertDialog.Cancel asChild>
                <button className="rounded border border-stone-300 px-3 py-1.5 text-sm font-medium text-stone-700 hover:bg-stone-100">
                  Cancel
                </button>
              </AlertDialog.Cancel>
              <AlertDialog.Action asChild>
                <button
                  onClick={confirmDelete}
                  className="rounded bg-red-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-red-700"
                >
                  Delete
                </button>
              </AlertDialog.Action>
            </div>
          </AlertDialog.Content>
        </AlertDialog.Portal>
      </AlertDialog.Root>
    </div>
  );
}