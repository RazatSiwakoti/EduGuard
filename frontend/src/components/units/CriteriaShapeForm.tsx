import { useState } from "react";
import { useReplaceUnitShape, detailOf, statusOf } from "../../hooks/useUnitShape";
import type { AssessmentKind, UnitShape } from "../../types/unitShape";
import {
  isShapeChanged,
  parsePercentage,
  shapeTotal,
  validateShape,
  type ShapeRow,
} from "../../utils/unitShape";

interface CriteriaShapeFormProps {
  shape: UnitShape;
  /** Called when the server answers 409 — the unit locked underneath us. */
  onLocked: () => void;
}

/**
 * The coordinator's three questions, and nothing else:
 *
 *   Does this unit run weekly tutorials?   yes / no, fixed share
 *   Which assessments does it have?        up to the server's limit
 *   What is each one worth?                a percentage
 *
 * THE DECISION THAT CARRIES THIS COMPONENT: A LOCKED UNIT KEEPS AN
 * EDITABLE NAME FIELD.
 *
 * The runbook says a locked unit shows "fields disabled". Taken
 * literally that includes the name — and both backend sections state
 * the opposite rule in as many words: *a label is not a rule*. T1
 * allows a rename on a locked unit, T2's `classify_shape_change`
 * returns "labels_only" for one, and neither bumps `criteria_updated_at`
 * nor consumes the admin's one-shot unlock window.
 *
 * Disabling the name here would make a supported, deliberately
 * harmless operation unreachable, and would push a coordinator fixing a
 * typo into asking an admin to unlock the unit — spending a one-shot
 * window on a spelling correction, which is exactly the outcome T1
 * describes as "the feature is broken".
 *
 * So: while locked, `kind`, `percentage`, the tutorial toggle, Add and
 * Remove are disabled, and `name` stays editable. Save stays enabled
 * for the same reason — the server accepts a rename and accepts a save
 * that changes nothing, and a disabled button cannot explain itself.
 */
