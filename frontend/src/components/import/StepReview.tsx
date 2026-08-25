import { Check, CircleAlert, FileSpreadsheet } from "lucide-react";
import type { Criterion } from "../../types/criteria";
import { CATEGORY_COLUMN_COUNT } from "../../types/criteria";
import type { FilePreviewResult, IdentityMapping } from "../../types/ingestion";

interface StepReviewProps {
  preview: FilePreviewResult;
  identity: IdentityMapping;
  criteria: Criterion[];
  singleMap: Record<number, string>;
  weeklyMap: Record<number, string[]>;
  /** Blocking problems — submit stays disabled while any exist. */
  problems: string[];
}

/**
 * Step 4 — confirm before anything is written.
 *
 * The last point at which this is reversible. Once submitted the
 * backend inserts AssessmentEvent rows, and those are immutable by
 * design: a correction is a new row, never an edit. So a wrong mapping
 * cannot be undone, only superseded by a corrected re-import.
 *
 * That is why this step restates every decision in plain language
 * rather than just showing a Submit button.
 */
export default function StepReview({
  preview,
  identity,
  criteria,
  singleMap,
  weeklyMap,
  problems,
}: StepReviewProps) {
  const identityRows: [string, string][] = [
    ["Student number", identity.student_number_col],
    ["Full name", identity.name_col],
    ["Email", identity.email_col],
    ["Program", identity.program_col],
    ["Gender", identity.gender_col],
    ["Age", identity.age_col],
  ];

  const mapped = criteria.filter((criterion) => {
    const columnCount = criterion.category
      ? CATEGORY_COLUMN_COUNT[criterion.category]
      : null;

    return columnCount === null
      ? Boolean(singleMap[criterion.id])
      : (weeklyMap[criterion.id] ?? []).filter(Boolean).length === columnCount;
  });

  const skipped = criteria.filter(
    (criterion) => criterion.enabled && !mapped.includes(criterion),
  );

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-lg border border-stone-200 bg-white px-4 py-3">
        <FileSpreadsheet className="h-4 w-4 text-stone-400" aria-hidden="true" />
        <span className="text-sm font-medium text-stone-900">{preview.filename}</span>
        <span className="text-xs text-stone-500">
          {preview.total_rows} row{preview.total_rows === 1 ? "" : "s"} will be processed
        </span>
      </div>

      <section className="rounded-lg border border-stone-200 bg-white p-5">
        <h3 className="text-sm font-semibold text-stone-900">Student identity</h3>
        <dl className="mt-3 space-y-1.5">
          {identityRows.map(([label, column]) => (
            <div key={label} className="flex items-baseline gap-3 text-xs">
              <dt className="w-32 shrink-0 text-stone-500">{label}</dt>
              <dd className={column ? "text-stone-900" : "text-stone-400"}>
                {column || "not mapped"}
              </dd>
            </div>
          ))}
        </dl>
      </section>

      <section className="rounded-lg border border-stone-200 bg-white p-5">
        <h3 className="text-sm font-semibold text-stone-900">
          Criteria being imported
        </h3>

        {mapped.length === 0 ? (
          <p className="mt-3 text-xs text-stone-500">
            None mapped — students would be created and enrolled, but with no scores to
            analyse.
          </p>
        ) : (
          <ul className="mt-3 space-y-2">
            {mapped.map((criterion) => {
              const columnCount = criterion.category
                ? CATEGORY_COLUMN_COUNT[criterion.category]
                : null;
              const source =
                columnCount === null
                  ? singleMap[criterion.id]
                  : (weeklyMap[criterion.id] ?? []).join(" → ");

              return (
                <li key={criterion.id} className="flex gap-2.5 text-xs">
                  <Check
                    className="mt-0.5 h-3.5 w-3.5 shrink-0 text-green-600"
                    aria-hidden="true"
                  />
                  <span className="min-w-0">
                    <span className="font-medium text-stone-900">{criterion.name}</span>
                    <span className="ml-2 break-words text-stone-500">{source}</span>
                  </span>
                </li>
              );
            })}
          </ul>
        )}

        {/* An unmapped criterion is not an error, but it IS worth
            stating: those students end up with a score the engines will
            flag as incomplete. */}
        {skipped.length > 0 && (
          <p className="mt-4 border-t border-stone-100 pt-3 text-[11px] leading-relaxed text-stone-500">
            Not mapped: {skipped.map((c) => c.name).join(", ")}. Students will be scored
            without these, and flagged as having incomplete data.
          </p>
        )}
      </section>

      {problems.length > 0 && (
        <div className="flex gap-3 rounded-lg border border-red-200 bg-red-50 p-4">
          <CircleAlert
            className="mt-0.5 h-4 w-4 shrink-0 text-red-600"
            aria-hidden="true"
          />
          <div className="text-xs leading-relaxed text-red-900">
            <p className="font-medium">Fix these before importing</p>
            <ul className="mt-1.5 space-y-1">
              {problems.map((problem) => (
                <li key={problem}>· {problem}</li>
              ))}
            </ul>
          </div>
        </div>
      )}

      <p className="text-[11px] leading-relaxed text-stone-400">
        On import, risk analysis runs automatically for every student whose data was
        stored. Imported rows cannot be edited afterwards — a correction is a fresh
        import, which supersedes the old values rather than overwriting them.
      </p>
    </div>
  );
}
