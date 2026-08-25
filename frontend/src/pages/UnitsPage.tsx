import { BookOpen, CircleAlert } from "lucide-react";
import { useLecturerUnits } from "../hooks/useLecturerUnits";
import UnitCard from "../components/units/UnitCard";

/**
 * Every unit the lecturer teaches — the entry point to each unit's
 * workspace.
 *
 * Reads GET /lecturer/units rather than the dashboard endpoint. This
 * page needs unit codes and enrolment counts; pulling the entire cohort
 * and every criterion score to render a handful of cards would be a lot
 * of payload for no benefit.
 */
export default function UnitsPage() {
  const { data: units, isLoading, isError, error } = useLecturerUnits();

  if (isLoading) {
    return (
      <div className="px-6 py-8">
        <div className="mx-auto max-w-5xl animate-pulse">
          <div className="mb-6 h-8 w-40 rounded bg-stone-200" />
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
            {[0, 1, 2].map((index) => (
              <div key={index} className="h-40 rounded-lg bg-stone-200" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="px-6 py-8">
        <div className="mx-auto max-w-md rounded-lg border border-stone-200 bg-white p-8 text-center">
          <CircleAlert className="mx-auto h-8 w-8 text-stone-300" aria-hidden="true" />
          <h1 className="mt-3 text-base font-semibold text-stone-900">
            Couldn't load your units
          </h1>
          <p className="mt-2 text-sm text-stone-500">
            {error instanceof Error
              ? error.message
              : "Something went wrong reaching the server."}
          </p>
        </div>
      </div>
    );
  }

  const list = units ?? [];

  return (
    <div className="px-6 py-8">
      <div className="mx-auto max-w-5xl">
        <header className="mb-6">
          <h1 className="flex items-center gap-2 text-xl font-semibold text-stone-900">
            <BookOpen className="h-5 w-5 text-stone-400" aria-hidden="true" />
            Units
          </h1>
          <p className="mt-1 text-sm text-stone-500">
            {list.length === 0
              ? "You aren't assigned to any units yet."
              : `${list.length} unit${list.length === 1 ? "" : "s"} assigned to you. Open one to import data or add a student.`}
          </p>
        </header>

        {/* Unit assignment is an administrator action, so the empty
            state points at the person who can actually fix it rather
            than offering a button this lecturer cannot use. */}
        {list.length === 0 ? (
          <div className="rounded-lg border border-dashed border-stone-300 bg-white p-10 text-center">
            <p className="text-sm text-stone-500">
              An administrator assigns units to lecturers. Once you're assigned one, it
              will appear here.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
            {list.map((unit) => (
              <UnitCard key={unit.id} unit={unit} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}