export default function CriteriaShapeForm({
  shape,
  onLocked,
}: CriteriaShapeFormProps) {
  const { limits, lock } = shape;

  // Derived once, at mount. The parent remounts this component with a
  // new `key` after every successful save, so there is no effect
  // syncing props into state and no window where a background refetch
  // can overwrite what the coordinator is typing.
  const initialRows: ShapeRow[] = shape.assessments.map((row) => ({
    key: `db-${row.id}`,
    id: row.id,
    name: row.name,
    kind: (row.kind ?? "assignment") as AssessmentKind,
    percentage: row.percentage === null ? "" : String(row.percentage),
  }));

  const [rows, setRows] = useState<ShapeRow[]>(initialRows);
  const [tutorialsEnabled, setTutorialsEnabled] = useState(shape.tutorials_enabled);
  const [newRowSeq, setNewRowSeq] = useState(0);

  const replace = useReplaceUnitShape(shape.unit_id);

  const validation = validateShape(rows, tutorialsEnabled, limits);
  const total = shapeTotal(rows, tutorialsEnabled, limits);
  const remaining = Math.round((limits.max_total_percentage - total) * 100) / 100;
  const overBudget = total > limits.max_total_percentage;

  const shapeChanged = isShapeChanged(
    rows,
    tutorialsEnabled,
    initialRows,
    shape.tutorials_enabled
  );

  // A locked unit accepts labels and no-ops. It refuses a shape change,
  // and saying so before the round trip is kinder than a 409.
  const blockedByLock = lock.locked && shapeChanged;

  const serverError =
    replace.isError && statusOf(replace.error) === 400
      ? detailOf(replace.error, "The server refused this shape.")
      : null;

  function updateRow(key: string, patch: Partial<ShapeRow>) {
    setRows((current) =>
      current.map((row) => (row.key === key ? { ...row, ...patch } : row))
    );
  }

  function addRow() {
    setRows((current) => [
      ...current,
      {
        key: `new-${newRowSeq}`,
        id: null,
        name: "",
        kind: "assignment",
        percentage: "",
      },
    ]);
    setNewRowSeq((n) => n + 1);
  }

  function removeRow(key: string) {
    setRows((current) => current.filter((row) => row.key !== key));
  }

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!validation.valid) return;

    replace.mutate(
      {
        tutorials_enabled: tutorialsEnabled,
        assessments: rows.map((row) => ({
          // Sending the id back is not optional. Without it the server
          // matches by slot alone, so a re-ordered save soft-deletes the
          // stored rows and starts new ones — losing the lecturer's pass
          // bar and orphaning every mark attached to them.
          id: row.id,
          name: row.name.trim(),
          kind: row.kind,
          percentage: parsePercentage(row.percentage) as number,
        })),
      },
      {
        onError: (error) => {
          if (statusOf(error) === 409) onLocked();
        },
      }
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5" data-testid="criteria-form">
      {/* ---------------- Weekly tutorials ---------------- */}
      <section>
        <h3 className="text-sm font-semibold text-stone-900">Weekly tutorials</h3>
        <label className="mt-2 flex items-start gap-2.5 rounded border border-stone-200 p-3">
          <input
            type="checkbox"
            checked={tutorialsEnabled}
            disabled={lock.locked}
            onChange={(event) => setTutorialsEnabled(event.target.checked)}
            className="mt-0.5 h-4 w-4 rounded border-stone-300 disabled:cursor-not-allowed"
            data-testid="tutorial-toggle"
          />
          <span className="text-sm">
            <span className="font-medium text-stone-900">
              This unit runs weekly tutorials
            </span>
            <span className="mt-0.5 block text-stone-500">
              Fixed at {limits.tutorial_percentage}% of the unit. Yes or no is
              the only choice — the share is not editable.
            </span>
          </span>
        </label>
      </section>

      {/* ---------------- Assessments ---------------- */}
      <section>
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-stone-900">
            Assessments{" "}
            <span className="font-normal text-stone-500">
              ({rows.length} of {limits.max_assessments})
            </span>
          </h3>
          <button
            type="button"
            onClick={addRow}
            disabled={lock.locked || rows.length >= limits.max_assessments}
            className="rounded border border-stone-300 px-2.5 py-1 text-xs font-medium text-stone-700 hover:bg-stone-100 disabled:cursor-not-allowed disabled:opacity-40"
            data-testid="add-assessment"
          >
            + Add assessment
          </button>
        </div>

        {rows.length === 0 && (
          <p className="mt-2 rounded border border-dashed border-stone-300 p-4 text-sm text-stone-500">
            No assessments yet. A unit with only tutorials is a legal shape, so
            this is a choice rather than an omission.
          </p>
        )}

        <div className="mt-2 space-y-2">
          {rows.map((row, index) => {
            const error = validation.rowErrors[row.key];
            return (
              <div
                key={row.key}
                className={`rounded border p-3 ${
                  error ? "border-red-300 bg-red-50" : "border-stone-200"
                }`}
                data-testid={`assessment-row-${index}`}
              >
                <div className="flex flex-wrap items-end gap-2">
                  <div className="min-w-[10rem] flex-1">
                    <label className="mb-1 block text-xs font-medium text-stone-600">
                      Name
                    </label>
                    <input
                      value={row.name}
                      // Editable even while locked — see the component
                      // docstring. A label is not a rule.
                      onChange={(event) =>
                        updateRow(row.key, { name: event.target.value })
                      }
                      placeholder={`Assessment ${index + 1}`}
                      className="w-full rounded border border-stone-300 px-2.5 py-1.5 text-sm outline-none focus:border-stone-500"
                      data-testid={`assessment-name-${index}`}
                    />
                  </div>

                  <div className="w-32">
                    <label className="mb-1 block text-xs font-medium text-stone-600">
                      Type
                    </label>
                    <select
                      value={row.kind}
                      disabled={lock.locked}
                      onChange={(event) =>
                        updateRow(row.key, {
                          kind: event.target.value as AssessmentKind,
                        })
                      }
                      className="w-full rounded border border-stone-300 px-2 py-1.5 text-sm outline-none focus:border-stone-500 disabled:bg-stone-100 disabled:text-stone-500"
                      data-testid={`assessment-kind-${index}`}
                    >
                      <option value="assignment">Assignment</option>
                      <option value="quiz">Quiz</option>
                    </select>
                  </div>

                  <div className="w-28">
                    <label className="mb-1 block text-xs font-medium text-stone-600">
                      % of unit
                    </label>
                    <input
                      type="number"
                      min={0}
                      max={limits.max_total_percentage}
                      step="0.01"
                      value={row.percentage}
                      disabled={lock.locked}
                      onChange={(event) =>
                        updateRow(row.key, { percentage: event.target.value })
                      }
                      className="w-full rounded border border-stone-300 px-2.5 py-1.5 text-sm outline-none focus:border-stone-500 disabled:bg-stone-100 disabled:text-stone-500"
                      data-testid={`assessment-pct-${index}`}
                    />
                  </div>

                  <button
                    type="button"
                    onClick={() => removeRow(row.key)}
                    disabled={lock.locked}
                    className="rounded border border-stone-300 px-2.5 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-40"
                    data-testid={`assessment-remove-${index}`}
                  >
                    Remove
                  </button>
                </div>

                {row.kind === "quiz" && (
                  <p className="mt-1.5 text-xs text-stone-500">
                    Quizzes are capped at {limits.quiz_max_percentage}% of the
                    unit.
                  </p>
                )}

                {error && (
                  <p
                    className="mt-1.5 text-xs font-medium text-red-700"
                    data-testid={`assessment-error-${index}`}
                  >
                    {error}
                  </p>
                )}
              </div>
            );
          })}
        </div>
      </section>

      {/* ---------------- Running total ---------------- */}
      <section
        className={`rounded border p-3 ${
          overBudget ? "border-red-300 bg-red-50" : "border-stone-200 bg-stone-50"
        }`}
        data-testid="running-total"
      >
        <div className="flex items-baseline justify-between">
          <span className="text-sm font-medium text-stone-700">
            Marks accounted for
          </span>
          <span
            className={`text-lg font-semibold ${
              overBudget ? "text-red-700" : "text-stone-900"
            }`}
          >
            {total}%
          </span>
        </div>

        <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-stone-200">
          <div
            className={`h-full ${overBudget ? "bg-red-500" : "bg-stone-800"}`}
            style={{
              width: `${Math.min(
                100,
                (total / limits.max_total_percentage) * 100
              )}%`,
            }}
          />
        </div>

        {/* Under 100% saves silently — the server accepts it without a
            warning and so does this. Stated as information, not as a
            problem to fix: a unit can legitimately carry a component
            this system does not model. */}
        <p className="mt-2 text-xs text-stone-500">
          {overBudget
            ? `Over by ${Math.round((total - limits.max_total_percentage) * 100) / 100}%.`
            : `${remaining}% not accounted for. Saving under ${limits.max_total_percentage}% is allowed.`}
        </p>

        {validation.formError && (
          <p
            className="mt-2 text-sm font-medium text-red-700"
            data-testid="form-error"
          >
            {validation.formError}
          </p>
        )}
      </section>

      {/* ---------------- Automatic, stated not offered ---------------- */}
      <section>
        <h3 className="text-sm font-semibold text-stone-900">
          Added automatically
        </h3>
        <p className="mt-1 text-xs text-stone-500">
          Every unit gets these. They are outside the {limits.max_total_percentage}%
          above and are not editable here.
        </p>
        <ul className="mt-2 divide-y divide-stone-100 rounded border border-stone-200">
          {shape.automatic.map((row) => (
            <li
              key={row.id ?? row.name}
              className="flex items-center justify-between px-3 py-2 text-sm"
            >
              <span className="text-stone-700">{row.name}</span>
              <span className="text-xs text-stone-500">
                pass mark {row.pass_mark ?? "—"} · fixed
              </span>
            </li>
          ))}
          {shape.automatic.length === 0 && (
            <li className="px-3 py-2 text-sm text-stone-500">
              None recorded for this unit.
            </li>
          )}
        </ul>
      </section>

      {serverError && (
        <p
          className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700"
          data-testid="server-error"
        >
          {serverError}
        </p>
      )}

      <div className="flex items-center justify-between gap-3 border-t border-stone-200 pt-4">
        <p className="text-xs text-stone-500">
          {blockedByLock
            ? "This unit is locked. Names can still be corrected; changing a percentage or the tutorial setting needs an unlock."
            : "The server re-checks every rule on save."}
        </p>
        <button
          type="submit"
          disabled={!validation.valid || replace.isPending}
          className="rounded bg-stone-900 px-4 py-2 text-sm font-medium text-white hover:bg-stone-800 disabled:cursor-not-allowed disabled:opacity-50"
          data-testid="save-criteria"
        >
          {replace.isPending ? "Saving…" : "Save criteria"}
        </button>
      </div>
    </form>
  );
}