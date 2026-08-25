import { Info } from "lucide-react";
import type { IdentityMapping } from "../../types/ingestion";
import ColumnSelect from "./ColumnSelect";

interface StepIdentityProps {
  columns: string[];
  identity: IdentityMapping;
  onChange: (next: IdentityMapping) => void;
}

/**
 * Step 2 — which columns identify the student.
 *
 * Only student number and name are required. Student number is the
 * matching key: ingestion looks a student up by it, creating them if
 * they are new and enrolling them in this unit either way. A row with
 * no student number is skipped entirely, which is why it cannot be left
 * unmapped.
 *
 * Gender and age are optional but NOT decorative — they are real
 * features the ML model was trained on. Leaving them unmapped when the
 * file has them means those students get scored on less information
 * than students entered by hand, so the hint says so rather than
 * letting a lecturer skip them without knowing.
 */
export default function StepIdentity({
  columns,
  identity,
  onChange,
}: StepIdentityProps) {
  // Every column selected by another identity field, so each dropdown
  // can flag a column that is already spoken for.
  function usedByOthers(current: keyof IdentityMapping): Set<string> {
    const used = new Set<string>();
    (Object.keys(identity) as (keyof IdentityMapping)[]).forEach((key) => {
      if (key !== current && identity[key]) used.add(identity[key]);
    });
    return used;
  }

  function set(key: keyof IdentityMapping, value: string) {
    onChange({ ...identity, [key]: value });
  }

  return (
    <div className="space-y-5">
      <div className="rounded-lg border border-stone-200 bg-white p-5">
        <h3 className="text-sm font-semibold text-stone-900">Required</h3>
        <p className="mt-0.5 text-xs text-stone-500">
          Rows missing either of these are skipped and reported back to you.
        </p>

        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
          <ColumnSelect
            label="Student number"
            hint="The unique ID used to match or create each student"
            value={identity.student_number_col}
            columns={columns}
            onChange={(value) => set("student_number_col", value)}
            required
            usedElsewhere={usedByOthers("student_number_col")}
          />
          <ColumnSelect
            label="Full name"
            value={identity.name_col}
            columns={columns}
            onChange={(value) => set("name_col", value)}
            required
            usedElsewhere={usedByOthers("name_col")}
          />
        </div>
      </div>

      <div className="rounded-lg border border-stone-200 bg-white p-5">
        <h3 className="text-sm font-semibold text-stone-900">Optional</h3>
        <p className="mt-0.5 text-xs text-stone-500">
          Leave any of these unmapped if your file doesn't have them.
        </p>

        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
          <ColumnSelect
            label="Email"
            value={identity.email_col}
            columns={columns}
            onChange={(value) => set("email_col", value)}
            usedElsewhere={usedByOthers("email_col")}
          />
          <ColumnSelect
            label="Program"
            value={identity.program_col}
            columns={columns}
            onChange={(value) => set("program_col", value)}
            usedElsewhere={usedByOthers("program_col")}
          />
          <ColumnSelect
            label="Gender"
            hint="Used by the ML model as a feature"
            value={identity.gender_col}
            columns={columns}
            onChange={(value) => set("gender_col", value)}
            usedElsewhere={usedByOthers("gender_col")}
          />
          <ColumnSelect
            label="Age"
            hint="Used by the ML model as a feature"
            value={identity.age_col}
            columns={columns}
            onChange={(value) => set("age_col", value)}
            usedElsewhere={usedByOthers("age_col")}
          />
        </div>

        {/* Only shown when the file plausibly HAS these columns and they
            are unmapped — nagging about data that does not exist would
            be noise. */}
        {(!identity.gender_col || !identity.age_col) && (
          <div className="mt-4 flex gap-2.5 rounded-md bg-stone-50 p-3">
            <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-stone-400" aria-hidden="true" />
            <p className="text-[11px] leading-relaxed text-stone-500">
              Gender and age are inputs to the risk model. If your file has them, mapping
              them gives these students a more complete score than leaving them out.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
