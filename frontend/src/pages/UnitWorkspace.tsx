import { Link, NavLink, Outlet, useParams } from "react-router-dom";
import { ArrowLeft, CircleAlert, Users } from "lucide-react";
import { useLecturerUnits } from "../hooks/useLecturerUnits";
import type { DashboardUnit } from "../types/dashboard";

/**
 * Everything you do to one unit, in one place.
 *
 * WHY THE TABS ARE ROUTES, NOT useState
 * -------------------------------------
 * Each tab is a nested route (/units/5, /units/5/import,
 * /units/5/add-student) rather than a local state variable. That means
 * the browser back button steps between tabs, a tab is bookmarkable and
 * shareable, and a refresh keeps you where you were. Local state loses
 * all three, and the import wizard in particular is a multi-step flow
 * where losing your place on refresh would be genuinely annoying.
 *
 * WHY THE UNIT IS RESOLVED FROM THE LIST
 * --------------------------------------
 * There is no GET /lecturer/units/{id}, and one is not needed: the list
 * is already cached by React Query with a five-minute staleTime, so
 * finding the unit in it is instant and costs no request. It also gives
 * authorisation for free — a unit that is not in this lecturer's list is
 * either someone else's or does not exist, and either way the answer to
 * show is the same.
 */
export default function UnitWorkspace() {
  const params = useParams();
  const { data: units, isLoading, isError } = useLecturerUnits();

  // Number("abc") is NaN, and NaN never equals any unit id - so a
  // malformed URL falls through to the not-found state rather than
  // throwing.
  const unitId = Number(params.unitId);
  const unit: DashboardUnit | undefined = units?.find((u) => u.id === unitId);

  if (isLoading) {
    return (
      <div className="px-6 py-8">
        <div className="mx-auto max-w-5xl animate-pulse">
          <div className="mb-3 h-7 w-56 rounded bg-stone-200" />
          <div className="mb-6 h-4 w-80 rounded bg-stone-200" />
          <div className="h-64 rounded-lg bg-stone-200" />
        </div>
      </div>
    );
  }

  if (isError || !unit) {
    return (
      <div className="px-6 py-8">
        <div className="mx-auto max-w-md rounded-lg border border-stone-200 bg-white p-8 text-center">
          <CircleAlert className="mx-auto h-8 w-8 text-stone-300" aria-hidden="true" />
          <h1 className="mt-3 text-base font-semibold text-stone-900">Unit not found</h1>
          <p className="mt-2 text-sm leading-relaxed text-stone-500">
            This unit either doesn't exist or isn't assigned to you. You can only open
            units you're the assigned lecturer for.
          </p>
          <Link
            to="/units"
            className="mt-5 inline-flex items-center gap-2 rounded-md bg-stone-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-stone-800"
          >
            <ArrowLeft className="h-4 w-4" aria-hidden="true" />
            Back to units
          </Link>
        </div>
      </div>
    );
  }

  const offering = [unit.teaching_period, unit.year].filter(Boolean).join(" ");

  const tabClass = ({ isActive }: { isActive: boolean }) =>
    `border-b-2 px-3 py-2 text-sm transition ${
      isActive
        ? "border-stone-900 font-medium text-stone-900"
        : "border-transparent text-stone-500 hover:text-stone-700"
    }`;

  return (
    <div className="px-6 py-8">
      <div className="mx-auto max-w-5xl">
        <Link
          to="/units"
          className="mb-4 inline-flex items-center gap-1.5 text-sm text-stone-500 transition hover:text-stone-900"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          All units
        </Link>

        <header className="mb-6">
          <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
            <h1 className="text-xl font-semibold text-stone-900">{unit.unit_code}</h1>
            <p className="text-base text-stone-600">{unit.unit_name}</p>
          </div>

          <div className="mt-1.5 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-stone-500">
            <span className="inline-flex items-center gap-1.5">
              <Users className="h-4 w-4" aria-hidden="true" />
              {unit.enrolled_count} enrolled
            </span>
            {offering && <span>{offering}</span>}
            {unit.level && <span className="capitalize">{unit.level}</span>}
          </div>
        </header>

        <nav className="mb-6 flex gap-1 border-b border-stone-200">
          {/* `end` is essential on the index tab. Without it NavLink
              treats /units/5 as a prefix of /units/5/import and marks
              Overview active on every tab. */}
          <NavLink to={`/units/${unit.id}`} end className={tabClass}>
            Overview
          </NavLink>
          <NavLink to={`/units/${unit.id}/import`} className={tabClass}>
            Import Data
          </NavLink>
          <NavLink to={`/units/${unit.id}/add-student`} className={tabClass}>
            Add Student
          </NavLink>
        </nav>

        {/* The unit is passed down through Outlet context so each tab
            gets it without refetching or prop-drilling through a router
            boundary that cannot carry props. */}
        <Outlet context={{ unit }} />
      </div>
    </div>
  );
}

/** Shape every unit tab receives via useOutletContext(). */
export interface UnitTabContext {
  unit: DashboardUnit;
}