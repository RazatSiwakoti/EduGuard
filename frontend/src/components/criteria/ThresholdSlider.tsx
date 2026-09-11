import { TriangleAlert } from "lucide-react";
import type { ThresholdGroup } from "../../types/unitShape";

interface ThresholdSliderProps {
  group: ThresholdGroup;
  label: string;
  /** The value being edited. Never null — the parent resolves `mixed`. */
  value: number;
  /**
   * True while the group's rows disagree and the lecturer has not
   * touched the slider yet. The control still SITS on `value` (it has
   * to sit somewhere) but the readout must not print that number as
   * though it were the unit's pass mark, because it is only one of
   * several.
   */
  mixedUntouched?: boolean;
  disabled?: boolean;
  onChange: (next: number) => void;
  /** One line per item: "Quiz 1 — pass at 9.2 / 20". */
  preview: string[];
}

/**
 * One category's pass bar.
 *
 * WHY THE RANGE IS THE RULE, NOT A HINT
 * -------------------------------------
 * `min` is the server's floor and `max` is the server's default, both
 * read out of the response rather than written here. A native range
 * input physically cannot be dragged outside them, so "lower only,
 * never above 50" is enforced by the control itself and the server
 * re-checks it anyway (`validate_lecturer_threshold`). Nothing in this
 * file knows that the numbers happen to be 45, 40 and 50 — a floor
 * stated twice is a floor that eventually disagrees with itself.
 *
 * WHY THE PASS MARKS ARE SHOWN WHILE DRAGGING
 * -------------------------------------------
 * "46%" is not what a lecturer is deciding. "9.2 out of 20" is. The
 * percentage is the stored number; the mark is the thing they can
 * picture a student getting, and it is derived from the coordinator's
 * `max_score`, which differs per item — so a single percentage produces
 * a different pass mark on every row.
 */
export default function ThresholdSlider({
  group,
  label,
  value,
  mixedUntouched = false,
  disabled = false,
  onChange,
  preview,
}: ThresholdSliderProps) {
  const floor = group.floor ?? 0;
  const max = group.default;
  const lowered = value < max;
  const inputId = `threshold-${group.category}`;

  return (
    <div className="rounded-md border border-stone-200 p-4">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <label htmlFor={inputId} className="text-sm font-medium text-stone-900">
          {label}
        </label>
        <p className="text-sm tabular-nums text-stone-900">
          {mixedUntouched ? (
            <span className="text-lg font-semibold text-amber-700">Mixed</span>
          ) : (
            <>
              <span className="text-lg font-semibold">{value}%</span>
              {lowered && (
                <span className="ml-2 text-xs font-normal text-stone-500">
                  {(max - value).toFixed(0)} below the {max}% default
                </span>
              )}
            </>
          )}
        </p>
      </div>

      <p className="mt-0.5 text-xs text-stone-500">
        Applies to {group.applies_to}{" "}
        {group.applies_to === 1 ? "criterion" : "criteria"}
        {group.item_names.length > 0 && `: ${group.item_names.join(", ")}`}
      </p>

      {/* The mixed warning sits ABOVE the control on purpose. It
          describes what pressing save will destroy, and a lecturer who
          reads it after dragging has already chosen. */}
      {group.mixed && (
        <div className="mt-3 flex gap-2 rounded border border-amber-300 bg-amber-50 p-2.5">
          <TriangleAlert
            className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-600"
            aria-hidden="true"
          />
          <p className="text-xs leading-relaxed text-amber-900">
            These criteria are currently on different pass marks (
            {group.values.map((v) => `${v}%`).join(", ")}). There is one bar per
            category, so saving will put all {group.applies_to} on the same
            number.
          </p>
        </div>
      )}

      <input
        id={inputId}
        type="range"
        min={floor}
        max={max}
        step={1}
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(Number(event.target.value))}
        className="mt-3 w-full accent-stone-900 disabled:cursor-not-allowed disabled:opacity-50"
        aria-describedby={`${inputId}-range`}
      />

      <div
        id={`${inputId}-range`}
        className="flex justify-between text-[11px] tabular-nums text-stone-400"
      >
        <span>{floor}% floor</span>
        <span>{max}% default</span>
      </div>

      {preview.length > 0 && (
        <ul className="mt-3 space-y-1 border-t border-stone-100 pt-3">
          {preview.map((line) => (
            <li key={line} className="text-xs tabular-nums text-stone-600">
              {line}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}