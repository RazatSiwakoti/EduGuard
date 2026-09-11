import { useOutletContext } from "react-router-dom";
import { Upload } from "lucide-react";
import type { UnitTabContext } from "../UnitWorkspace";
import { useUnitCriteria } from "../../hooks/useLecturerUnits";
import ImportWizard from "../../components/import/ImportWizard";

/**
 * The Import Data tab.
 *
 * Thin on purpose: it resolves the unit's criteria and hands them to
 * the wizard. The criteria have to be loaded HERE rather than inside
 * the wizard because the wizard pre-fills its column guesses the moment
 * a file is read, and a criteria list still in flight at that moment
 * would produce an empty mapping the lecturer then has to fill in by
 * hand.
 */
export default function UnitImportTab() {
  const { unit } = useOutletContext<UnitTabContext>();
  const { data: criteria, isLoading, isError } = useUnitCriteria(unit.id);

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-4">
        <div className="h-6 w-48 rounded bg-stone-200" />
        <div className="h-48 rounded-lg bg-stone-200" />
      </div>
    );
  }

  if (isError || !criteria) {
    return (
      <div className="rounded-lg border border-stone-200 bg-white p-8 text-center">
        <p className="text-sm text-stone-500">
          Couldn't load this unit's criteria, so there's nothing to map columns to yet.
        </p>
      </div>
    );
  }

  return (
    <div>
      <header className="mb-6">
        <h2 className="flex items-center gap-2 text-sm font-semibold text-stone-900">
          <Upload className="h-4 w-4 text-stone-400" aria-hidden="true" />
          Import cohort data
        </h2>
        <p className="mt-1 text-xs leading-relaxed text-stone-500">
          Upload a spreadsheet and map its columns to {unit.unit_code}'s criteria.
          Nothing is stored until you confirm at the final step.
        </p>
      </header>

      <ImportWizard
        unitId={unit.id}
        unitCode={unit.unit_code}
        criteria={criteria}
      />
    </div>
  );
}