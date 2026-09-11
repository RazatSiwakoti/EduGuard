import { useMemo, useState } from "react";
import { ArrowLeft, ArrowRight, Loader2, Upload } from "lucide-react";
import type { Criterion } from "../../types/criteria";
import { CATEGORY_COLUMN_COUNT } from "../../types/criteria";
import type {
  BulkIngestionMapping,
  FilePreviewResult,
  IdentityMapping,
  ImportStep,
} from "../../types/ingestion";
import { EMPTY_IDENTITY } from "../../types/ingestion";
import { useBulkImport, usePreviewFile } from "../../hooks/useIngestion";
import {
  guessColumnForCriterion,
  guessIdentityColumns,
  guessWeeklyColumns,
} from "../../utils/columnMatching";
import StepFile from "./StepFile";
import StepIdentity from "./StepIdentity";
import StepCriteria from "./StepCriteria";
import StepReview from "./StepReview";
import ImportResult from "./ImportResult";

interface ImportWizardProps {
  unitId: number;
  unitCode: string;
  criteria: Criterion[];
}

const STEP_ORDER: ImportStep[] = ["file", "identity", "criteria", "review"];

const STEP_LABELS: Record<ImportStep, string> = {
  file: "Choose file",
  identity: "Student identity",
  criteria: "Criteria",
  review: "Review",
  result: "Result",
};

/**
 * The four-step bulk import flow.
 *
 * ALL WIZARD STATE LIVES HERE, IN ONE PLACE
 * -----------------------------------------
 * The file, its preview, and both halves of the mapping are held in
 * this component and passed down. Each step is a presentational
 * component that renders what it is given and reports changes upward.
 *
 * That matters because the steps are interdependent: the criteria step
 * needs the column list discovered by the file step, and the review
 * step needs everything. Spreading state across the steps would mean
 * lifting most of it back up here anyway, in a less obvious way.
 *
 * State is intentionally NOT persisted across navigation. Leaving the
 * tab mid-import discards the mapping, which is the safe default — a
 * half-remembered mapping silently reapplied to a different file is a
 * far worse outcome than re-selecting a few dropdowns.
 */
