import { useCallback, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { CircleAlert, Users } from "lucide-react";
import type { DashboardStudent, RiskBucket } from "../types/dashboard";
import type { StudentCardTarget } from "../types/studentDetail";
import { useLecturerDashboard } from "../hooks/useDashboard";
import {
  PAGE_SIZE,
  countsByBucket,
  csvFilename,
  downloadCsv,
  filterByBucket,
  filterByUnit,
  pageCount,
  pageSlice,
  searchStudents,
  sortStudents,
  toCsv,
} from "../utils/studentsTable";
import type { SortDirection, SortKey } from "../utils/studentsTable";
import RiskTabs from "../components/students/RiskTabs";
import StudentsFilterBar from "../components/students/StudentsFilterBar";
import StudentsTable from "../components/students/StudentsTable";
import StudentsToolbar from "../components/students/StudentsToolBar";
import StudentCard from "../components/students/card/StudentCard";

/**
 * Students — every enrolment across the lecturer's units (Phase 7.6a).
 *
 * READS THE DASHBOARD PAYLOAD, ON PURPOSE. `GET /lecturer/dashboard`
 * already returns one flat row per student per unit carrying the final
 * verdict, both engines' tiers and every criterion's score, threshold
 * and trend — which is exactly this table. Reusing `useLecturerDashboard`
 * means the two pages share one TanStack Query cache entry, so opening
 * Students after the Dashboard fetches nothing at all.
 *
 * A dedicated per-student endpoint IS still needed, but only for the
 * student card in 7.6b: `RiskScore.explanation` (SHAP-derived) is not
 * in this payload and cannot be reconstructed from it.
 *
 * FILTER ORDER IS FIXED: subject → risk tab → search → sort → paginate.
 * The tab counts are computed after the subject filter but BEFORE the
 * search, so they describe the selected unit rather than flickering on
 * every keystroke.
 */
export default function StudentsPage() {
  const { data, isLoading, isError, error } = useLecturerDashboard();

  const [bucket, setBucket] = useState<RiskBucket | null>(null);
  const [unitId, setUnitId] = useState<number | null>(null);
  const [search, setSearch] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("risk");
  const [direction, setDirection] = useState<SortDirection>("asc");
  const [page, setPage] = useState(1);

  /**
   * Which card is open, held in the URL rather than in state.
   *
   * `?student=12&cardUnit=3` survives a refresh and can be pasted to a
   * colleague who teaches the same unit. BOTH ids are needed: risk is
   * computed per unit, so student 12 has a different verdict in every
   * unit they are enrolled in and `?student=12` alone would not
   * identify a card.
   *
   * The search params are the single source of truth here — keeping a
   * parallel useState would let the two drift apart on a back button.
   */
  const [searchParams, setSearchParams] = useSearchParams();

  const cardTarget = useMemo<StudentCardTarget | null>(() => {
    const studentId = Number(searchParams.get("student"));
    const cardUnitId = Number(searchParams.get("cardUnit"));
    // Number("") is 0 and Number(null) is 0, so a falsy check rejects
    // both a missing param and a malformed one without a separate guard.
    if (!studentId || !cardUnitId) return null;
    return { studentId, unitId: cardUnitId };
  }, [searchParams]);

  const openCard = useCallback(
    (student: DashboardStudent) => {
      setSearchParams(
        (current) => {
          const next = new URLSearchParams(current);
          next.set("student", String(student.student_id));
          next.set("cardUnit", String(student.unit_id));
          return next;
        },
        // replace, so closing the card doesn't require pressing Back
        // once per student the lecturer happened to open.
        { replace: true },
      );
    },
    [setSearchParams],
  );

  const closeCard = useCallback(() => {
    setSearchParams(
      (current) => {
        const next = new URLSearchParams(current);
        next.delete("student");
        next.delete("cardUnit");
        return next;
      },
      { replace: true },
    );
  }, [setSearchParams]);

  const units = useMemo(() => data?.units ?? [], [data]);
  const students = useMemo(() => data?.students ?? [], [data]);

  /**
   * Unit lookup for the assessment denominator and the CSV. Built once
   * per payload rather than per row — `assessmentProgressOf` runs for
   * every visible row on every render, and a linear find inside it
   * would make that O(rows × units).
   */
  const unitsById = useMemo(
    () => new Map(units.map((unit) => [unit.id, unit])),
    [units],
  );

  // Subject filter first. Everything below — including the tab counts —
  // describes the selected subject only.
  const inSubject = useMemo(() => filterByUnit(students, unitId), [students, unitId]);

  const counts = useMemo(() => countsByBucket(inSubject), [inSubject]);

  const filtered = useMemo(
    () => searchStudents(filterByBucket(inSubject, bucket), search),
    [inSubject, bucket, search],
  );

  const sorted = useMemo(
    () => sortStudents(filtered, sortKey, direction, unitsById),
    [filtered, sortKey, direction, unitsById],
  );

  /**
   * Whether the Weekly Tut column is rendered.
   *
   * Across ALL subjects it always is: some units run tutorials and some
   * don't, and hiding the column because one unit lacks it would hide
   * real data for every other unit on screen. Those rows simply read
   * "—".
   *
   * Once a single subject is selected the question becomes answerable —
   * this unit either runs tutorials or it doesn't — and a column of
   * nothing but dashes gets dropped. A dash column reads as a cohort
   * that stopped submitting, which is a much worse lie than an absent
   * column.
   *
   * Keyed to the SUBJECT FILTER, never to the visible page, so the
   * column cannot appear and vanish as the lecturer pages through.
   */
  const showTutorial = useMemo(() => {
    if (unitId === null) return true;
    const unit = unitsById.get(unitId);
    return (unit?.criteria ?? []).some((c) => c.category === "weekly_tut");
  }, [unitId, unitsById]);

  const totalPages = pageCount(sorted.length, PAGE_SIZE);

  /**
   * Clamped rather than trusted.
   *
   * Every filter setter below already returns to page 1, but a refetch
   * can shrink the cohort while a later page is open — a student is
   * un-enrolled, or the analysis is re-run. Clamping during render
   * means the table can never show a blank page it has no rows for, and
   * needs no effect to correct itself one render later.
   */
  const safePage = Math.min(page, totalPages);
  const visible = useMemo(() => pageSlice(sorted, safePage, PAGE_SIZE), [sorted, safePage]);

  /**
   * Every filter change returns to page 1.
   *
   * Without this: the lecturer is on page 4, types a search, six
   * results come back — and they stare at an empty table wondering
   * whether the search broke. Handled in the setters rather than in an
   * effect, so there is no second render pass and no blank flash.
   */
  function changeBucket(next: RiskBucket | null) {
    setBucket(next);
    setPage(1);
  }

  function changeUnit(next: number | null) {
    setUnitId(next);
    setPage(1);
  }

  function changeSearch(next: string) {
    setSearch(next);
    setPage(1);
  }

  function toggleSort(key: SortKey) {
    if (key === sortKey) {
      setDirection((current) => (current === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      // Ascending on a fresh column: risk ascends worst-first (severity
      // rank 0 is high risk), and every metric column reads naturally
      // low-to-high, which is where the concerning students are anyway.
      setDirection("asc");
    }
    setPage(1);
  }

  function clearFilters() {
    setBucket(null);
    setUnitId(null);
    setSearch("");
    setPage(1);
  }

  function exportCsv() {
    // `sorted`, not `visible` — the export covers every filtered row in
    // the order shown, not just the eight currently rendered.
    const selectedUnit = unitId === null ? null : (unitsById.get(unitId)?.unit_code ?? null);
    downloadCsv(toCsv(sorted, unitsById), csvFilename(selectedUnit));
  }

  if (isLoading) {
    return (
      <div className="px-6 py-8">
        <div className="mx-auto max-w-6xl animate-pulse">
          <div className="mb-6 h-9 w-64 rounded bg-stone-200" />
          <div className="mb-4 h-14 w-full rounded-xl bg-stone-200" />
          <div className="h-96 w-full rounded-2xl bg-stone-200" />
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="px-6 py-8">
        <div className="mx-auto max-w-md rounded-2xl border border-stone-200 bg-white p-8 text-center">
          <CircleAlert className="mx-auto h-8 w-8 text-stone-300" aria-hidden="true" />
          <h1 className="mt-3 text-base font-semibold text-stone-900">
            Couldn't load your students
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

  /**
   * Three distinct empty states, because each needs a different action
   * from a different person:
   *
   *  1. No units — an ADMINISTRATOR must assign one. Offering the
   *     lecturer a button they cannot use would be worse than useless.
   *  2. Units but no enrolments — the LECTURER imports or adds data.
   *  3. Enrolments but no matches — the lecturer clears their filters.
   *
   * Collapsing these into one "no students found" would leave a
   * lecturer with an unassigned account waiting for data that can never
   * arrive.
   */
  if (units.length === 0) {
    return (
      <div className="px-6 py-8">
        <div className="mx-auto max-w-2xl">
          <header className="mb-6">
            <h1 className="flex items-center gap-2 text-xl font-semibold text-stone-900">
              <Users className="h-5 w-5 text-stone-400" aria-hidden="true" />
              Students
            </h1>
          </header>

          <div className="rounded-2xl border border-dashed border-stone-300 bg-white p-10 text-center">
            <p className="text-sm text-stone-500">
              An administrator assigns units to lecturers. Once you're assigned one, the
              students enrolled in it will appear here.
            </p>
          </div>
        </div>
      </div>
    );
  }

  const distinctStudents = new Set(students.map((student) => student.student_id)).size;

  const emptyMessage =
    students.length === 0
      ? "No students are enrolled in your units yet. Open a unit to import a cohort or add a student manually."
      : "No students match the current filters.";

  return (
    <div className="px-6 py-8">
      <div className="mx-auto max-w-6xl">
        <StudentsToolbar
          enrolmentCount={students.length}
          studentCount={distinctStudents}
          unitCount={units.length}
          checkpointWeek={data?.checkpoint_week ?? 8}
        />

        <div className="mb-4">
          <RiskTabs
            counts={counts}
            total={inSubject.length}
            active={bucket}
            onChange={changeBucket}
          />
        </div>

        <div className="mb-5">
          <StudentsFilterBar
            search={search}
            onSearchChange={changeSearch}
            units={units}
            unitId={unitId}
            onUnitChange={changeUnit}
            resultCount={sorted.length}
          />
        </div>

        <StudentsTable
          rows={visible}
          filteredCount={sorted.length}
          unitsById={unitsById}
          sortKey={sortKey}
          direction={direction}
          onSort={toggleSort}
          page={safePage}
          totalPages={totalPages}
          onPageChange={setPage}
          onExport={exportCsv}
          emptyMessage={emptyMessage}
          // Only offered when clearing would actually change something.
          onClearFilters={
            students.length > 0 && (bucket !== null || unitId !== null || search !== "")
              ? clearFilters
              : undefined
          }
          onSelectStudent={openCard}
          showTutorial={showTutorial}
        />

        {/* Mounted only while a card is open, so its focus trap, scroll
            lock and query all tear down cleanly on close rather than
            lingering behind a hidden dialog. */}
        {cardTarget && (
          <StudentCard
            // Keyed on the target so switching students remounts the
            // dialog: the notes textarea gets fresh state instead of
            // carrying one student's draft into another's card.
            key={`${cardTarget.studentId}-${cardTarget.unitId}`}
            target={cardTarget}
            onClose={closeCard}
            checkpointWeek={data?.checkpoint_week ?? 8}
          />
        )}
      </div>
    </div>
  );
}