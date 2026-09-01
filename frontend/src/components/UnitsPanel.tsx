import { useState } from "react";
import * as AlertDialog from "@radix-ui/react-alert-dialog";
import * as Dialog from "@radix-ui/react-dialog";
import {
  useUnitsList,
  useCreateUnit,
  useArchiveUnit,
  useReactivateUnit,
  useAssignLecturer,
  useUnassignLecturer,
} from "../hooks/useUnits";
import { useLecturersList } from "../hooks/useLecturers";
import CriteriaStatusCell from "./units/CriteriaStatusCell";
import CriteriaSetupDialog from "./units/CriteriaSetupDialog";
import EditUnitDialog from "./units/EditUnitDialog";
import type { ClassType, Unit } from "../types/unit";
import { CLASS_TYPES, TEACHING_PERIODS, UNIT_LEVELS } from "../types/unit";
import { useAuth } from "../context/AuthContext";

/** Only LA is numbered — see types/unit.ts. */
function isNumbered(type: ClassType | ""): boolean {
  return CLASS_TYPES.some((option) => option.value === type && option.numbered);
}

export default function UnitsPanel() {
  const [showInactive, setShowInactive] = useState(false);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  // INLINE EDIT, not a modal.
  //
  // A dialog for three fields hides the row being changed behind an
  // overlay, which is the one thing a coordinator wants to keep looking
  // at while they change it - "was this the LA1 or the LA2?" is a
  // question the modal covers up. Editing in place also makes it
  // obvious which row is being edited when several are near-identical,
  // which is exactly what two classes of one subject are.
  //
  // The whole draft is held rather than read from the DOM on submit:
  // the class number input has to disappear when NCLA is picked, and a
  // controlled value is the only way that stays correct.
  // The create form's class fields are controlled, so the live preview
  // below them can show the full code the coordinator is about to make.
  // Reading it back from FormData would only be possible on submit,
  // which is after the moment the preview is useful.
  const [createUnitCode, setCreateUnitCode] = useState("");
  const [createClassType, setCreateClassType] = useState<ClassType | "">("");
  const [createClassNumber, setCreateClassNumber] = useState("");
  const [editTarget, setEditTarget] = useState<Unit | null>(null);
  const [assignTarget, setAssignTarget] = useState<Unit | null>(null);
  const [archiveTargetId, setArchiveTargetId] = useState<number | null>(null);
  // The unit whose criteria are being configured (section T3). Held as
  // the whole Unit, not an id: the dialog title and the unlock
  // confirmation both need the unit CODE, and re-deriving it from the
  // list would break the moment that list refetches mid-edit.
  const [criteriaTarget, setCriteriaTarget] = useState<Unit | null>(null);

  const { data: units, isLoading, isError } = useUnitsList(showInactive);
  const { data: lecturers } = useLecturersList(false); // active lecturers only
  const { user } = useAuth();

  /**
  * The unit-holder options, T5.
   *
   * `GET /admin/lecturers` returns LECTURER accounts only, by design —
   * it is the lecturer ACCOUNT listing and widening it would hand every
   * admin a Deactivate and a Delete button pointed at their colleagues.
   +   * a unit holder and there would be no way in the browser to make it
   +   * happen: T5's entire premise, unreachable.
   +   *
   +   * Only YOURSELF, and only if you are an admin. Assigning a unit to a
   +   * DIFFERENT admin would need an admin-visible listing of admins, and
   +   * the only one that exists is Super Admin's. That is a feature with a
   +   * permission question attached, not a dropdown entry.
   +   */

  const selfHolderOption = 
    user?.role === "admin" ? (
      <optgroup label="Administrators">
        <option value={user.id}>{user.full_name} (you)</option>
      </optgroup>
   ) : null;

  const lecturerOptions = (
    <optgroup label="Lecturers">
      {lecturers?.map((l) => (
        <option key={l.id} value={l.id}>
          {l.full_name}
        </option>
      ))}
    </optgroup>
  );

  const createUnit = useCreateUnit();
  const archiveUnit = useArchiveUnit();
  const reactivateUnit = useReactivateUnit();
  const assignLecturer = useAssignLecturer();
  const unassignLecturer = useUnassignLecturer();

  function handleCreateSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const yearRaw = form.get("year") as string;
    const lecturerRaw = form.get("lecturer_id") as string;

    createUnit.mutate(
      {
        unit_code: form.get("unit_code") as string,
        unit_name: form.get("unit_name") as string,
        start_date: form.get("start_date") as string,
        year: yearRaw ? Number(yearRaw) : null,
        teaching_period: (form.get("teaching_period") as string) || null,
        level: (form.get("level") as string) || null,
        lecturer_id: lecturerRaw ? Number(lecturerRaw) : null,
        class_type: createClassType === "" ? null : createClassType,
        class_number:
          createClassType !== "" && isNumbered(createClassType) && createClassNumber !== ""
            ? Number(createClassNumber)
            : null,
      },
      {
        onSuccess: () => {
          setIsCreateOpen(false);
          setCreateUnitCode("");
          setCreateClassType("");
          setCreateClassNumber("");
        },
      }
    );
  }

  function handleAssignSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!assignTarget) return;
    const form = new FormData(event.currentTarget);
    const lecturerId = Number(form.get("lecturer_id"));

    assignLecturer.mutate(
      { id: assignTarget.id, lecturerId },
      { onSuccess: () => setAssignTarget(null) }
    );
  }

  function confirmArchive() {
    if (archiveTargetId !== null) {
      archiveUnit.mutate(archiveTargetId);
      setArchiveTargetId(null);
    }
  }

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-stone-900">
            Manage Units
          </h2>
          <p className="mt-0.5 text-sm text-stone-500">
            Create units, assign who teaches them, archive when no longer offered
          </p>
        </div>
        <button
          onClick={() => setIsCreateOpen(true)}
          className="rounded bg-stone-900 px-3 py-1.5 text-sm font-medium text-white transition hover:bg-stone-800"
        >
          + New Unit
        </button>
      </div>

      <label className="mb-3 flex items-center gap-2 text-sm text-stone-600">
        <input
          type="checkbox"
          checked={showInactive}
          onChange={(e) => setShowInactive(e.target.checked)}
          className="h-4 w-4 rounded border-stone-300"
        />
        Show archived units
      </label>

      <div className="overflow-hidden rounded-md border border-stone-200 bg-white">
        {isLoading && <p className="p-6 text-sm text-stone-500">Loading…</p>}
        {isError && (
          <p className="p-6 text-sm text-red-600">
            Failed to load units. Try refreshing.
          </p>
        )}
        {units && units.length === 0 && (
          <p className="p-6 text-sm text-stone-500">No units found.</p>
        )}
        {units && units.length > 0 && (
          <table className="w-full text-left text-sm">
            <thead className="border-b border-stone-200 bg-stone-50 text-stone-500">
              <tr>
                <th className="px-4 py-2 font-medium">Code</th>
                <th className="px-4 py-2 font-medium">Name</th>
                <th className="px-4 py-2 font-medium">Period</th>
                <th className="px-4 py-2 font-medium">Year</th>
                <th className="px-4 py-2 font-medium">Level</th>
                <th className="px-4 py-2 font-medium">Lecturer</th>
                <th className="px-4 py-2 font-medium">Enrolled</th>
                <th className="px-4 py-2 font-medium">Criteria</th>
                <th className="px-4 py-2 font-medium">Status</th>
                <th className="px-4 py-2 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {units.map((unit) => (
                <tr key={unit.id} className="border-b border-stone-100 last:border-0">
                  <td className="whitespace-nowrap px-4 py-2.5 text-stone-900">
                    <span className="font-mono text-xs font-bold text-brand">{unit.unit_code}</span>
                    {unit.class_code && (
                      <span className="ml-1.5 rounded bg-brand-wash px-1.5 py-px font-mono text-[10px] font-bold text-brand">
                        {unit.class_code}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-2.5 text-stone-900">{unit.unit_name}</td>
                  <td className="px-4 py-2.5 text-stone-500">{unit.teaching_period ?? "—"}</td>
                  <td className="px-4 py-2.5 text-stone-500">{unit.year ?? "—"}</td>
                  <td className="px-4 py-2.5 text-stone-500">{unit.level ?? "—"}</td>
                  <td className="px-4 py-2.5 text-stone-600">
                    {unit.lecturer ? unit.lecturer.full_name : "Unassigned"}
                  </td>
                  <td className="px-4 py-2.5 text-stone-600">{unit.enrolled_count}</td>
                  <td className="whitespace-nowrap px-4 py-2.5">
                    <CriteriaStatusCell unitId={unit.id} />
                  </td>
                  <td className="px-4 py-2.5">
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                        !unit.is_active
                          ? "bg-stone-100 text-stone-500"
                          : unit.status === "ASSIGNED"
                          ? "bg-green-50 text-green-700"
                          : "bg-amber-50 text-amber-700"
                      }`}
                    >
                      {!unit.is_active ? "Archived" : unit.status}
                    </span>
                  </td>
                  <td className="px-4 py-2.5">
                    <div className="flex flex-wrap gap-2">
                      <button
                        onClick={() => setCriteriaTarget(unit)}
                        className="text-xs font-medium text-stone-900 underline decoration-stone-300 underline-offset-2 hover:decoration-stone-900"
                        data-testid={`setup-criteria-${unit.id}`}
                      >
                        Set up criteria
                      </button>
                      <button
                        onClick={() => setEditTarget(unit)}
                        className="text-xs font-medium text-stone-600 hover:underline"
                      >
                        Edit
                      </button>
                      {unit.lecturer ? (
                        <button
                          onClick={() => unassignLecturer.mutate(unit.id)}
                          className="text-xs font-medium text-stone-600 hover:underline"
                        >
                          Unassign
                        </button>
                      ) : (
                        <button
                          onClick={() => setAssignTarget(unit)}
                          className="text-xs font-medium text-stone-600 hover:underline"
                        >
                          Assign
                        </button>
                      )}
                      {unit.is_active ? (
                        <button
                          onClick={() => setArchiveTargetId(unit.id)}
                          className="text-xs font-medium text-red-600 hover:underline"
                        >
                          Archive
                        </button>
                      ) : (
                        <button
                          onClick={() => reactivateUnit.mutate(unit.id)}
                          className="text-xs font-medium text-stone-600 hover:underline"
                        >
                          Reactivate
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Criteria setup (section T3). Mounted only while a unit is
          selected, so closing it discards the form state and the next
          open re-reads the shape from the server. */}
      {criteriaTarget && (
        <CriteriaSetupDialog
          unitId={criteriaTarget.id}
          unitCode={criteriaTarget.unit_code}
          unitName={criteriaTarget.unit_name}
          onOpenChange={(open) => !open && setCriteriaTarget(null)}
        />
      )}
      {editTarget && (
        <EditUnitDialog unit={editTarget} onOpenChange={(open) => !open && setEditTarget(null)} />
      )}

      {/* Create Unit modal */}
      <Dialog.Root open={isCreateOpen} onOpenChange={setIsCreateOpen}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 bg-black/30" />
          <Dialog.Content className="fixed left-1/2 top-1/2 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-md bg-white p-6 shadow-lg">
            <Dialog.Title className="text-base font-semibold text-stone-900">
              Create New Unit
            </Dialog.Title>
            <form onSubmit={handleCreateSubmit} className="mt-4 space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="mb-1 block text-sm font-medium text-stone-700">
                    Unit code
                  </label>
                  <input
                    name="unit_code"
                    required
                    value={createUnitCode}
                    onChange={(event) => setCreateUnitCode(event.target.value.toUpperCase())}
                    className="w-full rounded border border-stone-300 px-3 py-2 text-sm uppercase outline-none focus:border-stone-500"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-stone-700">
                    Year
                  </label>
                  <input
                    name="year"
                    type="number"
                    className="w-full rounded border border-stone-300 px-3 py-2 text-sm outline-none focus:border-stone-500"
                  />
                </div>
              </div>
              {/* CLASS. Two locked options and a number, never free
                  text: the vocabulary has to stay closed or every count
                  grouped by class silently under-reports. Leaving both
                  blank is valid and means "no class split", which is
                  what every existing unit is. */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="mb-1 block text-sm font-medium text-stone-700">
                    Class <span className="font-normal text-stone-400">(optional)</span>
                  </label>
                  <select
                    name="class_type"
                    value={createClassType}
                    onChange={(event) => {
                      const next = event.target.value as ClassType | "";
                      setCreateClassType(next);
                      if (!isNumbered(next)) setCreateClassNumber("");
                    }}
                    className="w-full rounded border border-stone-300 px-3 py-2 text-sm outline-none focus:border-stone-500"
                  >
                    <option value="">No class split</option>
                    {CLASS_TYPES.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </div>
                {isNumbered(createClassType) && (
                  <div>
                    <label className="mb-1 block text-sm font-medium text-stone-700">
                      Class number
                    </label>
                    <input
                      name="class_number"
                      type="number"
                      min={1}
                      max={99}
                      value={createClassNumber}
                      onChange={(event) => setCreateClassNumber(event.target.value)}
                      required
                      className="w-full rounded border border-stone-300 px-3 py-2 text-sm outline-none focus:border-stone-500"
                    />
                  </div>
                )}
              </div>
              {createClassType && (
                <p className="-mt-1 font-mono text-xs text-stone-500">
                  This unit will be{" "}
                  <span className="font-bold text-brand">
                    {createUnitCode || "CODE"}
                    {createClassType}
                    {isNumbered(createClassType) ? createClassNumber : ""}
                  </span>
                </p>
              )}

              <div>
                <label className="mb-1 block text-sm font-medium text-stone-700">
                  Unit name
                </label>
                <input
                  name="unit_name"
                  required
                  className="w-full rounded border border-stone-300 px-3 py-2 text-sm outline-none focus:border-stone-500"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="mb-1 block text-sm font-medium text-stone-700">
                    Start date
                  </label>
                  <input
                    name="start_date"
                    type="date"
                    required
                    className="w-full rounded border border-stone-300 px-3 py-2 text-sm outline-none focus:border-stone-500"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-stone-700">
                    Teaching period
                  </label>
                  <select
                    name="teaching_period"
                    required
                    defaultValue=""
                    className="w-full rounded border border-stone-300 px-3 py-2 text-sm outline-none focus:border-stone-500"
                  >
                    <option value="">Select period</option>
                    {TEACHING_PERIODS.map((period) => (
                      <option key={period} value={period}>
                        {period}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="mb-1 block text-sm font-medium text-stone-700">
                    Level
                  </label>
                  <select
                    name="level"
                    required
                    defaultValue=""
                    className="w-full rounded border border-stone-300 px-3 py-2 text-sm outline-none focus:border-stone-500"
                  >
                    <option value="">Select level</option>
                    {UNIT_LEVELS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-stone-700">
                    Lecturer (optional)
                  </label>
                  <select
                    name="lecturer_id"
                    defaultValue=""
                    className="w-full rounded border border-stone-300 px-3 py-2 text-sm outline-none focus:border-stone-500"
                  >
                    <option value="">Unassigned</option>
                    {selfHolderOption }
                    {lecturerOptions}                  
                    
                  </select>
                </div>
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
                  disabled={createUnit.isPending}
                  className="rounded bg-stone-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-stone-800 disabled:opacity-50"
                >
                  {createUnit.isPending ? "Creating…" : "Create"}
                </button>
              </div>
            </form>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>

      {/* Assign Lecturer modal */}
      <Dialog.Root
        open={assignTarget !== null}
        onOpenChange={(open) => !open && setAssignTarget(null)}
      >
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 bg-black/30" />
          <Dialog.Content className="fixed left-1/2 top-1/2 w-full max-w-sm -translate-x-1/2 -translate-y-1/2 rounded-md bg-white p-6 shadow-lg">
            <Dialog.Title className="text-base font-semibold text-stone-900">
              Assign {assignTarget?.unit_code}
            </Dialog.Title>
            <form onSubmit={handleAssignSubmit} className="mt-4 space-y-3">
              <div>
                <label className="mb-1 block text-sm font-medium text-stone-700">
                  Teaching this unit
                </label>
                <select
                  name="lecturer_id"
                  required
                  defaultValue=""
                  className="w-full rounded border border-stone-300 px-3 py-2 text-sm outline-none focus:border-stone-500"
                >
                  <option value="" disabled>
                    Select who will teach this unit
                  </option>
                  {selfHolderOption}
                  {lecturerOptions}
                </select>
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
                  disabled={assignLecturer.isPending}
                  className="rounded bg-stone-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-stone-800 disabled:opacity-50"
                >
                  {assignLecturer.isPending ? "Assigning…" : "Assign"}
                </button>
              </div>
            </form>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>

      {/* Archive confirmation */}
      <AlertDialog.Root
        open={archiveTargetId !== null}
        onOpenChange={(open) => !open && setArchiveTargetId(null)}
      >
        <AlertDialog.Portal>
          <AlertDialog.Overlay className="fixed inset-0 bg-black/30" />
          <AlertDialog.Content className="fixed left-1/2 top-1/2 w-full max-w-sm -translate-x-1/2 -translate-y-1/2 rounded-md bg-white p-6 shadow-lg">
            <AlertDialog.Title className="text-base font-semibold text-stone-900">
              Archive this unit?
            </AlertDialog.Title>
            <AlertDialog.Description className="mt-2 text-sm text-stone-500">
              The unit will be hidden from active lists but its data is kept.
              You can reactivate it later.
            </AlertDialog.Description>
            <div className="mt-4 flex justify-end gap-2">
              <AlertDialog.Cancel asChild>
                <button className="rounded border border-stone-300 px-3 py-1.5 text-sm font-medium text-stone-700 hover:bg-stone-100">
                  Cancel
                </button>
              </AlertDialog.Cancel>
              <AlertDialog.Action asChild>
                <button
                  onClick={confirmArchive}
                  className="rounded bg-red-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-red-700"
                >
                  Archive
                </button>
              </AlertDialog.Action>
            </div>
          </AlertDialog.Content>
        </AlertDialog.Portal>
      </AlertDialog.Root>
    </div>
  );
}