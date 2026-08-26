import { Mail, Users } from "lucide-react";

interface StudentsToolbarProps {
  /** Enrolments in scope — NOT distinct people. See the note below. */
  enrolmentCount: number;
  /** Distinct people behind those enrolments. */
  studentCount: number;
  unitCount: number;
  /** Echoed from the payload rather than hardcoded. */
  checkpointWeek: number;
}

/**
 * Page title and the (parked) bulk-email action.
 *
 * THE SUBTITLE COUNTS BOTH WAYS ON PURPOSE. A row here is an enrolment,
 * because risk is computed per unit — the same person can be high risk
 * in one unit and safe in another, and merging them would force an
 * invented "worst tier wins" figure no engine ever produced. But saying
 * "24 students" when 20 people are enrolled would be quietly wrong, so
 * the line states both whenever they differ.
 *
 * "Email All At-Risk" is rendered and DISABLED. Keeping the button
 * visible shows where the feature will live, and disabling it is
 * honest; wiring it to nothing would be worse than not shipping it.
 * Its handler belongs with the Alerts phase, which owns email.
 */
export default function StudentsToolbar({
  enrolmentCount,
  studentCount,
  unitCount,
  checkpointWeek,
}: StudentsToolbarProps) {
  const enrolmentsDifferFromPeople = enrolmentCount !== studentCount;

  return (
    <header className="mb-6 flex flex-wrap items-start justify-between gap-4">
      <div>
        <h1 className="flex items-center gap-2.5 text-2xl font-semibold tracking-tight text-stone-900">
          <Users className="h-6 w-6 text-stone-400" aria-hidden="true" />
          Student Management
        </h1>

        <p className="mt-1 text-sm text-stone-500">
          Week {checkpointWeek} checkpoint
          <span className="mx-1.5 text-stone-300">·</span>
          {enrolmentsDifferFromPeople ? (
            <>
              {enrolmentCount} enrolment{enrolmentCount === 1 ? "" : "s"} ({studentCount}{" "}
              student{studentCount === 1 ? "" : "s"})
            </>
          ) : (
            <>
              {enrolmentCount} enrolled student{enrolmentCount === 1 ? "" : "s"}
            </>
          )}
          <span className="mx-1.5 text-stone-300">·</span>
          {unitCount} subject{unitCount === 1 ? "" : "s"}
        </p>
      </div>

      <button
        type="button"
        disabled
        title="Bulk email arrives with the Alerts section"
        className="inline-flex cursor-not-allowed items-center gap-2 rounded-xl bg-blue-600 px-5 py-3 text-sm font-medium text-white opacity-50"
      >
        <Mail className="h-4 w-4" aria-hidden="true" />
        Email All At-Risk
      </button>
    </header>
  );
}