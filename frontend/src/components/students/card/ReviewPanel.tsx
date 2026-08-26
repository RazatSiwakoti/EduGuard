import { useState } from "react";
import {
  Check,
  History,
  Loader2,
  Scale,
  TriangleAlert,
  UserCheck,
} from "lucide-react";
import type { RiskTier } from "../../../types/dashboard";
import type { StudentDetailResponse } from "../../../types/studentDetail";
import { BUCKET_LABELS, TIER_ORDER } from "../../../utils/dashboardAggregations";
import { formatDateTime } from "../../../utils/studentCard";
import { BUCKET_STYLES } from "../../dashboard/chartTheme";

interface ReviewPanelProps {
  detail: StudentDetailResponse;
  onSubmit: (decision: RiskTier, comment: string) => void;
  isSubmitting: boolean;
  isError: boolean;
  error: unknown;
}

/**
 * Resolving an engine disagreement — the only decision in this entire
 * application that a human, and only a human, can make.
 *
 * IT LIVES IN THE CARD ON PURPOSE. Every other placement was worse: an
 * inline control on the students table would let a lecturer set a
 * student's risk tier from a row, without ever seeing why the two
 * engines disagreed; a dedicated queue page optimises for clearing
 * fifteen quickly, which is exactly the behaviour this decision should
 * not have. Here the choice sits directly beneath both engines, their
 * reasoning and the weekly charts. Slower per student, and that is the
 * feature.
 *
 * For the same reason there is no one-click-per-tier: picking a tier
 * arms the decision, a separate button commits it. A stray click here
 * changes what every other screen says about this person.
 *
 * Renders in three states:
 *   - needs a decision, none on record   → the prompt
 *   - needs a decision, a PRIOR one exists that no longer applies
 *                                        → the prompt, plus what moved
 *   - already resolved by a human        → who decided what, and when,
 *     including a decision CARRIED FORWARD from an earlier run
 */
