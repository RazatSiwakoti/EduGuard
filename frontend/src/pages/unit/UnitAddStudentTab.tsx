import { useOutletContext } from "react-router-dom";
import { UserPlus } from "lucide-react";
import type { UnitTabContext } from "../UnitWorkspace";
import { useUnitCriteria } from "../../hooks/useLecturerUnits";
import ManualEntryForm from "../../components/manual/ManualEntryForm";

/**
 * The Add Student tab.
 *
 * Criteria load here rather than inside the form because the form's
 * initial weekly state is built FROM them — a criteria list still in
 * flight would produce empty attendance arrays that then need patching
 * once the data lands.
 */
export default function UnitAddStudentTab() {
  const { unit } = useOutletContext<UnitTabContext>();
  const { data: criteria, isLoading, isError } = useUnitCriteria(unit.id);

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-4">
        <div className="h-6 w-48 rounded bg-stone-200" />
        <div className="h-64 rounded-lg bg-stone-200" />
      </div>
    );
  }

  if (isError || !criteria) {
    return (
      <div className="rounded-lg border border-stone-200 bg-white p-8 text-center">
        <p className="text-sm text-stone-500">
          Couldn't load this unit's criteria, so there's nothing to enter scores against.
        </p>
      </div>
    );
  }

  return (
    <div>
      <header className="mb-6">
        <h2 className="flex items-center gap-2 text-sm font-semibold text-stone-900">
          <UserPlus className="h-4 w-4 text-stone-400" aria-hidden="true" />
          Add a student to {unit.unit_code}
        </h2>
        <p className="mt-1 text-xs leading-relaxed text-stone-500">
          For a late enrolment or a correction. Saves through the same pipeline as a
          spreadsheet import, then scores the student straight away.
        </p>
      </header>

      <ManualEntryForm
        unitId={unit.id}
        unitCode={unit.unit_code}
        criteria={criteria}
      />
    </div>
  );
}