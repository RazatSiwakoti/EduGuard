import { useState } from "react";
import { CircleAlert, Clock, Mail, MailCheck, UserCheck } from "lucide-react";
import type { AlertLogItem, AlertLogPage, AlertStatus } from "../../types/alerts";

interface Props { data: AlertLogPage | undefined; isLoading: boolean; status: AlertStatus | null; onStatusChange: (status: AlertStatus | null) => void; search: string; onSearchChange: (value: string) => void; page: number; onPageChange: (page: number) => void; }
const icons = { sent: MailCheck, queued: Clock, failed: CircleAlert };

// Locale-aware and timezone-aware by construction: the API sends UTC and
// the browser renders it where the lecturer is sitting. Hand-formatting
// this would be the third place in the project to reimplement a date.
const stamp = (value: string) => new Date(value).toLocaleString(undefined, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });

/**
 * One cell, three genuinely different meanings - which is why this is a
 * function and not a ternary buried in the row.
 *
 *   a summary       - cannot be acknowledged, nobody should look for one
 *   not yet sent    - the student has not been given the chance yet
 *   sent, no receipt - the only case that is actually an open question
 */
function AckCell({ item }: { item: AlertLogItem }) {
  // Plain text, NOT an icon plus a Tailwind `sr-only` label. That was
  // the first version, and it dragged the whole page sideways at 420px:
  // `sr-only` is `position: absolute`, this table has no positioned
  // ancestor, so the hidden span resolved against the initial
  // containing block and ESCAPED the `overflow-x-auto` wrapper - the
  // one element on the page that the scroll container could not clip.
  // Caught by rendering at 420px and measuring, not by reading it.
  if (item.kind !== "student_alert") return <span className="text-xs text-stone-300" title="Weekly summaries are not acknowledged">n/a</span>;
  if (item.acknowledged_at) return <span className="inline-flex items-center gap-1 text-xs text-teal-700" title={`Confirmed received on ${stamp(item.acknowledged_at)}`}><UserCheck className="h-3.5 w-3.5" aria-hidden="true" />{stamp(item.acknowledged_at)}</span>;
  if (item.status !== "sent") return <span className="text-xs text-stone-400">not sent yet</span>;
  return <span className="text-xs text-stone-500">awaiting</span>;
}
export default function AlertLogTable({ data, isLoading, status, onStatusChange, search, onSearchChange, page, onPageChange }: Props) {
  const [expanded, setExpanded] = useState<number | null>(null); const items = data?.items ?? []; const pages = Math.max(1, Math.ceil((data?.total ?? 0) / (data?.page_size ?? 20)));
  return <section className="overflow-hidden rounded-2xl border border-stone-200 bg-white"><header className="flex flex-wrap items-center justify-between gap-3 border-b border-stone-200 px-5 py-4"><h2 className="flex items-center gap-2 text-base font-semibold text-stone-900"><Mail className="h-4 w-4" />Email notification log ({data?.total ?? 0})</h2><div className="flex gap-2"><input value={search} onChange={(event) => onSearchChange(event.target.value)} placeholder="Search log" className="rounded-xl border border-stone-200 px-3 py-2 text-sm" /><select value={status ?? "all"} onChange={(event) => onStatusChange(event.target.value === "all" ? null : event.target.value as AlertStatus)} className="rounded-xl border border-stone-200 px-3 py-2 text-sm"><option value="all">All</option><option value="sent">Sent</option><option value="queued">Queued</option><option value="failed">Failed</option></select></div></header>{isLoading && items.length === 0 ? <p className="p-8 text-center text-sm text-stone-500">Loading...</p> : items.length === 0 ? <p className="p-8 text-center text-sm text-stone-500">No messages match this filter.</p> : <div className="overflow-x-auto"><table className="w-full min-w-[820px] text-left text-sm"><thead className="bg-stone-50 text-xs uppercase text-stone-500"><tr><th className="px-4 py-3">Recipient</th><th className="px-4 py-3">Unit</th><th className="px-4 py-3">Subject</th><th className="px-4 py-3">Status</th><th className="px-4 py-3">Acknowledged</th></tr></thead><tbody className="divide-y divide-stone-100">{items.map((item: AlertLogItem) => { const Icon = icons[item.status]; return <tr key={item.id} className="hover:bg-stone-50"><td className="px-4 py-3"><button type="button" onClick={() => setExpanded(expanded === item.id ? null : item.id)} className="text-left"><strong>{item.student_name ?? "Weekly summary"}</strong><br /><span className="text-xs text-stone-500">{item.recipient_email}</span></button></td><td className="px-4 py-3">{item.unit_code ?? "-"}</td><td className="px-4 py-3">{item.subject}{expanded === item.id && <pre className="mt-2 whitespace-pre-wrap text-xs text-stone-600">{item.body}</pre>}</td><td className="px-4 py-3"><span className="inline-flex items-center gap-1 text-xs"><Icon className="h-3.5 w-3.5" />{item.status}</span></td><td className="px-4 py-3"><AckCell item={item} /></td></tr>; })}</tbody></table></div>}<footer className="flex justify-between border-t border-stone-200 px-4 py-3 text-xs text-stone-500"><span>Page {page} of {pages}</span><span className="space-x-2"><button type="button" disabled={page === 1} onClick={() => onPageChange(page - 1)}>Previous</button><button type="button" disabled={page >= pages} onClick={() => onPageChange(page + 1)}>Next</button></span></footer></section>;
}