export default function ImportWizard({
  unitId,
  unitCode,
  criteria,
}: ImportWizardProps) {
  const [step, setStep] = useState<ImportStep>("file");
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<FilePreviewResult | null>(null);
  const [identity, setIdentity] = useState<IdentityMapping>(EMPTY_IDENTITY);
  const [singleMap, setSingleMap] = useState<Record<number, string>>({});
  const [weeklyMap, setWeeklyMap] = useState<Record<number, string[]>>({});

  const previewMutation = usePreviewFile(unitId);
  const importMutation = useBulkImport(unitId);

  const activeCriteria = useMemo(
    () => criteria.filter((criterion) => criterion.enabled),
    [criteria],
  );

  /**
   * Reads the file, then pre-fills every mapping it can guess.
   *
   * Guessing happens once, here, rather than inside the mapping steps.
   * Re-guessing on each render would fight the lecturer: correct a
   * dropdown, and a heuristic would helpfully change it back.
   */
  function handleFileChosen(chosen: File) {
    setFile(chosen);
    setPreview(null);

    previewMutation.mutate(chosen, {
      onSuccess: (result) => {
        setPreview(result);
        setIdentity({ ...EMPTY_IDENTITY, ...guessIdentityColumns(result.columns) });

        const nextSingle: Record<number, string> = {};
        const nextWeekly: Record<number, string[]> = {};

        for (const criterion of activeCriteria) {
          const category = criterion.category;
          const columnCount = category ? CATEGORY_COLUMN_COUNT[category] : null;

          if (category && columnCount !== null) {
            const startWeek = category === "weekly_tut" ? 2 : 1;
            const guessed = guessWeeklyColumns(
              result.columns,
              category,
              startWeek,
              columnCount,
            );
            // Always the right length, so a partially-guessed set never
            // leaves undefined holes the dropdowns would render blank.
            nextWeekly[criterion.id] =
              guessed.length === columnCount ? guessed : Array(columnCount).fill("");
          } else {
            nextSingle[criterion.id] = guessColumnForCriterion(
              result.columns,
              criterion.name,
              category,
            );
          }
        }

        setSingleMap(nextSingle);
        setWeeklyMap(nextWeekly);
      },
    });
  }

  function handleWeeklyChange(criteriaId: number, index: number, column: string) {
    setWeeklyMap((current) => {
      const criterion = activeCriteria.find((c) => c.id === criteriaId);
      const columnCount = criterion?.category
        ? CATEGORY_COLUMN_COUNT[criterion.category] ?? 0
        : 0;

      const existing = current[criteriaId] ?? Array(columnCount).fill("");
      const next = [...existing];
      next[index] = column;
      return { ...current, [criteriaId]: next };
    });
  }

  /**
   * Everything blocking submission, as sentences a lecturer can act on.
   *
   * The partial-weekly rule is the important one: the backend accepts a
   * wrong-length weekly list, computes a percentage from it, and simply
   * returns None for the trend — no error anywhere. That silent
   * degradation is exactly what this check exists to prevent.
   */
  const problems = useMemo(() => {
    const found: string[] = [];

    if (!identity.student_number_col) found.push("Student number column is not mapped.");
    if (!identity.name_col) found.push("Full name column is not mapped.");

    for (const criterion of activeCriteria) {
      const category = criterion.category;
      const columnCount = category ? CATEGORY_COLUMN_COUNT[category] : null;
      if (columnCount === null) continue;

      const filled = (weeklyMap[criterion.id] ?? []).filter(Boolean).length;
      if (filled > 0 && filled < columnCount) {
        found.push(
          `${criterion.name}: ${filled} of ${columnCount} weeks mapped — map them all or clear them.`,
        );
      }
    }

    return found;
  }, [identity, activeCriteria, weeklyMap]);

  function buildMapping(): BulkIngestionMapping {
    // Only fully-mapped weekly criteria are sent. A partial set is
    // already blocked above; this is the second line of defence.
    const weekly: Record<number, string[]> = {};
    for (const criterion of activeCriteria) {
      const category = criterion.category;
      const columnCount = category ? CATEGORY_COLUMN_COUNT[category] : null;
      if (columnCount === null) continue;

      const columns = (weeklyMap[criterion.id] ?? []).filter(Boolean);
      if (columns.length === columnCount) weekly[criterion.id] = columns;
    }

    const single: Record<number, string> = {};
    for (const [criteriaId, column] of Object.entries(singleMap)) {
      if (column) single[Number(criteriaId)] = column;
    }

    return {
      student_number_col: identity.student_number_col,
      name_col: identity.name_col,
      // Empty string means "not in my file"; the backend expects null.
      email_col: identity.email_col || null,
      program_col: identity.program_col || null,
      gender_col: identity.gender_col || null,
      age_col: identity.age_col || null,
      criteria_column_map: single,
      weekly_criteria_column_map: weekly,
    };
  }

  function handleSubmit() {
    if (!file || problems.length > 0) return;

    importMutation.mutate(
      { file, mapping: buildMapping() },
      { onSuccess: () => setStep("result") },
    );
  }

  function reset() {
    setStep("file");
    setFile(null);
    setPreview(null);
    setIdentity(EMPTY_IDENTITY);
    setSingleMap({});
    setWeeklyMap({});
    importMutation.reset();
    previewMutation.reset();
  }

  const stepIndex = STEP_ORDER.indexOf(step);
  const canGoForward = step === "file" ? Boolean(preview) : true;

  if (step === "result" && importMutation.data) {
    return (
      <ImportResult
        result={importMutation.data}
        unitId={unitId}
        onImportAnother={reset}
      />
    );
  }

  return (
    <div>
      {/* Progress rail. Completed steps are clickable so a lecturer can
          jump back to fix one thing without stepping backwards through
          every screen; future steps are not, because they depend on
          decisions not yet made. */}
      <ol className="mb-6 flex flex-wrap gap-x-2 gap-y-1">
        {STEP_ORDER.map((name, index) => {
          const isDone = index < stepIndex;
          const isCurrent = index === stepIndex;

          return (
            <li key={name} className="flex items-center gap-2">
              <button
                type="button"
                disabled={!isDone}
                onClick={() => setStep(name)}
                className={`flex items-center gap-1.5 rounded-md px-2 py-1 text-xs transition ${
                  isCurrent
                    ? "font-medium text-stone-900"
                    : isDone
                      ? "text-stone-500 hover:bg-stone-100 hover:text-stone-900"
                      : "text-stone-300"
                }`}
              >
                <span
                  className={`flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-medium ${
                    isCurrent
                      ? "bg-stone-900 text-white"
                      : isDone
                        ? "bg-stone-200 text-stone-600"
                        : "bg-stone-100 text-stone-400"
                  }`}
                >
                  {index + 1}
                </span>
                {STEP_LABELS[name]}
              </button>

              {index < STEP_ORDER.length - 1 && (
                <span className="text-stone-200" aria-hidden="true">
                  ›
                </span>
              )}
            </li>
          );
        })}
      </ol>

      {step === "file" && (
        <StepFile
          file={file}
          preview={preview}
          isLoading={previewMutation.isPending}
          onFileChosen={handleFileChosen}
        />
      )}

      {step === "identity" && preview && (
        <StepIdentity
          columns={preview.columns}
          identity={identity}
          onChange={setIdentity}
        />
      )}

      {step === "criteria" && preview && (
        <StepCriteria
          columns={preview.columns}
          criteria={activeCriteria}
          singleMap={singleMap}
          weeklyMap={weeklyMap}
          onSingleChange={(criteriaId, column) =>
            setSingleMap((current) => ({ ...current, [criteriaId]: column }))
          }
          onWeeklyChange={handleWeeklyChange}
        />
      )}

      {step === "review" && preview && (
        <StepReview
          preview={preview}
          identity={identity}
          criteria={activeCriteria}
          singleMap={singleMap}
          weeklyMap={weeklyMap}
          problems={problems}
        />
      )}

      <div className="mt-6 flex items-center justify-between gap-3 border-t border-stone-200 pt-4">
        <button
          type="button"
          onClick={() => setStep(STEP_ORDER[Math.max(0, stepIndex - 1)])}
          disabled={stepIndex === 0}
          className="inline-flex items-center gap-2 rounded-md border border-stone-200 bg-white px-3 py-2 text-sm font-medium text-stone-700 transition hover:bg-stone-50 disabled:opacity-40"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          Back
        </button>

        {step === "review" ? (
          <button
            type="button"
            onClick={handleSubmit}
            disabled={problems.length > 0 || importMutation.isPending}
            className="inline-flex items-center gap-2 rounded-md bg-stone-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-stone-800 disabled:opacity-40"
          >
            {importMutation.isPending ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                Importing and analysing…
              </>
            ) : (
              <>
                <Upload className="h-4 w-4" aria-hidden="true" />
                Import into {unitCode}
              </>
            )}
          </button>
        ) : (
          <button
            type="button"
            onClick={() => setStep(STEP_ORDER[stepIndex + 1])}
            disabled={!canGoForward}
            className="inline-flex items-center gap-2 rounded-md bg-stone-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-stone-800 disabled:opacity-40"
          >
            Continue
            <ArrowRight className="h-4 w-4" aria-hidden="true" />
          </button>
        )}
      </div>
    </div>
  );
}
