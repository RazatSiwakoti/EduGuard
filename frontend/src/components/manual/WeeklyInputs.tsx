import { ATTENDANCE_ABSENT, ATTENDANCE_PRESENT, TUTORIAL_STATUSES } from "../../types/ingestion";

interface WeeklyAttendanceInputProps {
  /** Exactly 7 values, weeks 1-7, in order. */
  values: string[];
  onChange: (index: number, value: string) => void;
}

/**
 * Seven present/absent toggles, weeks 1 to 7.
 *
 * The count is not a design choice: calculate_attendance_trend()
 * returns None unless it receives exactly 7 values, and the trend is
 * what the momentum chart and one of the six ML features depend on.
 * Rendering a fixed 7 boxes makes a wrong count structurally impossible
 * rather than something to validate against.
 *
 * A toggle rather than a dropdown because attendance is binary and the
 * whole week's pattern should be readable at a glance — seven dropdowns
 * all reading "yes" is far harder to scan than seven filled buttons.
 *
 * Note the values sent are the literal strings "yes" and "no". The
 * backend's parse_attendance_cell() treats anything unrecognised as
 * absent, so sending a boolean or a number would risk silently marking
 * every week absent.
 */
export function WeeklyAttendanceInput({
  values,
  onChange,
}: WeeklyAttendanceInputProps) {
  return (
    <div className="flex flex-wrap gap-2">
      {values.map((value, index) => {
        const isPresent = value === ATTENDANCE_PRESENT;

        return (
          <div key={index} className="text-center">
            <span className="mb-1 block text-[11px] text-stone-500">W{index + 1}</span>
            <button
              type="button"
              onClick={() =>
                onChange(index, isPresent ? ATTENDANCE_ABSENT : ATTENDANCE_PRESENT)
              }
              aria-pressed={isPresent}
              title={`Week ${index + 1}: ${isPresent ? "present" : "absent"}`}
              className={`h-10 w-12 rounded-md border text-xs font-medium transition ${
                isPresent
                  ? "border-green-300 bg-green-50 text-green-800"
                  : "border-stone-200 bg-white text-stone-400 hover:bg-stone-50"
              }`}
            >
              {isPresent ? "Present" : "Absent"}
            </button>
          </div>
        );
      })}
    </div>
  );
}

interface WeeklyTutorialInputProps {
  /** Exactly 6 values, weeks 2-7, in order. */
  values: string[];
  onChange: (index: number, value: string) => void;
}

/**
 * Six tutorial status selectors, weeks 2 to 7.
 *
 * Starts at week 2 because week 1 has no tutorial — that is why
 * calculate_tutorial_completion_trend() expects 6 values rather than 7,
 * and why the labels here start at W2. Mislabelling them 1-6 would make
 * a lecturer enter the wrong week's data in the right box.
 *
 * Three states, not two: "late" carries 0.8 credit in
 * TUTORIAL_STATUS_CREDIT, so collapsing it into either submitted or
 * missed would change the student's computed percentage.
 */
export function WeeklyTutorialInput({ values, onChange }: WeeklyTutorialInputProps) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
      {values.map((value, index) => (
        <label key={index} className="block">
          <span className="mb-1 block text-[11px] text-stone-500">W{index + 2}</span>
          <select
            value={value}
            onChange={(event) => onChange(index, event.target.value)}
            className="w-full rounded-md border border-stone-200 bg-white px-2 py-1.5 text-xs text-stone-900 outline-none transition focus:border-stone-400"
          >
            {TUTORIAL_STATUSES.map((status) => (
              <option key={status.value} value={status.value}>
                {status.label}
              </option>
            ))}
          </select>
        </label>
      ))}
    </div>
  );
}
