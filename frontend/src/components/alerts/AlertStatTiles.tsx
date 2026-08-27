import { CircleAlert, Clock, Mail, MailCheck } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { AlertCounters } from "../../types/alerts";

function Tile({ icon: Icon, value, label, tone }: { icon: LucideIcon; value: number; label: string; tone: string }) {
  return <div className="overflow-hidden rounded-2xl border border-stone-200 bg-white"><div className={`h-1 ${tone}`} /><div className="flex items-center gap-3 p-4"><Icon className="h-5 w-5 text-stone-500" aria-hidden="true" /><div><p className="text-2xl font-semibold tabular-nums text-stone-900">{value}</p><p className="text-xs text-stone-500">{label}</p></div></div></div>;
}

export default function AlertStatTiles({ counters }: { counters: AlertCounters }) {
  return <div className="grid grid-cols-2 gap-3 lg:grid-cols-4"><Tile icon={Mail} value={counters.total} label="Total messages" tone="bg-blue-500" /><Tile icon={MailCheck} value={counters.sent} label="Sent" tone="bg-green-500" /><Tile icon={Clock} value={counters.queued} label="In queue" tone="bg-amber-400" /><Tile icon={CircleAlert} value={counters.failed} label="Failed" tone="bg-red-500" /></div>;
}
