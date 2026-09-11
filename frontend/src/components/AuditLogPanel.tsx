import { useState } from "react";
import { ChevronDown, ChevronRight, ScrollText, ShieldAlert } from "lucide-react";
import { useAuditActions, useAuditEvents } from "../hooks/useAudit";
import type { AuditEvent } from "../types/audit";

/**
 * The admin's read-only view of the audit log.
 *
 * There is no control on this panel that writes anything, and that is
 * the point rather than an omission - see app/api/routes/audit.py.
 */

const RANGES: { label: string; days: number | null }[] = [
  { label: "All time", days: null },
  { label: "Last 7 days", days: 7 },
  { label: "Last 30 days", days: 30 },
  { label: "Last 90 days", days: 90 },
];

/** Colour carries the action, so a page of rows is scannable without reading. */
const TONE: Record<string, string> = {
  "threshold.changed": "bg-amber-100 text-amber-800",
  "criteria.unlocked": "bg-violet-100 text-violet-800",
  "criteria.shape_replaced": "bg-blue-100 text-blue-800",
  "verdict.overridden": "bg-rose-100 text-rose-800",
};

function stamp(value: string | null): string {
  if (!value) return "-";
  // The API sends naive UTC; the browser renders it wherever the reader
  // is. Hand-formatting this would be a fourth place in the project
  // reimplementing a date.
  const date = new Date(value.endsWith("Z") ? value : `${value}Z`);
  return date.toLocaleString(undefined, {
    day: "numeric", month: "short", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

/** Pretty-prints a stored snapshot, falling back to the raw text if it isn't JSON. */
function Snapshot({ label, json }: { label: string; json: string | null }) {
  if (!json) return null;
  let body = json;
  try {
    body = JSON.stringify(JSON.parse(json), null, 2);
  } catch {
    // Left as-is. A snapshot that failed to serialise is still evidence,
    // and hiding it because it will not parse would discard the one row
    // most worth looking at.
  }
  return (
    <div className="min-w-0 flex-1">
      <p className="mb-1 text-[11px] font-medium uppercase tracking-wide text-stone-400">{label}</p>
      <pre className="overflow-x-auto rounded-lg bg-stone-900 p-3 text-[11px] leading-relaxed text-stone-100">
        {body}
      </pre>
    </div>
  );
}

function Row({ event }: { event: AuditEvent }) {
  const [open, setOpen] = useState(false);
  const Chevron = open ? ChevronDown : ChevronRight;
  const hasDetail = Boolean(event.before_state || event.after_state || event.ip_address);

  return (
    <li className="border-b border-stone-100 last:border-b-0">
      <button
        type="button"
        onClick={() => hasDetail && setOpen(!open)}
        className="flex w-full items-start gap-3 px-4 py-3 text-left hover:bg-stone-50"
        aria-expanded={open}
      >
        <Chevron
          className={`mt-0.5 h-4 w-4 shrink-0 ${hasDetail ? "text-stone-400" : "text-transparent"}`}
          aria-hidden="true"
        />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${TONE[event.action] ?? "bg-stone-100 text-stone-700"}`}>
              {event.action_label}
            </span>
            {event.unit_code && (
              <span className="text-xs font-medium text-stone-600">{event.unit_code}</span>
            )}
            <span className="text-xs text-stone-400">{stamp(event.occurred_at)}</span>
          </div>

          {/* The server's sentence, printed verbatim. Rebuilding it from
              the snapshots here would mean the log reads differently in
              the table than it does in an export. */}
          <p className="mt-1 text-sm text-stone-800">{event.summary}</p>

          <p className="mt-0.5 text-xs text-stone-500">
            {event.actor_name ?? "Unknown actor"}
            {event.actor_email && <span className="text-stone-400"> · {event.actor_email}</span>}
            {event.actor_role && <span className="text-stone-400"> · {event.actor_role}</span>}
            {/* Says plainly that the person is gone rather than showing
                a blank where an account used to be. */}
            {event.actor_id === null && (
              <span className="ml-1 text-amber-700">(account since deleted)</span>
            )}
          </p>
        </div>
      </button>

      {open && (
        <div className="space-y-3 bg-stone-50 px-4 pb-4 pl-11">
          <div className="flex flex-col gap-3 sm:flex-row">
            <Snapshot label="Before" json={event.before_state} />
            <Snapshot label="After" json={event.after_state} />
          </div>
          <p className="text-[11px] text-stone-400">
            {event.ip_address ? `Requested from ${event.ip_address}` : "No source address recorded"}
            {event.entity_type && ` · ${event.entity_type} #${event.entity_id ?? "?"}`}
          </p>
        </div>
      )}
    </li>
  );
}

export default function AuditLogPanel() {
  const [action, setAction] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [days, setDays] = useState<number | null>(null);
  const [page, setPage] = useState(1);

  const actions = useAuditActions();
  const events = useAuditEvents({ action, search, days, page });

  const items = events.data?.items ?? [];
  const total = events.data?.total ?? 0;
  const pages = Math.max(1, Math.ceil(total / (events.data?.page_size ?? 25)));

  function reset<T>(setter: (value: T) => void) {
    return (value: T) => {
      setter(value);
      setPage(1);
    };
  }

  return (
    <section className="overflow-hidden rounded-2xl border border-stone-200 bg-white">
      <header className="border-b border-stone-200 px-5 py-4">
        <h2 className="flex items-center gap-2 text-base font-semibold text-stone-900">
          <ScrollText className="h-4 w-4" aria-hidden="true" />
          Audit log ({total})
        </h2>
        <p className="mt-1 text-xs text-stone-500">
          Every act that changed the basis of a judgement about a student: pass
          marks, unit shapes, unlocks and verdict overrides. Read-only — entries
          are written by the system, never by hand.
        </p>

        <div className="mt-3 flex flex-wrap gap-2">
          <input
            value={search}
            onChange={(event) => reset(setSearch)(event.target.value)}
            placeholder="Search person, unit or student"
            className="min-w-[200px] flex-1 rounded-xl border border-stone-200 px-3 py-2 text-sm"
          />
          <select
            value={action ?? "all"}
            onChange={(event) => reset(setAction)(event.target.value === "all" ? null : event.target.value)}
            className="rounded-xl border border-stone-200 px-3 py-2 text-sm"
          >
            <option value="all">All actions</option>
            {(actions.data ?? []).map((item) => (
              <option key={item.key} value={item.key}>{item.label}</option>
            ))}
          </select>
          <select
            value={String(days ?? "all")}
            onChange={(event) => reset(setDays)(event.target.value === "all" ? null : Number(event.target.value))}
            className="rounded-xl border border-stone-200 px-3 py-2 text-sm"
          >
            {RANGES.map((range) => (
              <option key={range.label} value={String(range.days ?? "all")}>{range.label}</option>
            ))}
          </select>
        </div>

        {/* The explanation of the selected action, served by the API
            beside the constant that names it. An audit log nobody can
            interpret is a table, not a control. */}
        {action && (
          <p className="mt-2 text-xs text-stone-500">
            {(actions.data ?? []).find((item) => item.key === action)?.description}
          </p>
        )}
      </header>

      {events.isLoading && items.length === 0 ? (
        <p className="p-8 text-center text-sm text-stone-500">Loading…</p>
      ) : items.length === 0 ? (
        <div className="p-8 text-center">
          <ShieldAlert className="mx-auto mb-2 h-5 w-5 text-stone-300" aria-hidden="true" />
          {/* An empty log is genuinely ambiguous - nothing has happened,
              or nothing matches the filter. Saying which stops a reader
              concluding the wrong one. */}
          <p className="text-sm text-stone-500">
            {action || search || days
              ? "No entries match these filters."
              : "Nothing has been recorded yet. Entries appear when someone changes a pass mark, a unit shape, or a verdict."}
          </p>
        </div>
      ) : (
        <ul>{items.map((event) => <Row key={event.id} event={event} />)}</ul>
      )}

      <footer className="flex items-center justify-between border-t border-stone-200 px-4 py-3 text-xs text-stone-500">
        <span>Page {page} of {pages}</span>
        <span className="space-x-3">
          <button type="button" disabled={page === 1} onClick={() => setPage(page - 1)} className="disabled:text-stone-300">
            Previous
          </button>
          <button type="button" disabled={page >= pages} onClick={() => setPage(page + 1)} className="disabled:text-stone-300">
            Next
          </button>
        </span>
      </footer>
    </section>
  );
}