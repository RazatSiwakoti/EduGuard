import { useState } from "react";
import UserManagementPanel from "../components/UserManagementPanel";
import UnitsPanel from "../components/UnitsPanel";
import AuditLogPanel from "../components/AuditLogPanel";
import LecturerUnitsCell from "../components/LecturerUnitsCell";
import {
  useLecturersList,
  useCreateLecturer,
  useDeactivateLecturer,
  useReactivateLecturer,
  useDeleteLecturer,
} from "../hooks/useLecturers";

type Tab = "lecturers" | "units" | "audit";

const TABS: { key: Tab; label: string }[] = [
  { key: "lecturers", label: "Lecturers" },
  { key: "units", label: "Units" },
  // Last on purpose. It is the tab an admin opens when they are checking
  // something, not the one they work in.
  { key: "audit", label: "Audit log" },
];

export default function AdminDashboard() {
  const [activeTab, setActiveTab] = useState<Tab>("lecturers");

  return (
    <div className="min-h-screen bg-stone-50 px-6 py-8">
      <div className="mx-auto max-w-5xl">
        <h1 className="mb-6 text-xl font-semibold text-stone-900">
          Admin Panel
        </h1>

        <div className="mb-6 flex gap-1 border-b border-stone-200">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`px-3 py-2 text-sm font-medium ${
                activeTab === tab.key
                  ? "border-b-2 border-stone-900 text-stone-900"
                  : "text-stone-500 hover:text-stone-700"
              }`}
            >
              {tab.label}
            </button>
          ))}
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
            extraColumns={[
              {
                header: "Teaching",
                render: (lecturer) => (
                  <LecturerUnitsCell lecturerId={lecturer.id} />
                ),
              },
            ]}
          />
        )}

        {activeTab === "units" && <UnitsPanel />}

        {activeTab === "audit" && <AuditLogPanel />}
      </div>
    </div>
  );
}