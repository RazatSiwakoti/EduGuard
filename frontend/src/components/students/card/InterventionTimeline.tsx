import { useState } from "react";
import { CalendarClock, Mail, Plus, Save } from "lucide-react";
import type { InterventionCreate, InterventionDetail } from "../../../types/studentDetail";

interface Props {
  interventions: InterventionDetail[];
  onRecord: (payload: InterventionCreate) => void;
  isSaving: boolean;
}

export default function InterventionTimeline({ interventions, onRecord, isSaving }: Props) {
  const [open, setOpen] = useState(false);
  const [kind, setKind] = useState<InterventionCreate["kind"]>("meeting");
  const [summary, setSummary] = useState("");
  const [followUp, setFollowUp] = useState("");

  function submit() {
    if (!summary.trim()) return;
    onRecord({
      kind,
      summary: summary.trim(),
      occurred_at: new Date().toISOString(),
      ...(followUp ? { follow_up_on: followUp } : {}),
    });
    setSummary("");
    setFollowUp("");
    setOpen(false);
  }

  return (
    <section>
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-stone-900">Intervention timeline</h3>
        <button type="button" onClick={() => setOpen((value) => !value)} className="inline-flex items-center gap-1 rounded-lg bg-stone-900 px-3 py-1.5 text-xs font-medium text-white">
          <Plus className="h-3 w-3" /> Record an intervention
        </button>
      </div>
      {open && (
        <div className="mb-4 space-y-2 rounded-xl border border-stone-200 bg-stone-50 p-3">
          <div className="flex gap-2">
            <select value={kind} onChange={(event) => setKind(event.target.value as InterventionCreate["kind"])} className="rounded-lg border border-stone-200 bg-white px-2 py-1.5 text-xs">
              {["meeting", "email", "phone", "referral", "extension", "other"].map((value) => <option key={value}>{value}</option>)}
            </select>
            <input type="date" value={followUp} onChange={(event) => setFollowUp(event.target.value)} className="rounded-lg border border-stone-200 bg-white px-2 py-1.5 text-xs" aria-label="Follow-up date" />
          </div>
          <textarea value={summary} onChange={(event) => setSummary(event.target.value)} rows={2} placeholder="What happened?" className="w-full rounded-lg border border-stone-200 bg-white p-2 text-sm" />
          <button type="button" disabled={isSaving || !summary.trim()} onClick={submit} className="inline-flex items-center gap-1 rounded-lg bg-stone-900 px-3 py-1.5 text-xs text-white disabled:opacity-40"><Save className="h-3 w-3" /> Save</button>
        </div>
      )}
      {interventions.length === 0 ? <p className="text-xs text-stone-400">No interventions recorded yet.</p> : (
        <ol className="space-y-3 border-l border-stone-200 pl-4">
          {interventions.map((item) => (
            <li key={item.id} className="relative">
              <span className="absolute -left-[1.35rem] top-1 flex h-4 w-4 items-center justify-center rounded-full bg-white text-stone-400">
                {item.automatic ? <Mail className="h-3 w-3" /> : <CalendarClock className="h-3 w-3" />}
              </span>
              <p className="text-xs font-medium text-stone-700">{item.kind} · {new Date(item.occurred_at).toLocaleDateString()}</p>
              <p className="text-sm text-stone-600">{item.summary}</p>
              {item.follow_up_on && <p className="text-[11px] text-amber-700">Follow-up due {item.follow_up_on}</p>}
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
