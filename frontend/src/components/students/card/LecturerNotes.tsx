import { useState } from "react";
import { Check, Loader2, NotebookPen, TriangleAlert } from "lucide-react";
import { formatDateTime } from "../../../utils/studentCard";

interface LecturerNotesProps {
  savedBody: string;
  savedAt: string | null;
  onSave: (body: string) => void;
  isSaving: boolean;
  isError: boolean;
  justSaved: boolean;
}

export default function LecturerNotes({
  savedBody,
  savedAt,
  onSave,
  isSaving,
  isError,
  justSaved,
}: LecturerNotesProps) {
  const [draft, setDraft] = useState(savedBody);
  const dirty = draft !== savedBody;

  function commit() {
    if (dirty) onSave(draft);
  }

  return (
    <section>
      <div className="mb-2 flex items-center justify-between gap-3">
        <h3 className="flex items-center gap-2 text-sm font-semibold text-stone-900">
          <NotebookPen className="h-4 w-4 text-stone-400" aria-hidden="true" />
          Your notes
        </h3>

        <div className="flex items-center gap-2 text-[11px]">
          {isSaving && (
            <span className="inline-flex items-center gap-1 text-stone-400">
              <Loader2 className="h-3 w-3 animate-spin" aria-hidden="true" />
              Saving
            </span>
          )}

          {!isSaving && justSaved && !dirty && (
            <span className="inline-flex items-center gap-1 text-green-700">
              <Check className="h-3 w-3" aria-hidden="true" />
              Saved
            </span>
          )}

          {!isSaving && dirty && <span className="text-amber-700">Unsaved changes</span>}
        </div>
      </div>

      <textarea
        value={draft}
        onChange={(event) => setDraft(event.target.value)}
        onBlur={commit}
        rows={4}
        placeholder="Anything worth remembering about this student — a conversation, an arrangement, context the numbers don't carry."
        aria-label="Your notes about this student"
        className="w-full resize-y rounded-xl border border-stone-200 bg-white p-3 text-sm leading-relaxed text-stone-800 placeholder:text-stone-400 focus:border-stone-400 focus:outline-none focus:ring-2 focus:ring-stone-200"
      />

      <div className="mt-2 flex flex-wrap items-center justify-between gap-2">
        <p className="text-[11px] text-stone-400">
          {isError ? (
            <span className="inline-flex items-center gap-1 text-red-600">
              <TriangleAlert className="h-3 w-3" aria-hidden="true" />
              Couldn't save — your text is still here, try again.
            </span>
          ) : savedAt ? (
            `Last saved ${formatDateTime(savedAt)}`
          ) : (
            "Only you can see these. They survive re-running the analysis."
          )}
        </p>

        <button
          type="button"
          onClick={commit}
          disabled={!dirty || isSaving}
          className="rounded-lg bg-stone-900 px-3.5 py-1.5 text-xs font-medium text-white transition hover:bg-stone-700 disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-stone-900"
        >
          Save note
        </button>
      </div>
    </section>
  );
}
