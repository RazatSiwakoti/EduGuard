import { Link } from "react-router-dom";
import { CircleAlert, CircleCheck, RotateCcw, TriangleAlert } from "lucide-react";
import type { BulkIngestionResult } from "../../types/ingestion";

interface ImportResultProps {
  result: BulkIngestionResult;
  unitId: number;
  onImportAnother: () => void;
}

/**
 * Step 5 — what actually happened.
 *
 * Deliberately not a toast. An import either fully succeeds or
 * partially succeeds, and a partial success is the interesting case: a
 * lecturer needs to know WHICH rows failed and why, not just that some
 * did. Row-level errors carry a row number and a reason, which is
 * enough to open the spreadsheet and fix it.
 *
 * Note the counting: values_stored counts individual criterion VALUES,
 * not students. One row with four mapped criteria contributes up to
 * four values. The labels here say "values" rather than "records" so
 * the numbers can't be misread as a student count.
 */
export default function ImportResult({
  result,
  unitId,
  onImportAnother,
}: ImportResultProps) {
  const analysis = result.analysis_summary;
  const cleanImport = result.rows_with_errors === 0 && result.values_failed === 0;

  return (
    <div className="space-y-4">
      <div
        className={`flex gap-3 rounded-lg border p-5 ${
          cleanImport ? "border-green-200 bg-green-50" : "border-amber-200 bg-amber-50"
        }`}
      >
        {cleanImport ? (
          <CircleCheck className="mt-0.5 h-5 w-5 shrink-0 text-green-600" aria-hidden="true" />
        ) : (
          <TriangleAlert className="mt-0.5 h-5 w-5 shrink-0 text-amber-600" aria-hidden="true" />
        )}

        <div>
          <h3
            className={`text-sm font-semibold ${
              cleanImport ? "text-green-900" : "text-amber-900"
            }`}
          >
            {cleanImport
              ? "Import completed successfully"
              : "Import completed with some problems"}
          </h3>
          <p
            className={`mt-1 text-xs leading-relaxed ${
              cleanImport ? "text-green-800" : "text-amber-900"
            }`}
          >
            {result.filename} · {result.total_rows} row
            {result.total_rows === 1 ? "" : "s"} processed
            {result.rows_with_errors > 0 && (
              <> · {result.rows_with_errors} row(s) had at least one problem</>
            )}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="Values stored" value={result.values_stored} />
        <Stat label="Values failed" value={result.values_failed} muted={result.values_failed === 0} />
        <Stat
          label="Students analysed"
          value={analysis ? analysis.succeeded : 0}
        />
        <Stat
          label="Needs review"
          value={analysis ? analysis.results.filter((r) => r.requires_review).length : 0}
        />
      </div>

      {result.incomplete_count > 0 && (
        <section className="rounded-lg border border-amber-200 bg-amber-50 p-5">
          <div className="flex gap-3">
            <CircleAlert className="mt-0.5 h-5 w-5 shrink-0 text-amber-600" aria-hidden="true" />
            <div className="min-w-0">
              <h3 className="text-sm font-semibold text-amber-900">
                {result.incomplete_count} student{result.incomplete_count === 1 ? "" : "s"} have missing data
              </h3>
              <p className="mt-1 text-xs leading-relaxed text-amber-900">
                These students were imported and will be analysed, but no risk level will be claimed for them until the gaps are filled. They appear under Needs Review.
              </p>
              <ul className="mt-3 space-y-1 text-xs text-amber-900">
                {result.incomplete_students.map((student) => (
                  <li key={student.student_number}>
                    <span className="font-medium">{student.student_number}</span> · {student.name} — {student.missing.join(", ")}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </section>
      )}

      {analysis && analysis.failed > 0 && (
        <p className="rounded-md bg-stone-50 px-4 py-3 text-xs leading-relaxed text-stone-600">
          {analysis.failed === 1
            ? "1 student was"
            : `${analysis.failed} students were`}{" "}
          imported but could not be scored. Their data is stored — running the analysis
          again once the missing criteria have data will pick them up.
        </p>
      )}

      {result.errors.length > 0 && (
        <IssueList
          title={`${result.errors.length} error${result.errors.length === 1 ? "" : "s"}`}
          tone="error"
          items={result.errors.map((error) => ({
            row: error.row,
            student: error.student_number,
            text: error.criteria ? `${error.criteria}: ${error.reason}` : error.reason,
          }))}
        />
      )}

      {result.warnings.length > 0 && (
        <IssueList
          title={`${result.warnings.length} warning${result.warnings.length === 1 ? "" : "s"}`}
          tone="warning"
          items={result.warnings.map((warning) => ({
            row: warning.row,
            student: warning.student_number,
            text: warning.message,
          }))}
        />
      )}

      <div className="flex flex-wrap gap-3 pt-1">
        <Link
          to="/dashboard"
          className="inline-flex items-center gap-2 rounded-md bg-stone-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-stone-800"
        >
          View risk dashboard
        </Link>
        <Link
          to={`/units/${unitId}`}
          className="inline-flex items-center gap-2 rounded-md border border-stone-200 bg-white px-4 py-2 text-sm font-medium text-stone-700 transition hover:bg-stone-50"
        >
          Back to unit
        </Link>
        <button
          type="button"
          onClick={onImportAnother}
          className="inline-flex items-center gap-2 rounded-md border border-stone-200 bg-white px-4 py-2 text-sm font-medium text-stone-700 transition hover:bg-stone-50"
        >
          <RotateCcw className="h-4 w-4" aria-hidden="true" />
          Import another file
        </button>
      </div>
    </div>
  );
}

function Stat({
  label,
  value,
  muted = false,
}: {
  label: string;
  value: number;
  muted?: boolean;
}) {
  return (
    <div className="rounded-lg border border-stone-200 bg-white p-4">
      <p
        className={`text-xl font-semibold leading-none ${
          muted ? "text-stone-400" : "text-stone-900"
        }`}
      >
        {value}
      </p>
      <p className="mt-1.5 text-xs text-stone-600">{label}</p>
    </div>
  );
}

interface IssueItem {
  row: number | null;
  student: string | null;
  text: string;
}

/**
 * Errors and warnings share one presentation because they are read the
 * same way: find the row, read the reason, go fix the spreadsheet.
 *
 * Capped at 50 with a count of the remainder. A file where 400 rows
 * failed has one systemic cause, and printing all 400 buries it.
 */
function IssueList({
  title,
  tone,
  items,
}: {
  title: string;
  tone: "error" | "warning";
  items: IssueItem[];
}) {
  const shown = items.slice(0, 50);
  const hidden = items.length - shown.length;
  const isError = tone === "error";

  return (
    <section className="rounded-lg border border-stone-200 bg-white">
      <header className="flex items-center gap-2 border-b border-stone-200 px-4 py-3">
        {isError ? (
          <CircleAlert className="h-4 w-4 text-red-500" aria-hidden="true" />
        ) : (
          <TriangleAlert className="h-4 w-4 text-amber-500" aria-hidden="true" />
        )}
        <h3 className="text-sm font-semibold text-stone-900">{title}</h3>
      </header>

      <ul className="max-h-72 divide-y divide-stone-100 overflow-y-auto">
        {shown.map((item, index) => (
          <li key={index} className="flex gap-3 px-4 py-2.5 text-xs">
            <span className="w-16 shrink-0 tabular-nums text-stone-400">
              {item.row !== null ? `Row ${item.row}` : "—"}
            </span>
            <span className="w-24 shrink-0 truncate text-stone-500">
              {item.student ?? ""}
            </span>
            <span className="min-w-0 text-stone-700">{item.text}</span>
          </li>
        ))}
      </ul>

      {hidden > 0 && (
        <p className="border-t border-stone-200 px-4 py-2.5 text-[11px] text-stone-400">
          {hidden} more not shown. A large number of identical problems usually has one
          cause — check the mapping for that column.
        </p>
      )}
    </section>
  );
}
