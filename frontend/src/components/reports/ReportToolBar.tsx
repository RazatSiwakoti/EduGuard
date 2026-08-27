import { Download, Loader2 } from "lucide-react";
import type { DashboardUnit } from "../../types/dashboard";
import type { ReportCheckpoint } from "../../types/reports";

interface ReportToolbarProps {
  units: DashboardUnit[];
  unitId: number | null;
  onUnitChange: (unitId: number) => void;

  checkpoints: ReportCheckpoint[];
  checkpointWeek: number | null;
  onWeekChange: (week: number) => void;

  onDownload: () => void;
  downloading: boolean;
  /** Disabled while there is no report to print. */
  canDownload: boolean;
}

/**
 * Unit, checkpoint, download.
 *
 * THE WEEK LIST IS NOT A FIXED 1-14 RANGE. It comes from
 * `/checkpoints`, which returns only the weeks this unit has actually
 * been analysed at. A dropdown of fourteen weeks where thirteen render
 * "no analysis has been run" is a menu of dead ends, and it invites a
 * lecturer to conclude the report is broken rather than that the
 * analysis was never run.
 *
 * When the list is empty the selector is hidden entirely rather than
 * shown disabled: there is nothing to choose between, and the report
 * below already explains why.
 */
export default function ReportToolbar({
  units,
  unitId,
  onUnitChange,
  checkpoints,
  checkpointWeek,
  onWeekChange,
  onDownload,
  downloading,
  canDownload,
}: ReportToolbarProps) {
  const selectClass =
    "rounded-xl border border-stone-300 bg-white px-3 py-2 text-sm text-stone-900 focus:border-stone-400 focus:outline-none focus:ring-1 focus:ring-stone-400";

  return (
    <div className="flex flex-wrap items-center gap-2">
      <label className="flex items-center gap-2 text-sm">
        <span className="text-stone-500">Unit</span>
        <select
          value={unitId ?? ""}
          onChange={(event) => onUnitChange(Number(event.target.value))}
          className={selectClass}
        >
          {units.map((unit) => (
            <option key={unit.id} value={unit.id}>
              {unit.unit_code} — {unit.unit_name}
            </option>
          ))}
        </select>
      </label>

      {checkpoints.length > 0 && (
        <label className="flex items-center gap-2 text-sm">
          <span className="text-stone-500">Week</span>
          <select
            value={checkpointWeek ?? ""}
            onChange={(event) => onWeekChange(Number(event.target.value))}
            className={selectClass}
          >
            {checkpoints.map((checkpoint) => (
              <option key={checkpoint.week} value={checkpoint.week}>
                Week {checkpoint.week} ({checkpoint.student_count} analysed)
              </option>
            ))}
          </select>
        </label>
      )}

      <button
        type="button"
        onClick={onDownload}
        disabled={!canDownload || downloading}
        title={
          canDownload
            ? "Downloads the same figures as this page, as a PDF"
            : "There is no report to download yet"
        }
        className="inline-flex items-center gap-2 rounded-xl bg-stone-900 px-3.5 py-2 text-sm font-medium text-white transition hover:bg-stone-800 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {downloading ? (
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
        ) : (
          <Download className="h-4 w-4" aria-hidden="true" />
        )}
        {downloading ? "Preparing…" : "Download PDF"}
      </button>
    </div>
  );
}