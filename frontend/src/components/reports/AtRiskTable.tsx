import { CircleAlert, Mail, MailX, TrendingDown, UserCheck } from "lucide-react";
import type { ReportStudentRow } from "../../types/reports";
import { BUCKET_STYLES } from "../dashboard/chartTheme";
import { formatDateTime } from "../../utils/studentCard";

interface AtRiskTableProps {
  rows: ReportStudentRow[];
  /**
   * False when the alerts feature is not installed. The contact column
   * is then hidden rather than shown full of zeros, which would read as
   * "nobody was contacted" — a much stronger claim.
   */
  alertsAvailable: boolean;
}

/** Movement smaller than this is noise, not a direction. Matches the
 *  server's MOMENTUM_BAND_PP and the students table's trend column. */
const MOMENTUM_BAND_PP = 10;

/**
 * A figure, or a dash. NEVER a zero.
 *
 * A student with no attendance record has not attended zero classes —
 * nobody has measured them. Printing 0 is a claim the system cannot
 * support, and it is the difference between "this student is failing"
 * and "we have no idea how this student is doing".
 */
function Figure({
  value,
  suffix = "",
  threshold,
}: {
  value: number | null;
  suffix?: string;
  threshold?: number | null;
}) {
  if (value === null) {
    return (
      <span className="text-stone-300" title="Not recorded — not the same as zero">
        &mdash;
      </span>
    );
  }

  const below = threshold != null && value < threshold;

  return (
    <span
      className={`tabular-nums ${below ? "font-semibold text-red-700" : "text-stone-700"}`}
      title={threshold != null ? `Threshold: ${threshold}${suffix}` : undefined}
    >
      {value}
      {suffix}
    </span>
  );
}

/**
 * Every student the report says needs attention, worst first.
 *
 * WHO IS HERE. High risk, low risk, and — deliberately — the students
 * whose engines disagreed and whom nobody has decided about yet. Those
 * carry no tier at all, so a naive "filter by final_tier" would drop
 * the people who most need a human to look at them.
 *
 * WHO IS NOT. Safe students, and students who have never been analysed.
 * The second group is the dangerous omission, which is why the caveats
 * panel above states how many there are.
 *
 * The ordering is the server's, not this component's. Sorting here
 * would be a second implementation of the same rule.
 */