export default function ReviewPanel({
  detail,
  onSubmit,
  isSubmitting,
  isError,
  error,
}: ReviewPanelProps) {
  const [decision, setDecision] = useState<RiskTier | null>(null);
  const [comment, setComment] = useState("");

  const { requires_review, applied_review_id, review_history, rule, ml } = detail;

  const applied =
    applied_review_id === null
      ? null
      : (review_history.find((entry) => entry.id === applied_review_id) ?? null);

  // The most recent decision, whether or not it still applies. When the
  // verdict needs review AND one of these exists, the engines have moved
  // since it was made.
  const latest = review_history[0] ?? null;
  const stale = requires_review && latest !== null;

  // Nothing to show: the engines agreed and no human has ever been
  // involved. Rendering an empty "Review" heading would imply there is
  // something here to do.
  if (!requires_review && applied === null) return null;

  function commit() {
    if (decision !== null) onSubmit(decision, comment);
  }

  return (
    <section>
      <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-stone-900">
        <Scale className="h-4 w-4 text-stone-400" aria-hidden="true" />
        {requires_review ? "Your decision is needed" : "Resolved by a lecturer"}
      </h3>

      {/* ------------------------------------------------------------ */}
      {/* Already resolved                                              */}
      {/* ------------------------------------------------------------ */}
      {applied && (
        <div className="rounded-xl border border-stone-200 bg-white p-4">
          <div className="flex flex-wrap items-center gap-2">
            <UserCheck className="h-4 w-4 shrink-0 text-stone-400" aria-hidden="true" />
            <span className="text-sm text-stone-700">
              {applied.reviewer_name ?? "A lecturer"} resolved this as
            </span>
            <span
              className={`rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${BUCKET_STYLES[applied.decision].pill}`}
            >
              {BUCKET_LABELS[applied.decision]}
            </span>
          </div>

          <p className="mt-1.5 text-xs text-stone-500">
            {formatDateTime(applied.created_at)}
            {/* The engines were re-run and still disagree the same way,
                so this decision was applied automatically. Saying so
                stops a carried-forward judgement from reading as an
                ordinary engine result — a human still stands behind
                this tier, and the page should not pretend otherwise. */}
            {rule &&
              ml &&
              applied.rule_tier === rule.tier &&
              applied.ml_tier === ml.tier && (
                <>
                  {" · "}carried forward to the latest analysis, because both engines
                  still say the same thing
                </>
              )}
          </p>

          {applied.comment && (
            <p className="mt-2.5 border-t border-stone-100 pt-2.5 text-sm italic leading-relaxed text-stone-600">
              “{applied.comment}”
            </p>
          )}
        </div>
      )}

      {/* ------------------------------------------------------------ */}
      {/* A prior decision that no longer applies                       */}
      {/* ------------------------------------------------------------ */}
      {stale && latest && (
        <div className="mb-3 rounded-xl border border-amber-200 bg-amber-50/70 p-4">
          <p className="flex items-center gap-2 text-sm font-medium text-amber-900">
            <TriangleAlert className="h-4 w-4 shrink-0" aria-hidden="true" />
            The disagreement has changed since you last decided
          </p>

          {/* NAMES WHAT MOVED. Silently re-asking a lecturer who already
              decided this student reads as the system losing their work —
              which, before reviews were made to survive re-analysis, is
              exactly what used to happen. */}
          <p className="mt-1.5 text-xs leading-relaxed text-amber-900/90">
            You resolved this as{" "}
            <span className="font-medium">{BUCKET_LABELS[latest.decision]}</span> on{" "}
            {formatDateTime(latest.created_at)}, when the rule engine said{" "}
            <span className="font-medium">{BUCKET_LABELS[latest.rule_tier]}</span> and the
            model said <span className="font-medium">{BUCKET_LABELS[latest.ml_tier]}</span>.
            {rule && ml && (
              <>
                {" "}
                They now say <span className="font-medium">{BUCKET_LABELS[rule.tier]}</span>{" "}
                and <span className="font-medium">{BUCKET_LABELS[ml.tier]}</span>, so that
                decision was not carried forward.
              </>
            )}
          </p>
        </div>
      )}

      {/* ------------------------------------------------------------ */}
      {/* The decision itself                                           */}
      {/* ------------------------------------------------------------ */}
      {requires_review && (
        <div className="rounded-xl border border-violet-200 bg-violet-50/50 p-4">
          <p className="text-sm leading-relaxed text-stone-700">
            The two engines disagreed too widely to reconcile automatically, so no
            verdict was recorded. Which tier should this student sit in?
          </p>

          <div className="mt-3 flex flex-wrap gap-2">
            {TIER_ORDER.map((tier) => {
              const selected = decision === tier;
              return (
                <button
                  key={tier}
                  type="button"
                  onClick={() => setDecision(tier)}
                  aria-pressed={selected}
                  className={`rounded-xl px-4 py-2 text-sm font-medium ring-1 ring-inset transition ${
                    selected
                      ? "bg-stone-900 text-white ring-stone-900"
                      : `${BUCKET_STYLES[tier].pill} hover:brightness-95`
                  }`}
                >
                  {BUCKET_LABELS[tier]}
                </button>
              );
            })}
          </div>

          <textarea
            value={comment}
            onChange={(event) => setComment(event.target.value)}
            rows={2}
            placeholder="Why? (optional — e.g. approved leave, so the attendance figure is misleading)"
            aria-label="Reason for this decision"
            className="mt-3 w-full resize-y rounded-xl border border-stone-200 bg-white p-3 text-sm leading-relaxed text-stone-800 placeholder:text-stone-400 focus:border-stone-400 focus:outline-none focus:ring-2 focus:ring-stone-200"
          />

          <div className="mt-2.5 flex flex-wrap items-center justify-between gap-2">
            <p className="text-[11px] leading-relaxed text-stone-500">
              {isError ? (
                <span className="inline-flex items-center gap-1 text-red-600">
                  <TriangleAlert className="h-3 w-3" aria-hidden="true" />
                  {error instanceof Error ? error.message : "Couldn't save that decision."}
                </span>
              ) : (
                "This sets the student's risk tier everywhere. You can change it later — the history is kept."
              )}
            </p>

            {/* Two steps by design: choosing a tier arms the decision,
                this commits it. One-click-per-tier would make a stray
                click reclassify a student across the whole app. */}
            <button
              type="button"
              onClick={commit}
              disabled={decision === null || isSubmitting}
              className="inline-flex items-center gap-2 rounded-xl bg-stone-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-stone-700 disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-stone-900"
            >
              {isSubmitting ? (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              ) : (
                <Check className="h-4 w-4" aria-hidden="true" />
              )}
              Record decision
            </button>
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------ */}
      {/* History                                                       */}
      {/* ------------------------------------------------------------ */}
      {review_history.length > (applied ? 1 : 0) && (
        <details className="mt-3 rounded-xl border border-stone-200 bg-white">
          <summary className="cursor-pointer list-none px-4 py-2.5 text-xs font-medium text-stone-600 transition hover:text-stone-900">
            <span className="inline-flex items-center gap-1.5">
              <History className="h-3.5 w-3.5" aria-hidden="true" />
              Decision history ({review_history.length})
            </span>
          </summary>

          {/* Superseded decisions are KEPT, not overwritten. "Resolved as
              high risk, changed to safe forty minutes later" is exactly
              what an audit of an early-warning system needs to see. */}
          <ul className="divide-y divide-stone-100 border-t border-stone-100">
            {review_history.map((entry) => (
              <li key={entry.id} className="px-4 py-2.5 text-xs">
                <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                  <span
                    className={`rounded-full px-1.5 py-0.5 font-medium ring-1 ring-inset ${BUCKET_STYLES[entry.decision].pill}`}
                  >
                    {BUCKET_LABELS[entry.decision]}
                  </span>
                  <span className="text-stone-500">
                    {entry.reviewer_name ?? "Unknown lecturer"}
                    {" · "}
                    {formatDateTime(entry.created_at)}
                  </span>
                  {entry.id === applied_review_id && (
                    <span className="rounded-full bg-stone-100 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-stone-500">
                      In effect
                    </span>
                  )}
                </div>

                <p className="mt-1 text-[11px] text-stone-400">
                  Decided when the rule engine said{" "}
                  {BUCKET_LABELS[entry.rule_tier].toLowerCase()} and the model said{" "}
                  {BUCKET_LABELS[entry.ml_tier].toLowerCase()}.
                </p>

                {entry.comment && (
                  <p className="mt-1 italic leading-relaxed text-stone-600">
                    “{entry.comment}”
                  </p>
                )}
              </li>
            ))}
          </ul>
        </details>
      )}
    </section>
  );
}