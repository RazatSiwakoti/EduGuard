import { useEffect, useRef, useState } from "react";
import {
  Activity,
  BookOpen,
  CircleAlert,
  ClipboardList,
  Info,
  Mail,
  OctagonAlert,
  TrendingDown,
  TriangleAlert,
  X,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { StudentCardTarget } from "../../../types/studentDetail";
import { BUCKET_LABELS, getBucket } from "../../../utils/dashboardAggregations";
import type { RiskBucket } from "../../../types/dashboard";
import {
  attendanceWeeks,
  formatDateTime,
  formatMonthYear,
  assessmentPercent,
  groupCriteria,
  riskIndicators,
  tutorialWeeks,
} from "../../../utils/studentCard";
import {
  useSaveStudentNote,
  useStudentDetail,
  useSubmitReview,
} from "../../../hooks/useStudentDetail";
import type { RiskTier } from "../../../types/dashboard";
import { BUCKET_ICONS } from "../../dashboard/BucketBadge";
import { BUCKET_STYLES } from "../../dashboard/chartTheme";
import AttendanceStrip from "./AttendanceStrip";
import EnginePanels from "./EnginePanels";
import LecturerNotes from "./LecturerNotes";
import MetricBar from "./MetricBar";
import ReviewPanel from "./ReviewPanel";
import TutorialBars from "./TutorialBars";

interface StudentCardProps {
  target: StudentCardTarget;
  onClose: () => void;
  checkpointWeek?: number;
}

/** Focusable descendants, for the tab trap. */
const FOCUSABLE =
  'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

const SEVERITY_ICONS: Record<string, LucideIcon> = {
  critical: OctagonAlert,
  warning: TriangleAlert,
  info: Info,
};

const SEVERITY_STYLES: Record<string, string> = {
  critical: "border-l-red-500 bg-red-50/70 text-red-900",
  warning: "border-l-amber-400 bg-amber-50/70 text-amber-900",
  info: "border-l-stone-300 bg-stone-50 text-stone-700",
};

interface StatTileProps {
  icon: LucideIcon;
  value: string;
  label: string;
}

/** Declared at module level — a component defined during render is a new
 *  type every render, which remounts it and trips the React Compiler. */
function StatTile({ icon: Icon, value, label }: StatTileProps) {
  return (
    <div className="rounded-xl border border-stone-200 bg-white p-3">
      <Icon className="h-4 w-4 text-stone-400" aria-hidden="true" />
      <p className="mt-1.5 text-lg font-semibold tabular-nums text-stone-900">{value}</p>
      <p className="text-[11px] text-stone-500">{label}</p>
    </div>
  );
}

/**
 * The student card — one student, one unit, the whole picture.
 *
 * A DIALOG, NOT A PAGE, because it is a detour: a lecturer scanning the
 * table opens a student, decides something, and goes back to scanning.
 * A route change would lose their scroll position, their filters and
 * their page number every single time.
 *
 * It is still deep-linkable through `?student=` on the parent page, so
 * a refresh — or a link pasted to a colleague who teaches the same unit
 * — reopens the same card.
 *
 * Accessibility here is not decoration. A dialog that traps nothing
 * lets a keyboard user tab straight out into the table behind it and
 * carry on interacting with content they cannot see. So: focus moves in
 * on open, Tab cycles inside, Escape closes, the background is inert to
 * screen readers via aria-modal, the page behind cannot scroll, and
 * focus returns to the element that opened it.
 */
export default function StudentCard({
  target,
  onClose,
  checkpointWeek = 8,
}: StudentCardProps) {
  const { data, isLoading, isError, error } = useStudentDetail(target, checkpointWeek);
  const saveNote = useSaveStudentNote(target, checkpointWeek);
  const submitReview = useSubmitReview(target, checkpointWeek);

  const dialogRef = useRef<HTMLDivElement | null>(null);
  const closeButtonRef = useRef<HTMLButtonElement | null>(null);
  // Remembered so focus can go back where it came from on close.
  const openerRef = useRef<Element | null>(null);

  const [justSaved, setJustSaved] = useState(false);

  useEffect(() => {
    openerRef.current = document.activeElement;

    // Lock the page behind the dialog. Without this, scrolling inside
    // the card chains to the body and the table drifts underneath.
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    // Focus the close button rather than the dialog itself: it is the
    // one control every user needs and the safest place to land.
    closeButtonRef.current?.focus();

    return () => {
      document.body.style.overflow = previousOverflow;
      // Only restore focus if the opener is still in the document —
      // it may have been unmounted by a filter change while the card
      // was open.
      const opener = openerRef.current;
      if (opener instanceof HTMLElement && document.contains(opener)) {
        opener.focus();
      }
    };
  }, []);

  /**
   * Escape and the tab trap, bound to the DOCUMENT rather than to the
   * dialog element.
   *
   * The obvious version — onKeyDown on the dialog div — has a bug that
   * shows up immediately in real use: press "Save note", the button
   * disables itself, the browser drops focus to <body> because a
   * disabled element cannot hold it, and from that moment Escape does
   * nothing and Tab walks straight out into the table behind. A dialog
   * whose keyboard handling depends on focus still being inside it is a
   * dialog that stops working the first time a control disables.
   *
   * Listening on the document fixes both: Escape always closes, and a
   * Tab pressed while focus has fallen outside is pulled back in rather
   * than escaping.
   */
  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.stopPropagation();
        onClose();
        return;
      }

      if (event.key !== "Tab") return;

      const dialog = dialogRef.current;
      if (!dialog) return;

      const focusable = dialog.querySelectorAll<HTMLElement>(FOCUSABLE);
      if (focusable.length === 0) return;

      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      const active = document.activeElement;

      // Focus fell outside the dialog (a control disabled itself, or a
      // click landed on the backdrop). Reel it back in.
      if (!(active instanceof HTMLElement) || !dialog.contains(active)) {
        event.preventDefault();
        (event.shiftKey ? last : first).focus();
        return;
      }

      // Wrap in both directions so Tab and Shift+Tab both stay inside.
      if (event.shiftKey && active === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && active === last) {
        event.preventDefault();
        first.focus();
      }
    }

    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  function handleSubmitReview(decision: RiskTier, comment: string) {
    submitReview.mutate({ decision, comment: comment.trim() || undefined });
  }

  function handleSaveNote(body: string) {
    saveNote.mutate(body, {
      onSuccess: () => {
        setJustSaved(true);
        window.setTimeout(() => setJustSaved(false), 2500);
      },
    });
  }

  const bucket: RiskBucket | null = data
    ? getBucket({
        analysed: data.analysed,
        requires_review: data.requires_review,
        final_tier: data.final_tier,
        // getBucket only reads these four fields; the cast keeps this
        // honest rather than fabricating a whole DashboardStudent.
      } as Parameters<typeof getBucket>[0])
    : null;

  const groups = data ? groupCriteria(data.criteria) : null;
  const indicators = data ? riskIndicators(data) : [];

  const markedAssessments =
    groups?.assessments.filter((item) => item.score !== null).length ?? 0;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-stone-900/40 p-4 backdrop-blur-sm sm:p-8"
      // Clicking the backdrop closes. The check that the click landed on
      // the backdrop itself stops a drag that ends outside the dialog
      // from closing it mid-selection.
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
      style={{ animation: "eduguard-fade-in 160ms ease-out" }}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label={data ? `${data.name}, ${data.unit_code}` : "Student details"}
        className="my-auto w-full max-w-2xl overflow-hidden rounded-2xl bg-stone-50 shadow-2xl"
        // A spring-ish overshoot on entry, and a straight fade for
        // anyone who has asked for reduced motion — handled in the
        // keyframes, see index.css.
        style={{ animation: "eduguard-card-in 260ms cubic-bezier(0.22, 1.2, 0.36, 1)" }}
      >
        {/* ---------------------------------------------------------- */}
        {/* Header                                                      */}
        {/* ---------------------------------------------------------- */}
        <header className="flex items-start justify-between gap-4 border-b border-stone-200 bg-white px-5 py-4">
          {isLoading || !data ? (
            <div className="h-12 w-56 animate-pulse rounded bg-stone-200" />
          ) : (
            <div className="flex min-w-0 items-center gap-3">
              <span
                className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-full text-sm font-semibold ring-1 ring-inset ${
                  bucket ? BUCKET_STYLES[bucket].pill : "bg-stone-100 text-stone-600"
                }`}
                aria-hidden="true"
              >
                {data.name
                  .trim()
                  .split(/\s+/)
                  .slice(0, 2)
                  .map((part) => part[0])
                  .join("")
                  .toUpperCase()}
              </span>

              <div className="min-w-0">
                <h2 className="truncate text-xl font-semibold text-stone-900">
                  {data.name}
                </h2>

                <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-stone-500">
                  {bucket && (
                    <span
                      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 font-medium uppercase tracking-wide ring-1 ring-inset ${BUCKET_STYLES[bucket].pill}`}
                    >
                      {(() => {
                        const Icon = BUCKET_ICONS[bucket];
                        return <Icon className="h-3 w-3" aria-hidden="true" />;
                      })()}
                      {BUCKET_LABELS[bucket]}
                    </span>
                  )}
                  <span className="font-medium text-stone-700">{data.unit_code}</span>
                  <span className="text-stone-300">·</span>
                  <span className="tabular-nums">{data.student_number}</span>
                  {data.program && (
                    <>
                      <span className="text-stone-300">·</span>
                      <span className="truncate">{data.program}</span>
                    </>
                  )}
                </div>
              </div>
            </div>
          )}

          <button
            ref={closeButtonRef}
            type="button"
            onClick={onClose}
            aria-label="Close student details"
            className="shrink-0 rounded-lg p-1.5 text-stone-400 transition hover:bg-stone-100 hover:text-stone-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-stone-400"
          >
            <X className="h-5 w-5" aria-hidden="true" />
          </button>
        </header>

        {/* ---------------------------------------------------------- */}
        {/* Body                                                        */}
        {/* ---------------------------------------------------------- */}
        <div className="max-h-[calc(100vh-13rem)] space-y-6 overflow-y-auto px-5 py-5">
          {isLoading && (
            <div className="space-y-3">
              {[0, 1, 2, 3].map((index) => (
                <div key={index} className="h-20 animate-pulse rounded-xl bg-stone-200" />
              ))}
            </div>
          )}

          {isError && (
            <div className="rounded-xl border border-stone-200 bg-white p-8 text-center">
              <CircleAlert className="mx-auto h-8 w-8 text-stone-300" aria-hidden="true" />
              <p className="mt-3 text-sm font-medium text-stone-900">
                Couldn't load this student
              </p>
              <p className="mt-1 text-sm text-stone-500">
                {error instanceof Error
                  ? error.message
                  : "Something went wrong reaching the server."}
              </p>
            </div>
          )}

          {data && groups && (
            <>
              {/* Contact + enrolment. Phone and "last active" from the
                  original design are absent because neither exists in
                  the schema — inventing them would have been the easy
                  part and the wrong one. */}
              <div className="grid gap-2 sm:grid-cols-2">
                <div className="flex items-center gap-2 rounded-xl border border-stone-200 bg-white px-3 py-2.5">
                  <Mail className="h-4 w-4 shrink-0 text-stone-400" aria-hidden="true" />
                  {data.email ? (
                    <a
                      href={`mailto:${data.email}`}
                      className="truncate text-sm text-stone-700 underline-offset-2 hover:underline"
                    >
                      {data.email}
                    </a>
                  ) : (
                    <span className="text-sm text-stone-400">No email on record</span>
                  )}
                </div>

                <div className="flex items-center gap-2 rounded-xl border border-stone-200 bg-white px-3 py-2.5">
                  <BookOpen className="h-4 w-4 shrink-0 text-stone-400" aria-hidden="true" />
                  <span className="truncate text-sm text-stone-700">
                    {data.unit_name}
                    {data.enrolled_at && (
                      <span className="text-stone-400">
                        {" "}
                        · enrolled {formatMonthYear(data.enrolled_at)}
                      </span>
                    )}
                  </span>
                </div>
              </div>

              {/* Three tiles from data that actually exists. The original
                  design's "Emails Sent" and "Forum Posts" have no
                  backing anywhere in this system. */}
              <div className="grid grid-cols-3 gap-2">
                <StatTile
                  icon={Activity}
                  value={
                    groups.moodle?.score != null
                      ? String(Math.round(groups.moodle.score))
                      : "—"
                  }
                  label="Moodle logins"
                />
                <StatTile
                  icon={ClipboardList}
                  value={
                    groups.assessments.length > 0
                      ? `${markedAssessments}/${groups.assessments.length}`
                      : "—"
                  }
                  label="Assessments marked"
                />
                <StatTile
                  icon={TrendingDown}
                  value={
                    groups.tutorial?.score != null
                      ? `${Math.round(groups.tutorial.score)}%`
                      : "—"
                  }
                  label="Tutorial completion"
                />
              </div>

              {/* ------------------------------------------------------ */}
              {/* Performance metrics                                    */}
              {/* ------------------------------------------------------ */}
              <section>
                <h3 className="mb-3 text-sm font-semibold text-stone-900">
                  Performance metrics
                </h3>

                <div className="space-y-4 rounded-xl border border-stone-200 bg-white p-4">
                  {groups.attendance && (
                    <MetricBar
                      label="Attendance"
                      value={groups.attendance.score}
                      threshold={groups.attendance.threshold}
                      scaleMax={100}
                    />
                  )}

                  {/* Each assessment on its own row rather than one
                      average. The average is what the ML model sees, but
                      a lecturer needs to know WHICH assessment was
                      missed — that is the one they can act on. */}
                  {groups.assessments.map((assessment) => (
                    <MetricBar
                      key={assessment.criteria_id}
                      label={assessment.name}
                      // NORMALISED, not raw. `threshold` is a percentage
                      // while an assessment mark is on its own scale —
                      // comparing 4 against 45 is the 7.4 bug wearing a
                      // different hat. The raw mark stays visible via
                      // rawLabel so nothing is hidden.
                      value={assessmentPercent(assessment.score, assessment.max_score)}
                      threshold={assessment.threshold}
                      scaleMax={100}
                      rawLabel={
                        assessment.score !== null && assessment.max_score !== 100
                          ? `${assessment.score} / ${assessment.max_score}`
                          : undefined
                      }
                    />
                  ))}

                  {/* Rendered only when the unit runs tutorials. A unit
                      without them should not show an empty row implying
                      the student failed to do something optional. */}
                  {groups.tutorial && (
                    <MetricBar
                      label="Weekly tutorials"
                      value={groups.tutorial.score}
                      threshold={groups.tutorial.threshold}
                      scaleMax={100}
                      hint="W2–W7 completion"
                    />
                  )}

                  {groups.moodle && (
                    <MetricBar
                      label="Moodle logins"
                      value={groups.moodle.score}
                      threshold={groups.moodle.threshold}
                      scaleMax={Math.max(groups.moodle.threshold * 2, 20)}
                      suffix=""
                      hint="raw login count, not a percentage"
                    />
                  )}

                  {groups.uncategorised.map((criterion) => (
                    <MetricBar
                      key={criterion.criteria_id}
                      label={criterion.name}
                      // Normalised on the same reasoning as assessments:
                      // an uncategorised criterion carries a max_score
                      // and a percentage threshold too.
                      value={assessmentPercent(criterion.score, criterion.max_score)}
                      threshold={criterion.threshold}
                      scaleMax={100}
                      rawLabel={
                        criterion.score !== null && criterion.max_score !== 100
                          ? `${criterion.score} / ${criterion.max_score}`
                          : undefined
                      }
                      hint="no category set — invisible to the ML model"
                    />
                  ))}
                </div>
              </section>

              {/* ------------------------------------------------------ */}
              {/* Weekly trend                                           */}
              {/* ------------------------------------------------------ */}
              {(groups.attendance || groups.tutorial) && (
                <section>
                  <h3 className="mb-3 text-sm font-semibold text-stone-900">
                    Week-by-week detail
                  </h3>

                  <div className="space-y-5 rounded-xl border border-stone-200 bg-white p-4">
                    {groups.attendance && (
                      <div>
                        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-stone-500">
                          Attendance · weeks 1–7
                        </p>
                        <AttendanceStrip weeks={attendanceWeeks(groups.attendance)} />
                      </div>
                    )}

                    {groups.tutorial && (
                      <div className={groups.attendance ? "border-t border-stone-100 pt-4" : ""}>
                        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-stone-500">
                          Weekly tutorials · weeks 2–7
                        </p>
                        <TutorialBars weeks={tutorialWeeks(groups.tutorial)} />
                      </div>
                    )}
                  </div>
                </section>
              )}

              {/* ------------------------------------------------------ */}
              {/* Risk indicators                                        */}
              {/* ------------------------------------------------------ */}
              <section>
                <h3 className="mb-3 text-sm font-semibold text-stone-900">
                  Why this student was flagged
                </h3>

                {indicators.length === 0 ? (
                  <p className="rounded-xl border border-stone-200 bg-white p-4 text-sm text-stone-500">
                    No criterion is below its threshold and no trend is declining.
                  </p>
                ) : (
                  <ul className="space-y-2">
                    {indicators.map((indicator) => {
                      const Icon = SEVERITY_ICONS[indicator.severity];
                      return (
                        <li
                          key={indicator.text}
                          className={`flex gap-2.5 rounded-lg border-l-[3px] px-3 py-2.5 text-sm leading-relaxed ${SEVERITY_STYLES[indicator.severity]}`}
                        >
                          <Icon className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
                          {indicator.text}
                        </li>
                      );
                    })}
                  </ul>
                )}

                {/* Every line above restates a number already on this
                    card. Nothing here is generated advice — see
                    riskIndicators() for why that boundary matters. */}
                <p className="mt-2 text-[11px] leading-relaxed text-stone-400">
                  Derived from this unit's criteria and thresholds. What to do about it is
                  your call — the system doesn't recommend interventions.
                </p>
              </section>

              {/* ------------------------------------------------------ */}
              {/* Lecturer notes                                         */}
              {/* ------------------------------------------------------ */}
              <LecturerNotes
                savedBody={data.note?.body ?? ""}
                savedAt={data.note?.updated_at ?? null}
                onSave={handleSaveNote}
                isSaving={saveNote.isPending}
                isError={saveNote.isError}
                justSaved={justSaved}
              />

              {/* ------------------------------------------------------ */}
              {/* Engines                                                */}
              {/* ------------------------------------------------------ */}
              <EnginePanels detail={data} />

              {/* ------------------------------------------------------ */}
              {/* Review                                                 */}
              {/* ------------------------------------------------------ */}
              {/* Deliberately AFTER the engine panels. The decision is
                  only defensible once the lecturer has the two verdicts
                  and their reasoning in front of them, so the control
                  sits below the evidence rather than above it. */}
              <ReviewPanel
                detail={data}
                onSubmit={handleSubmitReview}
                isSubmitting={submitReview.isPending}
                isError={submitReview.isError}
                error={submitReview.error}
              />
            </>
          )}
        </div>

        {/* ---------------------------------------------------------- */}
        {/* Footer                                                      */}
        {/* ---------------------------------------------------------- */}
        <footer className="flex flex-wrap items-center justify-between gap-3 border-t border-stone-200 bg-white px-5 py-3.5">
          <p className="text-[11px] text-stone-400">
            {data?.computed_at
              ? `Week ${data.checkpoint_week} checkpoint · last analysed ${formatDateTime(data.computed_at)}`
              : "Not yet analysed"}
          </p>

          <button
            type="button"
            onClick={onClose}
            className="rounded-xl bg-stone-900 px-5 py-2 text-sm font-medium text-white transition hover:bg-stone-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-stone-400"
          >
            Close
          </button>
        </footer>
      </div>
    </div>
  );
}