export default function AtRiskTable({ rows, alertsAvailable }: AtRiskTableProps) {
  return (
    <section className="overflow-hidden rounded-2xl border border-stone-200 bg-white">
      <header className="border-b border-stone-200 px-5 py-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-base font-semibold text-stone-900">
            Students requiring attention
          </h2>
          <span className="rounded-full bg-stone-100 px-2 py-0.5 text-xs font-medium tabular-nums text-stone-600">
            {rows.length} student{rows.length === 1 ? "" : "s"}
          </span>
        </div>
        <p className="mt-1 text-xs leading-relaxed text-stone-500">
          Ordered worst first. Assessment figures are percentages of each
          assessment&rsquo;s own maximum mark, not raw marks. A dash means{" "}
          <span className="font-medium text-stone-700">not recorded</span>, which
          is not the same as zero.
        </p>
      </header>

      {rows.length === 0 ? (
        <p className="px-6 py-10 text-center text-sm text-stone-500">
          No students are currently on the at-risk list for this checkpoint. Read
          this alongside the qualifications above &mdash; students who have never
          been analysed do not appear here.
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[860px] text-sm">
            <thead>
              <tr className="border-b border-stone-200 text-left text-xs font-medium text-stone-500">
                <th scope="col" className="px-5 py-2.5">
                  Student
                </th>
                <th scope="col" className="px-5 py-2.5">
                  Tier
                </th>
                <th scope="col" className="px-5 py-2.5 text-right">
                  Attendance
                </th>
                <th scope="col" className="px-5 py-2.5 text-right">
                  Tutorial
                </th>
                <th scope="col" className="px-5 py-2.5 text-right">
                  Assessments
                </th>
                <th scope="col" className="px-5 py-2.5 text-right">
                  Moodle
                </th>
                {alertsAvailable && (
                  <th scope="col" className="px-5 py-2.5 text-right">
                    Contacted
                  </th>
                )}
              </tr>
            </thead>

            <tbody className="divide-y divide-stone-100">
              {rows.map((row) => {
                // A review-pending student carries a NULL tier. Falling
                // back to needs_review keeps their row coloured and
                // labelled rather than rendering as an unstyled blank.
                const bucket = row.risk_tier ?? "needs_review";
                const declining =
                  row.attendance_trend !== null &&
                  row.attendance_trend <= -MOMENTUM_BAND_PP;

                return (
                  <tr
                    key={row.student_id}
                    className="align-top transition hover:bg-stone-50"
                  >
                    <td className="px-5 py-3">
                      <div className="flex items-start gap-2">
                        <span
                          className="mt-1.5 h-2 w-2 shrink-0 rounded-full"
                          style={{ backgroundColor: BUCKET_STYLES[bucket].fill }}
                          aria-hidden="true"
                        />
                        <div className="min-w-0">
                          <p className="font-medium text-stone-900">{row.name}</p>
                          <p className="text-xs text-stone-400">
                            {row.student_number}
                            {row.email ? (
                              <>
                                <span className="mx-1 text-stone-300">·</span>
                                {row.email}
                              </>
                            ) : (
                              // Worth saying out loud: no address means
                              // the alerts feature can never reach this
                              // student, and they are on the at-risk list.
                              <>
                                <span className="mx-1 text-stone-300">·</span>
                                <span className="inline-flex items-center gap-1 text-amber-700">
                                  <MailX className="h-3 w-3" aria-hidden="true" />
                                  no email on record
                                </span>
                              </>
                            )}
                          </p>

                          <div className="mt-1 flex flex-wrap gap-x-2.5 gap-y-1 text-xs">
                            {row.requires_review && (
                              <span className="inline-flex items-center gap-1 text-violet-700">
                                <CircleAlert className="h-3 w-3" aria-hidden="true" />
                                awaiting your decision
                              </span>
                            )}
                            {row.decided_by_lecturer && (
                              <span
                                className="inline-flex items-center gap-1 text-stone-500"
                                title="A human resolved the engine disagreement behind this tier"
                              >
                                <UserCheck className="h-3 w-3" aria-hidden="true" />
                                decided by {row.reviewer_name ?? "a lecturer"}
                              </span>
                            )}
                            {row.is_incomplete && (
                              <span
                                className="inline-flex items-center gap-1 text-amber-700"
                                title="An engine flagged missing inputs — read these figures with caution"
                              >
                                <CircleAlert className="h-3 w-3" aria-hidden="true" />
                                incomplete data
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    </td>

                    <td className="px-5 py-3">
                      <span
                        className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${BUCKET_STYLES[bucket].pill}`}
                      >
                        {row.risk_label}
                      </span>
                    </td>

                    <td className="px-5 py-3 text-right">
                      <Figure
                        value={row.attendance_pct}
                        suffix="%"
                        threshold={row.attendance_threshold}
                      />
                      {row.attendance_trend !== null && (
                        <p
                          className={`mt-0.5 text-xs tabular-nums ${
                            declining ? "text-red-600" : "text-stone-400"
                          }`}
                        >
                          {declining && (
                            <TrendingDown
                              className="mr-0.5 inline h-3 w-3"
                              aria-hidden="true"
                            />
                          )}
                          {row.attendance_trend > 0 ? "+" : ""}
                          {row.attendance_trend} pp
                        </p>
                      )}
                    </td>

                    <td className="px-5 py-3 text-right">
                      <Figure
                        value={row.tutorial_pct}
                        suffix="%"
                        threshold={row.tutorial_threshold}
                      />
                    </td>

                    <td className="px-5 py-3 text-right">
                      <Figure value={row.assessment_avg_pct} suffix="%" />
                      <p className="mt-0.5 text-xs text-stone-400 tabular-nums">
                        {/* "Marked", not "submitted": a blank cell
                            creates no event while a literal 0 creates
                            one scored zero. */}
                        {row.assessments_marked} of {row.assessments_total} marked
                      </p>
                    </td>

                    <td className="px-5 py-3 text-right">
                      <Figure
                        value={row.moodle_logins}
                        threshold={row.moodle_threshold}
                      />
                    </td>

                    {alertsAvailable && (
                      <td className="px-5 py-3 text-right">
                        {row.alerts_sent === 0 ? (
                          <span className="text-xs text-stone-400">
                            not contacted
                          </span>
                        ) : (
                          <>
                            <span className="inline-flex items-center gap-1 text-xs font-medium text-stone-700">
                              <Mail className="h-3 w-3" aria-hidden="true" />
                              {row.alerts_sent}
                            </span>
                            {row.last_alert_at && (
                              <p className="mt-0.5 text-xs text-stone-400">
                                {formatDateTime(row.last_alert_at)}
                              </p>
                            )}
                          </>
                        )}
                      </td>
                    )}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}