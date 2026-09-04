import { useEffect, useRef, useState } from "react";
import {
  CircleAlert,
  CircleCheck,
  Loader2,
  Play,
  TrendingDown,
  TrendingUp,
  UserCheck,
  X,
} from "lucide-react";
import { useRunAnalysis } from "../../hooks/useAnalysis";
import { analysisService } from "../../services/analysisService";
import type { AnalysisRunResult, UnitAnalysisResult } from "../../types/analysis";

interface RunAnalysisButtonProps {
  /** Omit to run every active unit the lecturer teaches. */
  unitId?: number | null;
  /** Shown on the button. "Run analysis" / "Analyse all units". */
  label?: string;
  variant?: "primary" | "secondary";
}

type Stage = "idle" | "confirming" | "running" | "done" | "error";

function Stat({
  value,
  label,
  tone = "neutral",
  icon: Icon,
}: {
  value: number;
  label: string;
  tone?: "neutral" | "bad" | "good";
  icon?: typeof TrendingUp;
}) {
  const colour =
    tone === "bad" && value > 0
      ? "text-red-700"
      : tone === "good" && value > 0
        ? "text-green-700"
        : "text-stone-900";

  return (
    <div className="px-4 py-3">
      <p className={`flex items-center gap-1.5 text-lg font-semibold tabular-nums ${colour}`}>
        {Icon && value > 0 && <Icon className="h-4 w-4" aria-hidden="true" />}
        {value}
      </p>
      <p className="mt-0.5 text-xs text-stone-600">{label}</p>
    </div>
  );
}

/**
 * The button that actually runs the system.
 *
 * The rule engine, the ML model and the hybrid reconciliation have
 * existed since Phase 5, and so has an endpoint that runs them. This is
 * the first time a lecturer can press it.
 *
 * WHY IT CONFIRMS FIRST. The verdict tables are append-only, so a run
 * destroys nothing and looks completely safe. It is not quite: it
 * supersedes every current verdict, and any review decision whose engine
 * tiers no longer match is left behind by the carry-forward rule. A
 * lecturer can lose a judgement they made last week without a single row
 * being deleted — so the dialog says how many decisions are standing
 * before they commit, and the result says how many survived.
 *
 * WHY IT REPORTS A DIFF. "40 students analysed" answers "did it work".
 * "3 moved into High Risk" answers what they actually asked.
 */
