import { Check, X } from "lucide-react";
import { ATTENDANCE_FIRST_WEEK } from "../../../utils/studentCard";

interface AttendanceStripProps {
  /** One boolean per week, W1 first. `null` = never recorded. */
  weeks: boolean[] | null;
}

/**
 * Week-by-week attendance as a strip of cells.
 *
 * A STRIP, NOT A LINE CHART, and the reason is the data. Weekly
 * attendance is binary — `parse_attendance_cell` returns true or false,
 * nothing between. A line drawn through those points slopes across the
 * gap between two weeks and implies the student was "0.6 present" on a
 * Wednesday, which never happened. Discrete data gets discrete marks.
 *
 * It is also the more useful shape: a lecturer looking at this wants to
 * know WHICH week someone dropped off, and a strip answers that at a
 * glance where the aggregate percentage above it never can.
 *
 * Present and absent differ by fill, by icon and by colour — three
 * channels — so the strip survives greyscale printing and every form of
 * colour-vision deficiency. Plain divs rather than a charting library:
 * Recharts is built for continuous scales and axes, and neither exists
 * here.
 */
export default function AttendanceStrip({ weeks }: AttendanceStripProps) {
  if (weeks === null) {
    return (
      <p className="rounded-lg border border-dashed border-stone-300 bg-stone-50 px-3 py-2.5 text-xs leading-relaxed text-stone-500">
        Week-by-week attendance wasn't recorded for this upload. Only the overall
        percentage and its trend were kept. Re-importing this student's data will
        capture the weekly detail.
      </p>
    );
  }

  const attended = weeks.filter(Boolean).length;

  return (
    <div>
      <div className="flex flex-wrap gap-1.5">
        {weeks.map((present, index) => {
          const week = ATTENDANCE_FIRST_WEEK + index;
          const Icon = present ? Check : X;

          return (
            <div
              key={week}
              className="flex flex-col items-center gap-1"
              title={`Week ${week}: ${present ? "present" : "absent"}`}
            >
              <div
                className={`flex h-9 w-9 items-center justify-center rounded-lg ring-1 ring-inset ${
                  present
                    ? "bg-green-50 text-green-700 ring-green-200"
                    : "bg-red-50 text-red-600 ring-red-200"
                }`}
              >
                <Icon className="h-4 w-4" aria-hidden="true" />
              </div>
              <span className="text-[10px] tabular-nums text-stone-400">W{week}</span>
            </div>
          );
        })}
      </div>

      <p className="mt-2 text-xs text-stone-500">
        Present in{" "}
        <span className="font-medium tabular-nums text-stone-700">
          {attended} of {weeks.length}
        </span>{" "}
        recorded weeks.
      </p>

      <span className="sr-only">
        Weekly attendance:{" "}
        {weeks
          .map(
            (present, index) =>
              `week ${ATTENDANCE_FIRST_WEEK + index} ${present ? "present" : "absent"}`,
          )
          .join(", ")}
        .
      </span>
    </div>
  );
}
