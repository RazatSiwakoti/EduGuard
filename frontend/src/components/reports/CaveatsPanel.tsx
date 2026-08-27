import { CircleCheck, TriangleAlert } from "lucide-react";

interface CaveatsPanelProps {
  caveats: string[];
}

/**
 * The qualifications, above the figures they qualify.
 *
 * WHY THIS SITS AT THE TOP. Every other view in this project qualifies
 * itself through tooltips, amber icons and badges — things a reader
 * discovers by hovering. A report is read top to bottom and printed,
 * and the same object is rendered into a PDF that gets forwarded to a
 * course coordinator with no hover states at all.
 *
 * Putting these in a footnote would mean a reader reaches the risk
 * figures first and the disclaimer afterwards, if ever. So the panel
 * goes above the numbers, in both renderers, and the strings come from
 * the server so the two can never disagree about what to disclose.
 *
 * An empty list still renders. "No qualifications apply" is a statement
 * about the data; the section quietly vanishing would read as it having
 * been forgotten.
 */
export default function CaveatsPanel({ caveats }: CaveatsPanelProps) {
  if (caveats.length === 0) {
    return (
      <section className="rounded-2xl border border-green-200 bg-green-50/70 px-5 py-4">
        <div className="flex items-start gap-2.5">
          <CircleCheck
            className="mt-0.5 h-4 w-4 shrink-0 text-green-600"
            aria-hidden="true"
          />
          <p className="text-sm text-green-900">
            <span className="font-semibold">No qualifications apply.</span> Every
            enrolled student has been analysed on complete data, and no engine
            disagreements are outstanding.
          </p>
        </div>
      </section>
    );
  }

  return (
    <section
      className="rounded-2xl border border-orange-200 bg-orange-50/70 px-5 py-4"
      aria-labelledby="report-caveats-heading"
    >
      <h2
        id="report-caveats-heading"
        className="flex items-center gap-2 text-sm font-semibold text-orange-900"
      >
        <TriangleAlert className="h-4 w-4 text-orange-500" aria-hidden="true" />
        Read these before the figures
      </h2>

      <ul className="mt-2.5 space-y-1.5">
        {caveats.map((caveat) => (
          // The string itself is the key: the server produces one line
          // per distinct qualification, so duplicates cannot occur, and
          // an index key would reorder wrongly if the list changed.
          <li key={caveat} className="flex gap-2.5 text-sm text-orange-950">
            <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-orange-400" />
            {caveat}
          </li>
        ))}
      </ul>
    </section>
  );
}