export default function RunAnalysisButton({
  unitId = null,
  label = "Run analysis",
  variant = "primary",
}: RunAnalysisButtonProps) {
  const [stage, setStage] = useState<Stage>("idle");
  const [scope, setScope] = useState<UnitAnalysisResult[] | null>(null);
  const [result, setResult] = useState<AnalysisRunResult | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const dialogRef = useRef<HTMLDivElement>(null);

  const runAnalysis = useRunAnalysis();
  const open = stage !== "idle";

  /**
   * Escape closes the dialog — bound to `document`, not to the dialog.
   *
   * Bound to the dialog it stops working the moment focus lands on a
   * disabled button, because a disabled element drops focus to <body>.
   * That exact bug cost a debugging session in Phase 7.6b.
   */
  useEffect(() => {
    if (!open) return;
    function onKey(event: KeyboardEvent) {
      // Never interruptible mid-run: the request is already in flight
      // and closing the dialog would hide a result the lecturer needs.
      if (event.key === "Escape" && stage !== "running") setStage("idle");
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, stage]);

  async function handleOpen() {
    setStage("confirming");
    setScope(null);
    setMessage(null);
    try {
      setScope(await analysisService.preview(unitId));
    } catch {
      // A failed preview must not block the run. It is context, not a
      // precondition — the dialog just says less.
      setScope([]);
    }
  }

  async function handleRun() {
    setStage("running");
    try {
      setResult(await runAnalysis.mutateAsync({ unitId }));
      setStage("done");
    } catch (error) {
      const detail =
        (error as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail;
      setMessage(
        detail ??
          "The analysis could not be completed. Nothing was changed — try again.",
      );
      setStage("error");
    }
  }

  const totalStudents = scope?.reduce((sum, u) => sum + u.total_students, 0) ?? 0;
  const alreadyAnalysed = scope?.reduce((sum, u) => sum + u.unchanged, 0) ?? 0;
  const standingDecisions =
    scope?.reduce((sum, u) => sum + u.lecturer_decisions_carried, 0) ?? 0;

  return (
    <>
      <button
        type="button"
        onClick={handleOpen}
        className={
          variant === "primary"
            ? "inline-flex items-center gap-2 rounded-xl bg-stone-900 px-3.5 py-2 text-sm font-medium text-white transition hover:bg-stone-800"
            : "inline-flex items-center gap-2 rounded-xl border border-stone-300 bg-white px-3.5 py-2 text-sm font-medium text-stone-700 transition hover:bg-stone-50"
        }
      >
        <Play className="h-4 w-4" aria-hidden="true" />
        {label}
      </button>

      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-stone-900/40 px-4">
          <div
            ref={dialogRef}
            role="dialog"
            aria-modal="true"
            aria-labelledby="run-analysis-title"
            className="max-h-[85vh] w-full max-w-lg overflow-y-auto rounded-2xl bg-white shadow-xl"
          >
            <header className="flex items-start justify-between gap-3 border-b border-stone-200 px-5 py-4">
              <h2
                id="run-analysis-title"
                className="text-base font-semibold text-stone-900"
              >
                {stage === "done"
                  ? "Analysis complete"
                  : stage === "error"
                    ? "Analysis did not run"
                    : unitId
                      ? "Run analysis for this unit"
                      : "Run analysis for all your units"}
              </h2>
              {stage !== "running" && (
                <button
                  type="button"
                  onClick={() => setStage("idle")}
                  aria-label="Close"
                  className="rounded-lg p-1 text-stone-400 transition hover:bg-stone-100 hover:text-stone-600"
                >
                  <X className="h-4 w-4" aria-hidden="true" />
                </button>
              )}
            </header>

            {/* ------------------------------------------------ */}
            {/* Confirm                                           */}
            {/* ------------------------------------------------ */}
            {(stage === "confirming" || stage === "running") && (
              <div className="space-y-4 px-5 py-5">
                <p className="text-sm text-stone-600">
                  This re-scores every enrolled student with the rule engine and
                  the ML model, using the data already ingested. Nothing is
                  deleted &mdash; each run adds a new verdict that supersedes the
                  last.
                </p>

                {scope === null ? (
                  <p className="flex items-center gap-2 text-sm text-stone-400">
                    <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
                    Checking what this covers…
                  </p>
                ) : (
                  <div className="rounded-xl border border-stone-200">
                    <div className="grid grid-cols-3 divide-x divide-stone-100">
                      <Stat value={scope.length} label="units" />
                      <Stat value={totalStudents} label="students" />
                      <Stat value={alreadyAnalysed} label="already scored" />
                    </div>
                  </div>
                )}

                {/* The one thing a run can actually cost you. */}
                {standingDecisions > 0 && (
                  <div className="flex items-start gap-2.5 rounded-xl border border-orange-200 bg-orange-50 px-4 py-3">
                    <CircleAlert
                      className="mt-0.5 h-4 w-4 shrink-0 text-orange-500"
                      aria-hidden="true"
                    />
                    <p className="text-sm text-orange-900">
                      <span className="font-semibold">
                        {standingDecisions} review decision
                        {standingDecisions === 1 ? "" : "s"}
                      </span>{" "}
                      currently stand on {standingDecisions === 1 ? "a" : "these"}{" "}
                      student{standingDecisions === 1 ? "" : "s"}. A decision is
                      kept only if both engines return the same tiers as before
                      &mdash; otherwise it goes back to Needs Review.
                    </p>
                  </div>
                )}

                {totalStudents === 0 && scope !== null && (
                  <p className="rounded-xl bg-stone-50 px-4 py-3 text-sm text-stone-600">
                    No students are enrolled yet, so there is nothing to analyse.
                  </p>
                )}

                <div className="flex justify-end gap-2 pt-1">
                  <button
                    type="button"
                    onClick={() => setStage("idle")}
                    disabled={stage === "running"}
                    className="rounded-xl border border-stone-300 px-3.5 py-2 text-sm font-medium text-stone-700 transition hover:bg-stone-50 disabled:opacity-50"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={handleRun}
                    disabled={stage === "running" || totalStudents === 0}
                    className="inline-flex items-center gap-2 rounded-xl bg-stone-900 px-3.5 py-2 text-sm font-medium text-white transition hover:bg-stone-800 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {stage === "running" ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                        Analysing…
                      </>
                    ) : (
                      <>
                        <Play className="h-4 w-4" aria-hidden="true" />
                        Run analysis
                      </>
                    )}
                  </button>
                </div>
              </div>
            )}

            {/* ------------------------------------------------ */}
            {/* Result                                            */}
            {/* ------------------------------------------------ */}
            {stage === "done" && result && (
              <div className="space-y-4 px-5 py-5">
                <p className="flex items-center gap-2 text-sm text-stone-700">
                  <CircleCheck className="h-4 w-4 text-green-600" aria-hidden="true" />
                  {result.succeeded} of {result.total_students} student
                  {result.total_students === 1 ? "" : "s"} scored across{" "}
                  {result.units_analysed} unit
                  {result.units_analysed === 1 ? "" : "s"} at week{" "}
                  {result.checkpoint_week}.
                </p>

                <div className="grid grid-cols-2 divide-x divide-y divide-stone-100 rounded-xl border border-stone-200 sm:grid-cols-4 sm:divide-y-0">
                  <Stat
                    value={result.moved_toward_risk}
                    label="moved toward risk"
                    tone="bad"
                    icon={TrendingUp}
                  />
                  <Stat
                    value={result.moved_away_from_risk}
                    label="moved away from risk"
                    tone="good"
                    icon={TrendingDown}
                  />
                  <Stat value={result.newly_analysed} label="newly scored" />
                  <Stat value={result.unchanged} label="unchanged" />
                  <Stat value={result.missing_data} label="missing data" tone="bad" icon={CircleAlert} />
                </div>

                {(result.now_needs_review > 0 ||
                  result.lecturer_decisions_invalidated > 0) && (
                  <div className="space-y-2 rounded-xl border border-violet-200 bg-violet-50 px-4 py-3">
                    {result.now_needs_review > 0 && (
                      <p className="flex items-start gap-2 text-sm text-violet-900">
                        <CircleAlert
                          className="mt-0.5 h-4 w-4 shrink-0"
                          aria-hidden="true"
                        />
                        <span>
                          <span className="font-semibold">
                            {result.now_needs_review}
                          </span>{" "}
                          student{result.now_needs_review === 1 ? "" : "s"} need a
                          decision &mdash; the two engines disagreed.
                        </span>
                      </p>
                    )}
                    {result.lecturer_decisions_invalidated > 0 && (
                      <p className="flex items-start gap-2 text-sm text-violet-900">
                        <UserCheck
                          className="mt-0.5 h-4 w-4 shrink-0"
                          aria-hidden="true"
                        />
                        <span>
                          <span className="font-semibold">
                            {result.lecturer_decisions_invalidated}
                          </span>{" "}
                          previous review decision
                          {result.lecturer_decisions_invalidated === 1
                            ? " was"
                            : "s were"}{" "}
                          discarded because the engine tiers changed.
                        </span>
                      </p>
                    )}
                  </div>
                )}

                {result.failed > 0 && (
                  <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
                    {result.failed} student
                    {result.failed === 1 ? "" : "s"} could not be scored, usually
                    because required data is missing. Everyone else was scored
                    normally.
                  </p>
                )}

                {/* Only worth showing when a run covered more than one. */}
                {result.units.length > 1 && (
                  <ul className="divide-y divide-stone-100 rounded-xl border border-stone-200">
                    {result.units.map((unit) => (
                      <li
                        key={unit.unit_id}
                        className="flex flex-wrap items-center justify-between gap-2 px-4 py-2.5 text-sm"
                      >
                        <span className="font-medium text-stone-800">
                          {unit.unit_code}
                        </span>
                        <span className="text-xs text-stone-500">
                          {unit.skipped_reason ??
                            `${unit.succeeded} scored · ${unit.moved_toward_risk} toward risk`}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}

                <div className="flex justify-end pt-1">
                  <button
                    type="button"
                    onClick={() => setStage("idle")}
                    className="rounded-xl bg-stone-900 px-3.5 py-2 text-sm font-medium text-white transition hover:bg-stone-800"
                  >
                    Done
                  </button>
                </div>
              </div>
            )}

            {/* ------------------------------------------------ */}
            {/* Error                                             */}
            {/* ------------------------------------------------ */}
            {stage === "error" && (
              <div className="space-y-4 px-5 py-5">
                <p className="flex items-start gap-2.5 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
                  <CircleAlert
                    className="mt-0.5 h-4 w-4 shrink-0 text-red-500"
                    aria-hidden="true"
                  />
                  {message}
                </p>
                <div className="flex justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => setStage("idle")}
                    className="rounded-xl border border-stone-300 px-3.5 py-2 text-sm font-medium text-stone-700 transition hover:bg-stone-50"
                  >
                    Close
                  </button>
                  <button
                    type="button"
                    onClick={handleRun}
                    className="rounded-xl bg-stone-900 px-3.5 py-2 text-sm font-medium text-white transition hover:bg-stone-800"
                  >
                    Try again
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}