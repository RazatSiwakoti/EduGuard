import type { AssessmentProgress } from "../../utils/studentsTable";

interface AssessmentCellProps {
  progress: AssessmentProgress;
  /**
   * Whether this student has ANY criterion data recorded at all.
   *
   * Decides whether "0 marked" is a finding or just an absence. A
   * student with attendance and tutorial data but no assessment marks
   * has genuinely missed every assessment — worth colouring. A student
   * with nothing uploaded at all has not missed anything; nobody has
   * measured them yet, and flagging that in red would invent a fact
   * about a row whose other cells all read "—".
   */
  hasAnyData: boolean;
}

/**
 * "2/3 marked" — how many of the unit's assessments this student has a
 * recorded mark for.
 *
 * THE WORD IS "MARKED", NOT "SUBMITTED", AND THAT MATTERS.
 * In `bulk_ingest` a blank cell creates no AssessmentEvent, while a
 * literal `0` creates an event scored zero. So this counts assessments
 * with a mark on record — which includes a student marked 0. Calling it
 * "submitted" would either be wrong for that student, or force us to
 * treat a mark of zero as a non-submission, which would erase a real
 * zero from the one row a lecturer most needs to act on.
 *
 * The tooltip lists every assessment with its actual mark, so a
 * lecturer seeing "Quiz 1 — 0 / 20" knows exactly what happened rather
 * than inferring it from a ratio.
 *
 * The denominator comes from the UNIT'S criteria, not the student's:
 * `DashboardStudent.criteria` omits criteria the student has no event
 * for, so counting from it would report "2 of 2" for a student missing
 * a third assessment entirely — precisely backwards.
 */
export default function AssessmentCell({ progress, hasAnyData }: AssessmentCellProps) {
  const { marked, total, averagePercent, items, totalUnknown } = progress;

  if (total === 0) {
    return (
      <span className="text-stone-400" title="This unit has no assessment criteria configured">
        —
      </span>
    );
  }

  // Nothing marked is only a finding when the student HAS been
  // measured on something. For a row with no data anywhere, red would
  // claim a missed assessment where there is simply nothing on record.
  const noneMarked = marked === 0 && hasAnyData;

  const tooltip = [
    totalUnknown
      ? `${marked} assessment${marked === 1 ? "" : "s"} marked (unit total unavailable)`
      : `${marked} of ${total} assessments marked`,
    averagePercent !== null ? `Average of marked: ${averagePercent}%` : undefined,
    "",
    ...items.map((item) =>
      item.score === null
        ? `${item.name} — no mark recorded`
        : `${item.name} — ${item.score} / ${item.maxScore}`,
    ),
  ]
    .filter((line) => line !== undefined)
    .join("\n");

  return (
    <div className="w-24" title={tooltip}>
      <div className="flex items-baseline gap-1">
        <span
          className={`text-sm font-medium tabular-nums ${
            noneMarked ? "text-red-600" : "text-stone-800"
          }`}
        >
          {marked}
          {!totalUnknown && <span className="text-stone-400">/{total}</span>}
        </span>
      </div>

      <p className="mt-0.5 text-[11px] leading-tight text-stone-400">
        {/* "marked" is load-bearing, not a space filler — see the
            component docstring. Do not shorten it to "submitted". */}
        marked
        {averagePercent !== null && (
          <span className="tabular-nums"> · {averagePercent}%</span>
        )}
      </p>

      <span className="sr-only">
        {marked} of {total} assessments marked
        {averagePercent !== null ? `, averaging ${averagePercent} percent` : ""}
      </span>
    </div>
  );
}