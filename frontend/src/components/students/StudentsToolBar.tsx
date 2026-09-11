import { Download, Eye, Mail, Users } from "lucide-react";

interface StudentsToolbarProps {
  /** Enrolments in scope — NOT distinct people. See the note below. */
  enrolmentCount: number;
  /** Distinct people behind those enrolments. */
  studentCount: number;
  unitCount: number;
  /** Echoed from the payload rather than hardcoded. */
  checkpointWeek: number;
  anonymise: boolean;
  onAnonymiseChange: (value: boolean) => void;
  selectedCount?: number;
  onSendAlerts?: () => void;
  onMarkReviewed?: () => void;
  onAddToWatchlist?: () => void;
  onExportSelected?: () => void;
}

/**
 * Page title and the (parked) bulk-email action.
 *
 * THE SUBTITLE COUNTS BOTH WAYS ON PURPOSE. A row here is an enrolment,
 * because risk is computed per unit — the same person can be high risk
 * in one unit and safe in another, and merging them would force an
 * invented "worst tier wins" figure no engine ever produced. But saying
 * "24 students" when 20 people are enrolled would be quietly wrong, so
 * the line states both whenever they differ.
 *
 * "Email All At-Risk" is rendered and DISABLED. Keeping the button
 * visible shows where the feature will live, and disabling it is
 * honest; wiring it to nothing would be worse than not shipping it.
 * Its handler belongs with the Alerts phase, which owns email.
 */
export default function StudentsToolbar({
  enrolmentCount,
  studentCount,
  unitCount,
  checkpointWeek,
  anonymise,
  onAnonymiseChange,
  selectedCount = 0,
  onSendAlerts,
  onMarkReviewed,
  onAddToWatchlist,
  onExportSelected,
}: StudentsToolbarProps) {
  const enrolmentsDifferFromPeople = enrolmentCount !== studentCount;

  return (
    <header className="mb-6 flex flex-wrap items-start justify-between gap-4">
      <div>
        <h1 className="flex items-center gap-2.5 text-2xl font-semibold tracking-tight text-stone-900">
          <Users className="h-6 w-6 text-stone-400" aria-hidden="true" />
          Student Management
        </h1>

        <p className="mt-1 text-sm text-stone-500">
          Week {checkpointWeek} checkpoint
          <span className="mx-1.5 text-stone-300">·</span>
          {enrolmentsDifferFromPeople ? (
            <>
              {enrolmentCount} enrolment{enrolmentCount === 1 ? "" : "s"} ({studentCount}{" "}
              student{studentCount === 1 ? "" : "s"})
            </>
          ) : (
            <>
              {enrolmentCount} enrolled student{enrolmentCount === 1 ? "" : "s"}
            </>
          )}
          <span className="mx-1.5 text-stone-300">·</span>
          {unitCount} subject{unitCount === 1 ? "" : "s"}
        </p>
      </div>

      <label className="flex items-center gap-2 text-sm text-stone-600" title="For sharing outside the teaching team.">
        <input type="checkbox" checked={anonymise} onChange={(event) => onAnonymiseChange(event.target.checked)} />
        Remove identifying details
      </label>
      {selectedCount > 0 && (
        <div className="flex flex-wrap items-center gap-2 rounded-xl border border-blue-100 bg-blue-50 px-3 py-2">
          <span className="mr-1 text-sm font-medium text-blue-900">{selectedCount} selected</span>
          <button type="button" onClick={onSendAlerts} className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-2 text-xs font-medium text-white"><Mail className="h-3.5 w-3.5" /> Send alerts</button>
          <button type="button" onClick={onMarkReviewed} className="inline-flex items-center gap-1.5 rounded-lg bg-stone-800 px-3 py-2 text-xs font-medium text-white"><Eye className="h-3.5 w-3.5" /> Mark reviewed</button>
          <button type="button" onClick={onAddToWatchlist} disabled title="Watchlist is not available yet" className="inline-flex cursor-not-allowed items-center gap-1.5 rounded-lg border border-stone-300 px-3 py-2 text-xs font-medium text-stone-500">Add to watchlist</button>
          <button type="button" onClick={onExportSelected} className="inline-flex items-center gap-1.5 rounded-lg border border-stone-300 px-3 py-2 text-xs font-medium text-stone-700"><Download className="h-3.5 w-3.5" /> Export selected</button>
        </div>
      )}
    </header>
  );
}