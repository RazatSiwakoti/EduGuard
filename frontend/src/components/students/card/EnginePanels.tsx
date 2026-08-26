import { Brain, Scale, Scale3d, ShieldCheck } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { StudentDetailResponse, StudentEngineDetail } from "../../../types/studentDetail";
import { BUCKET_LABELS } from "../../../utils/dashboardAggregations";
import { explanationPhrases, formatDateTime } from "../../../utils/studentCard";
import { BUCKET_STYLES } from "../../dashboard/chartTheme";

interface EnginePanelProps {
  title: string;
  icon: LucideIcon;
  engine: StudentEngineDetail | null;
  scoreCaption: string;
}

function EnginePanel({ title, icon: Icon, engine, scoreCaption }: EnginePanelProps) {
  if (engine === null) {
    return (
      <div className="rounded-xl border border-dashed border-stone-300 bg-stone-50 p-4">
        <p className="flex items-center gap-2 text-sm font-medium text-stone-500">
          <Icon className="h-4 w-4" aria-hidden="true" />
          {title}
        </p>
        <p className="mt-2 text-xs text-stone-500">
          No score recorded — the analysis has never completed for this student.
        </p>
      </div>
    );
  }

  const phrases = explanationPhrases(engine.explanation);
  const style = BUCKET_STYLES[engine.tier];

  return (
    <div className="rounded-xl border border-stone-200 bg-white p-4">
      <div className="flex items-start justify-between gap-3">
        <p className="flex items-center gap-2 text-sm font-medium text-stone-700">
          <Icon className="h-4 w-4 text-stone-400" aria-hidden="true" />
          {title}
        </p>

        <span
          className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${style.pill}`}
        >
          {BUCKET_LABELS[engine.tier]}
        </span>
      </div>

      <p className="mt-3 text-2xl font-semibold tabular-nums text-stone-900">
        {engine.score_kind === "confidence"
          ? `${Math.round(engine.score * 100)}%`
          : engine.score.toFixed(2)}
      </p>
      <p className="text-[11px] leading-relaxed text-stone-400">{scoreCaption}</p>

      {phrases.length > 0 && (
        <ul className="mt-3 space-y-1.5 border-t border-stone-100 pt-3">
          {phrases.map((phrase) => (
            <li key={phrase} className="flex gap-2 text-xs leading-relaxed text-stone-600">
              <span
                className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-stone-300"
                aria-hidden="true"
              />
              {phrase}
            </li>
          ))}
        </ul>
      )}

      {engine.computed_at && (
        <p className="mt-3 text-[11px] text-stone-400">
          Computed {formatDateTime(engine.computed_at)}
        </p>
      )}
    </div>
  );
}

interface EnginePanelsProps {
  detail: StudentDetailResponse;
}

export default function EnginePanels({ detail }: EnginePanelsProps) {
  const { rule, ml, requires_review, final_tier, reason } = detail;

  const agreementText = (() => {
    if (!rule || !ml) return "The analysis has not completed for this student.";

    if (requires_review) {
      return `The rule engine says ${BUCKET_LABELS[rule.tier].toLowerCase()} and the ML model says ${BUCKET_LABELS[ml.tier].toLowerCase()}. That gap is too wide to resolve automatically, so no verdict was recorded — it needs your decision.`;
    }

    if (rule.tier === ml.tier) {
      return `Both engines independently reached ${BUCKET_LABELS[rule.tier].toLowerCase()}.`;
    }

    return `The engines differed — rule engine ${BUCKET_LABELS[rule.tier].toLowerCase()}, ML model ${BUCKET_LABELS[ml.tier].toLowerCase()} — and the reconciliation rules resolved it to ${final_tier ? BUCKET_LABELS[final_tier].toLowerCase() : "no verdict"}.`;
  })();

  return (
    <section>
      <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-stone-900">
        <Scale3d className="h-4 w-4 text-stone-400" aria-hidden="true" />
        How this verdict was reached
      </h3>

      <div className="grid gap-3 sm:grid-cols-2">
        <EnginePanel
          title="Rule engine"
          icon={ShieldCheck}
          engine={rule}
          scoreCaption="Combined weighted badness across this unit's criteria. Higher is worse."
        />
        <EnginePanel
          title="ML model (SHAP)"
          icon={Brain}
          engine={ml}
          scoreCaption="The model's confidence in the tier it chose — not how at-risk the student is."
        />
      </div>

      <div
        className={`mt-3 rounded-xl border p-4 ${
          requires_review
            ? "border-violet-200 bg-violet-50"
            : "border-stone-200 bg-stone-50"
        }`}
      >
        <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-stone-500">
          <Scale className="h-3.5 w-3.5" aria-hidden="true" />
          Reconciliation
        </p>
        <p className="mt-1.5 text-sm leading-relaxed text-stone-700">{agreementText}</p>

        {reason && (
          <p className="mt-2 border-t border-stone-200 pt-2 text-xs leading-relaxed text-stone-500">
            {reason}
          </p>
        )}
      </div>
    </section>
  );
}
