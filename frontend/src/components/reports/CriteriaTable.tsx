import type { ReportCriterionSummary } from "../../types/reports";

interface CriteriaTableProps {
  criteria: ReportCriterionSummary[];
}

/**
 * The unit each category's figures are actually in.
 *
 * Without this the "Cohort avg" column silently mixes percentages with
 * a login count, and a reader comparing 59.2 against 11.8 concludes the
 * wrong thing. Assessments are a percentage because the server divides
 * each mark by its own max_score before averaging — see `_comparable_score`.
 */
const CATEGORY_UNITS: Record<string, string> = {
  attendance: "%",
  weekly_tut: "%",
  assessment: "%",
  moodle: " logins",
};

function unitOf(category: string): string {
  return CATEGORY_UNITS[category] ?? "";
}

/**
 * How the cohort is doing against each criterion category.
 *
 * WHY "% OF THRESHOLD" IS THE COMPARABLE COLUMN. The categories are not
 * comparable raw: attendance is a percentage against a threshold of 50,
 * Moodle is a login COUNT against a threshold of 10, and assessments
 * are marks out of wildly different maximums. Dividing each student's
 * value by the threshold THEY were held to puts all four on one axis
 * where 100% means "exactly at the bar".
 *
 * The server does that arithmetic, per student, before averaging. This
 * component prints it.
 */
export default function CriteriaTable({ criteria }: CriteriaTableProps) {
  return (
    <section className="overflow-hidden rounded-2xl border border-stone-200 bg-white">
      <header className="border-b border-stone-200 px-5 py-4">
        <h2 className="text-base font-semibold text-stone-900">
          Criteria performance
        </h2>
        <p className="mt-1 text-xs leading-relaxed text-stone-500">
          Categories are not comparable raw &mdash; attendance is a percentage,
          Moodle is a login count, and assessment marks are shown as a percentage
          of each assessment&rsquo;s own maximum. Each student&rsquo;s value is
          divided by the threshold <em>they</em> were held to before averaging, so{" "}
          <span className="font-medium text-stone-700">
            100% means exactly at the bar
          </span>
          .
        </p>
      </header>

      {criteria.length === 0 ? (
        <p className="px-6 py-10 text-center text-sm text-stone-500">
          No criteria on this unit have recorded data yet.
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-sm">
            <thead>
              <tr className="border-b border-stone-200 text-left text-xs font-medium text-stone-500">
                <th scope="col" className="px-5 py-2.5">
                  Category
                </th>
                <th scope="col" className="px-5 py-2.5 text-right">
                  Cohort avg
                </th>
                <th scope="col" className="px-5 py-2.5 text-right">
                  Threshold
                </th>
                <th scope="col" className="px-5 py-2.5 text-right">
                  % of threshold
                </th>
                <th scope="col" className="px-5 py-2.5 text-right">
                  Below bar
                </th>
                <th scope="col" className="px-5 py-2.5 text-right">
                  Declining
                </th>
              </tr>
            </thead>

            <tbody className="divide-y divide-stone-100">
              {criteria.map((row) => {
                const unit = unitOf(row.category);
                const below = row.percent_of_threshold < 100;

                return (
                  <tr key={row.category} className="transition hover:bg-stone-50">
                    <td className="px-5 py-3">
                      <p className="font-medium text-stone-900">{row.label}</p>
                      <p className="text-xs text-stone-400">
                        {row.sample_size} data point
                        {row.sample_size === 1 ? "" : "s"}
                      </p>
                    </td>

                    <td className="px-5 py-3 text-right tabular-nums text-stone-700">
                      {row.average_score}
                      {unit}
                    </td>
                    <td className="px-5 py-3 text-right tabular-nums text-stone-500">
                      {row.average_threshold}
                      {unit}
                    </td>

                    <td
                      className={`px-5 py-3 text-right font-semibold tabular-nums ${
                        below ? "text-red-700" : "text-green-700"
                      }`}
                    >
                      {row.percent_of_threshold}%
                    </td>

                    <td className="px-5 py-3 text-right tabular-nums text-stone-600">
                      {row.below_threshold} of {row.sample_size}
                    </td>

                    <td className="px-5 py-3 text-right tabular-nums text-stone-600">
                      {/* null, not 0. Assessments have no early/late
                          window, so "is anyone declining" is not a
                          question that can be asked of them — and a 0
                          would read as "nobody is". */}
                      {row.declining_count === null ? (
                        <span
                          className="text-stone-300"
                          title="Not applicable — this category has no early/late window"
                        >
                          &mdash;
                        </span>
                      ) : (
                        row.declining_count
                      )}
                    </td>
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