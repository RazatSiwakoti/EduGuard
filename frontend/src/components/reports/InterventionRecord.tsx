import { Info } from "lucide-react";
import type { ReportInterventionSummary } from "../../types/reports";

interface InterventionRecordProps {
  intervention: ReportInterventionSummary;
}

interface StatProps {
  value: number;
  label: string;
  hint?: string;
  tone?: "default" | "warning";
}

function Stat({ value, label, hint, tone = "default" }: StatProps) {
  return (
    <div className="px-5 py-4">
      <p
        className={`text-xl font-semibold tabular-nums ${
          tone === "warning" && value > 0 ? "text-red-700" : "text-stone-900"
        }`}
      >
        {value}
      </p>
      <p className="mt-0.5 text-xs font-medium text-stone-600">{label}</p>
      {hint && <p className="mt-0.5 text-xs text-stone-400">{hint}</p>}
    </div>
  );
}

/**
 * What the lecturer DID, as distinct from what the engines found.
 *
 * This is the section that makes the document a record of an
 * intervention rather than only a diagnosis — which is the difference
 * between a report a faculty can act on and a report that only says
 * who is struggling.
 *
 * IT DEGRADES HONESTLY. When the alerts feature is not installed on a
 * deployment, this renders a statement saying so instead of a grid of
 * zeros. "0 alerts sent" and "the alerts feature is not installed" look
 * identical in a table and mean completely different things; only one
 * of them is a claim that nobody was contacted.
 */
export default function InterventionRecord({
  intervention,
}: InterventionRecordProps) {
  return (
    <section className="overflow-hidden rounded-2xl border border-stone-200 bg-white">
      <header className="border-b border-stone-200 px-5 py-4">
        <h2 className="text-base font-semibold text-stone-900">
          Intervention record
        </h2>
        <p className="mt-1 text-xs leading-relaxed text-stone-500">
          What was done, as distinct from what the engines found.{" "}
          <span className="font-medium text-stone-700">&ldquo;Sent&rdquo;</span>{" "}
          means the mail server accepted the message; it is not a read receipt.
        </p>
      </header>

      {!intervention.available ? (
        <div className="space-y-4 px-5 py-5">
          <div className="flex items-start gap-2.5 rounded-xl bg-stone-50 px-4 py-3">
            <Info
              className="mt-0.5 h-4 w-4 shrink-0 text-stone-400"
              aria-hidden="true"
            />
            <p className="text-sm text-stone-600">
              The alerts feature is not installed on this deployment, so no
              contact history can be reported.{" "}
              <span className="font-medium text-stone-800">
                This is not evidence that no students were contacted.
              </span>
            </p>
          </div>

          <div className="grid grid-cols-2 divide-x divide-stone-100 rounded-xl border border-stone-200">
            <Stat
              value={intervention.reviews_resolved}
              label="Disagreements resolved"
            />
            <Stat
              value={intervention.reviews_pending}
              label="Awaiting a decision"
              tone="warning"
            />
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-2 divide-x divide-y divide-stone-100 sm:grid-cols-4">
          <Stat value={intervention.alerts_sent} label="Alerts sent" />
          <Stat
            value={intervention.alerts_failed}
            label="Failed to send"
            tone="warning"
          />
          <Stat value={intervention.alerts_queued} label="Still queued" />
          <Stat
            value={intervention.students_contacted}
            label="Students contacted"
            // Distinct students, not messages. One student can be
            // emailed more than once over a semester, and counting
            // messages as people overstates how far the unit reached.
            hint="distinct people, not messages"
          />
          <Stat value={intervention.alerts_automatic} label="Sent automatically" />
          <Stat value={intervention.alerts_manual} label="Sent by hand" />
          <Stat
            value={intervention.reviews_resolved}
            label="Disagreements resolved"
          />
          <Stat
            value={intervention.reviews_pending}
            label="Awaiting a decision"
            tone="warning"
          />
        </div>
      )}
    </section>
  );
}