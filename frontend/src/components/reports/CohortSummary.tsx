import type { ReportBucketCount } from "../../types/reports";
import { BUCKET_STYLES } from "../dashboard/chartTheme";

interface CohortSummaryProps {
  enrolled: number;
  analysed: number;
  notAnalysed: number;
  atRiskCount: number;
  distribution: ReportBucketCount[];
}

interface TileProps {
  value: number;
  label: string;
  hint?: string;
}

function Tile({ value, label, hint }: TileProps) {
  return (
    <div className="px-5 py-4">
      <p className="text-2xl font-semibold tabular-nums text-stone-900">{value}</p>
      <p className="mt-0.5 text-xs font-medium text-stone-600">{label}</p>
      {hint && <p className="mt-0.5 text-xs text-stone-400">{hint}</p>}
    </div>
  );
}

/**
 * How the cohort splits across the risk tiers.
 *
 * THE BAR IS PROPORTIONAL TO ANALYSED STUDENTS, NOT TO EVERYONE. Every
 * percentage here comes from the server already divided that way:
 * counting students the engines never scored into the denominator would
 * quietly understate the risk rate, which is the opposite of what an
 * early-warning system should do. The not-analysed count is shown
 * beside it rather than folded in, so nothing is hidden either.
 *
 * Nothing is computed here. The counts, the percentages and the order
 * all arrive finished — the PDF renders the identical numbers.
 */
export default function CohortSummary({
  enrolled,
  analysed,
  notAnalysed,
  atRiskCount,
  distribution,
}: CohortSummaryProps) {
  // Tiers with nobody in them are dropped from the BAR (a zero-width
  // segment is invisible anyway) but kept in the TABLE below, where
  // "High Risk — 0" is a real and reassuring statement.
  const segments = distribution.filter((row) => row.count > 0);

  return (
    <section className="overflow-hidden rounded-2xl border border-stone-200 bg-white">
      <header className="border-b border-stone-200 px-5 py-4">
        <h2 className="text-base font-semibold text-stone-900">Cohort summary</h2>
      </header>

      <div className="grid grid-cols-2 divide-x divide-y divide-stone-100 sm:grid-cols-4 sm:divide-y-0">
        <Tile value={enrolled} label="Enrolled" />
        <Tile value={analysed} label="Analysed" hint="the denominator below" />
        <Tile
          value={notAnalysed}
          label="Not analysed"
          hint={notAnalysed > 0 ? "excluded from every %" : undefined}
        />
        <Tile value={atRiskCount} label="On the at-risk list" />
      </div>

      <div className="border-t border-stone-200 px-5 py-5">
        {analysed === 0 ? (
          <p className="rounded-xl bg-stone-50 px-4 py-3 text-sm text-stone-600">
            No analysis has been run for this unit at this checkpoint. The counts
            above describe enrolment only &mdash;{" "}
            <span className="font-medium text-stone-800">
              they are not evidence that no student is at risk.
            </span>
          </p>
        ) : (
          <>
            <div
              className="flex h-3 w-full overflow-hidden rounded-full bg-stone-100"
              role="img"
              aria-label={segments
                .map((row) => `${row.label}: ${row.count}`)
                .join(", ")}
            >
              {segments.map((row) => (
                <div
                  key={row.bucket}
                  className="h-full"
                  style={{
                    width: `${row.percent_of_analysed}%`,
                    backgroundColor: BUCKET_STYLES[row.bucket].fill,
                  }}
                  title={`${row.label}: ${row.count} (${row.percent_of_analysed}%)`}
                />
              ))}
            </div>

            <ul className="mt-4 grid gap-x-6 gap-y-2 sm:grid-cols-2">
              {distribution.map((row) => (
                <li
                  key={row.bucket}
                  className="flex items-center justify-between gap-3 text-sm"
                >
                  <span className="flex min-w-0 items-center gap-2">
                    {/* Colour is never the only channel: every row also
                        carries its label and its count in text. */}
                    <span
                      className="h-2.5 w-2.5 shrink-0 rounded-sm"
                      style={{ backgroundColor: BUCKET_STYLES[row.bucket].fill }}
                      aria-hidden="true"
                    />
                    <span
                      className={
                        row.count === 0 ? "text-stone-400" : "text-stone-700"
                      }
                    >
                      {row.label}
                    </span>
                  </span>
                  <span className="shrink-0 tabular-nums text-stone-500">
                    <span className="font-medium text-stone-900">{row.count}</span>
                    {/* not-analysed students are not IN the denominator,
                        so printing their share of it would be a lie. */}
                    {row.bucket !== "not_analysed" && (
                      <span className="ml-1.5 text-xs">
                        {row.percent_of_analysed}%
                      </span>
                    )}
                  </span>
                </li>
              ))}
            </ul>
          </>
        )}
      </div>
    </section>
  );
}