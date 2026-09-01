import {
  ArrowRight,
  CircleCheck,
  Cpu,
  RefreshCw,
  Scale,
  SlidersHorizontal,
} from "lucide-react";
import type { RiskTier } from "../../types/dashboard";
import type { ManualEntryResult } from "../../types/ingestion";
import BucketBadge from "../dashboard/BucketBadge";

interface EngineVerdictPanelProps {
  result: ManualEntryResult;
  studentName: string;
  onAddAnother: () => void;
}

/**
 * What the risk pipeline decided about this one student.
 *
 * This panel is the reason manual entry is worth building before the
 * students page: it is the only place in the product that shows BOTH
 * engines' independent verdicts side by side, for a student whose
 * numbers you just typed in yourself. Enter a student with 20%
 * attendance and no submissions, and you should watch both engines say
 * high risk — which is a far more convincing test that the pipeline
 * works than any number on a dashboard.
 *
 * The three-column layout mirrors the actual architecture: two
 * independent engines feeding a reconciliation step. Showing only the
 * final tier would hide exactly the disagreement the hybrid layer
 * exists to resolve.
 */
export default function EngineVerdictPanel({
  result,
  studentName,
  onAddAnother,
}: EngineVerdictPanelProps) {
  const analysis = result.analysis_result;
  const who = studentName || result.student_number;

  /**
   * What actually happened to the student record.
   *
   * Three genuinely different outcomes, which the old single "added"
   * message collapsed into one falsehood. Re-submitting an existing
   * student number is supported and useful — it is how you add scores
   * to someone already on file — but nothing was "added" about the
   * student themselves, and saying so made a working feature look like
   * it had silently failed.
   */
  const outcome = result.student_created
    ? {
        headline: `${who} added to the unit`,
        detail: "New student record created and enrolled.",
        tone: "created" as const,
      }
    : result.enrollment_created
      ? {
          headline: `${who} enrolled in this unit`,
          detail:
            "This student already existed on another unit. Their existing details were kept, not overwritten.",
          tone: "enrolled" as const,
        }
      : {
          headline: `${who}'s scores were updated`,
          detail:
            "This student number is already enrolled here, so no new student was created. Their new values supersede the old ones.",
          tone: "updated" as const,
        };

  // "Updated" is deliberately neutral rather than green: nothing was
  // created, and a green success banner would imply otherwise.
  const isCreation = outcome.tone !== "updated";

  // No events created means nothing was scored — every criterion was
  // left blank or opted out. Worth saying explicitly rather than
  // rendering an empty verdict panel that looks broken.
  if (!analysis) {
    return (
      <div className="rounded-lg border border-stone-200 bg-white p-6">
        <h3 className="text-sm font-semibold text-stone-900">{outcome.headline}</h3>
        <p className="mt-1.5 text-xs leading-relaxed text-stone-500">
          {outcome.detail} No scores were entered, so there was nothing to analyse —
          add their data and the risk pipeline will run.
        </p>
        <button
          type="button"
          onClick={onAddAnother}
          className="mt-4 rounded-md bg-stone-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-stone-800"
        >
          Add another student
        </button>
      </div>
    );
  }

  const agreed = analysis.rule_level === analysis.ml_level;

  return (
    <div className="space-y-4">
      <div
        className={`flex gap-3 rounded-lg border p-5 ${
          isCreation ? "border-green-200 bg-green-50" : "border-stone-200 bg-stone-50"
        }`}
      >
        {isCreation ? (
          <CircleCheck
            className="mt-0.5 h-5 w-5 shrink-0 text-green-600"
            aria-hidden="true"
          />
        ) : (
          <RefreshCw className="mt-0.5 h-5 w-5 shrink-0 text-stone-400" aria-hidden="true" />
        )}

        <div>
          <h3
            className={`text-sm font-semibold ${
              isCreation ? "text-green-900" : "text-stone-900"
            }`}
          >
            {outcome.headline}
          </h3>
          <p
            className={`mt-1 text-xs leading-relaxed ${
              isCreation ? "text-green-800" : "text-stone-600"
            }`}
          >
            {outcome.detail} {result.events_created} criterion value
            {result.events_created === 1 ? "" : "s"} stored, then scored by both engines.
          </p>
        </div>
      </div>

      <section className="rounded-lg border border-stone-200 bg-white p-5">
        <h3 className="text-sm font-semibold text-stone-900">What the engines said</h3>
        <p className="mt-0.5 text-xs text-stone-500">
          Two independent engines score every student. The hybrid layer reconciles them.
        </p>

        <div className="mt-4 grid grid-cols-1 items-stretch gap-3 sm:grid-cols-[1fr_1fr_auto_1fr]">
          <EngineCard
            icon={SlidersHorizontal}
            label="Rule engine"
            detail="Your marks and pass marks"
            tier={analysis.rule_level as RiskTier}
          />
          <EngineCard
            icon={Cpu}
            label="ML model"
            detail="Learned from training data"
            tier={analysis.ml_level as RiskTier}
          />

          <div className="hidden items-center justify-center sm:flex">
            <ArrowRight className="h-4 w-4 text-stone-300" aria-hidden="true" />
          </div>

          <div
            className={`rounded-lg border p-4 ${
              analysis.requires_review
                ? "border-violet-200 bg-violet-50"
                : "border-stone-200 bg-stone-50"
            }`}
          >
            <p className="flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wide text-stone-500">
              <Scale className="h-3.5 w-3.5" aria-hidden="true" />
              Final verdict
            </p>
            <div className="mt-2">
              <BucketBadge
                bucket={
                  analysis.requires_review || !analysis.final_tier
                    ? "needs_review"
                    : (analysis.final_tier as RiskTier)
                }
              />
            </div>
            <p className="mt-2 text-[11px] leading-relaxed text-stone-500">
              {analysis.requires_review
                ? "The engines disagreed too sharply to auto-resolve."
                : agreed
                  ? "Both engines agreed."
                  : "Reconciled from a partial disagreement."}
            </p>
          </div>
        </div>

        {/* The review case is the one that needs an explanation rather
            than just a label — a null final tier looks like a failure
            unless you know it is deliberate. */}
        {analysis.requires_review && (
          <p className="mt-4 rounded-md bg-violet-50 px-3 py-2.5 text-[11px] leading-relaxed text-violet-900">
            A safe-versus-high-risk split is never auto-resolved. This student has no
            final tier until you review them — that queue lives on the Students page.
          </p>
        )}
      </section>

      {result.warnings.length > 0 && (
        <section className="rounded-lg border border-amber-200 bg-amber-50 p-4">
          <h3 className="text-xs font-semibold text-amber-900">Warnings</h3>
          <ul className="mt-2 space-y-1">
            {result.warnings.map((warning, index) => (
              <li key={index} className="text-[11px] leading-relaxed text-amber-900">
                · {warning.message}
              </li>
            ))}
          </ul>
        </section>
      )}

      {result.errors.length > 0 && (
        <section className="rounded-lg border border-red-200 bg-red-50 p-4">
          <h3 className="text-xs font-semibold text-red-900">
            Some values were rejected
          </h3>
          <ul className="mt-2 space-y-1">
            {result.errors.map((error, index) => (
              <li key={index} className="text-[11px] leading-relaxed text-red-900">
                · {error.criteria ? `${error.criteria}: ` : ""}
                {error.reason}
              </li>
            ))}
          </ul>
        </section>
      )}

      <button
        type="button"
        onClick={onAddAnother}
        className="rounded-md bg-stone-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-stone-800"
      >
        Add another student
      </button>
    </div>
  );
}

interface EngineCardProps {
  icon: typeof Cpu;
  label: string;
  detail: string;
  tier: RiskTier;
}

/** One engine's independent verdict. */
function EngineCard({ icon: Icon, label, detail, tier }: EngineCardProps) {
  return (
    <div className="rounded-lg border border-stone-200 p-4">
      <p className="flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wide text-stone-500">
        <Icon className="h-3.5 w-3.5" aria-hidden="true" />
        {label}
      </p>
      <div className="mt-2">
        <BucketBadge bucket={tier} />
      </div>
      <p className="mt-2 text-[11px] leading-relaxed text-stone-400">{detail}</p>
    </div>
  );
}