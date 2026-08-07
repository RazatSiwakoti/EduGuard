import { useState } from "react";
import { useAuth } from "../context/AuthContext";
import UserManagementPanel from "../components/UserManagementPanel";
import {
  useLecturersList,
  useCreateLecturer,
  useDeactivateLecturer,
  useReactivateLecturer,
  useDeleteLecturer,
} from "../hooks/useLecturers";

type Tab = "lecturers" | "units";

export default function AdminDashboard() {
  const [activeTab, setActiveTab] = useState<Tab>("lecturers");
  const { logout } = useAuth();

  return (
    <div className="min-h-screen bg-stone-50 px-6 py-8">
      <div className="mx-auto max-w-4xl">
        <div className="mb-6 flex items-center justify-between">
          <h1 className="text-xl font-semibold text-stone-900">Admin</h1>
          <button
            onClick={logout}
            className="rounded border border-stone-300 px-3 py-1.5 text-sm font-medium text-stone-700 transition hover:bg-stone-100"
          >
            Log out
          </button>
        </div>

        <div className="mb-6 flex gap-1 border-b border-stone-200">
          <button
            onClick={() => setActiveTab("lecturers")}
            className={`px-3 py-2 text-sm font-medium ${
              activeTab === "lecturers"
                ? "border-b-2 border-stone-900 text-stone-900"
                : "text-stone-500 hover:text-stone-700"
            }`}
          >
            Lecturers
          </button>
          <button
            onClick={() => setActiveTab("units")}
            className={`px-3 py-2 text-sm font-medium ${
              activeTab === "units"
                ? "border-b-2 border-stone-900 text-stone-900"
                : "text-stone-500 hover:text-stone-700"
            }`}
          >
            Units
          </button>
        </div>

        {activeTab === "lecturers" && (
          <UserManagementPanel
            title="Manage Lecturers"
            subtitle="Create, deactivate, and remove lecturer accounts"
            createButtonLabel="+ New Lecturer"
            emptyStateLabel="No lecturers found."
            hooks={{
              useList: useLecturersList,
              useCreate: useCreateLecturer,
              useDeactivate: useDeactivateLecturer,
              useReactivate: useReactivateLecturer,
              useDelete: useDeleteLecturer,
            }}
          />
        )}

        {activeTab === "units" && (
          <p className="text-sm text-stone-500">
            Unit management — coming next.
          </p>
        )}
      </div>
    </div>
  );
}