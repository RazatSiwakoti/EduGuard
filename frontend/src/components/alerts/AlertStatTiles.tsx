import { CircleAlert, Clock, Mail, MailCheck, UserCheck } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { AlertCounters } from "../../types/alerts";

function Tile({ icon: Icon, value, label, tone, hint }: { icon: LucideIcon; value: number; label: string; tone: string; hint?: string }) {
  return <div className="overflow-hidden rounded-2xl border border-stone-200 bg-white"><div className={`h-1 ${tone}`} /><div className="flex items-center gap-3 p-4"><Icon className="h-5 w-5 text-stone-500" aria-hidden="true" /><div><p className="text-2xl font-semibold tabular-nums text-stone-900">{value}</p><p className="text-xs text-stone-500">{label}</p>{hint && <p className="text-[11px] text-stone-400">{hint}</p>}</div></div></div>;
}

export default function AlertStatTiles({ counters }: { counters: AlertCounters }) {
  // Phrased as "of N sent", never as a percentage. A percentage over a
  // handful of messages reads as a score for the lecturer, and this is
  // not one - a student who never opens their email is not a lecturer
  // who failed to send. The denominator is sent student alerts only,
  // so a queued or bounced message can't be counted as a student
  // ignoring a notice that never reached them.
  const hint = counters.acknowledgeable > 0 ? `of ${counters.acknowledgeable} sent` : "none sent yet";
  return <div className="grid grid-cols-2 gap-3 lg:grid-cols-5"><Tile icon={Mail} value={counters.total} label="Total messages" tone="bg-blue-500" /><Tile icon={MailCheck} value={counters.sent} label="Sent" tone="bg-green-500" /><Tile icon={UserCheck} value={counters.acknowledged} label="Acknowledged" tone="bg-teal-500" hint={hint} /><Tile icon={Clock} value={counters.queued} label="In queue" tone="bg-amber-400" /><Tile icon={CircleAlert} value={counters.failed} label="Failed" tone="bg-red-500" /></div>;
}
