import { useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import type { DashboardCriterionScore, DashboardUnitCriterion, DashboardStudent } from "../../types/dashboard";
import { useUpdateStudent } from "../../hooks/useStudentDetail";

interface Props {
  student: DashboardStudent;
  unitCode: string;
  criteria: DashboardUnitCriterion[];
  onOpenChange: (open: boolean) => void;
}

export default function EditStudentDialog({ student, unitCode, criteria, onOpenChange }: Props) {
  const update = useUpdateStudent();
  const [name, setName] = useState(student.name);
  const [program, setProgram] = useState(student.program ?? "");
  const [gender, setGender] = useState(student.gender ?? "");
  const [age, setAge] = useState(student.age === null ? "" : String(student.age));
  const [scores, setScores] = useState<Record<number, string>>(() =>
    Object.fromEntries(student.criteria.map((item) => [item.criteria_id, String(item.score ?? "")])),
  );

  function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const numericScores: Record<number, number | null> = {};
    for (const criterion of criteria.filter((item) => item.category === "assessment")) {
      const raw = scores[criterion.id] ?? "";
      numericScores[criterion.id] = raw === "" ? null : Number(raw);
    }
    update.mutate(
      {
        studentId: student.student_id,
        unitId: student.unit_id,
        payload: {
          name: name.trim(),
          program: program.trim() || null,
          gender: gender.trim() || null,
          age: age.trim() ? Number(age) : null,
          scores: numericScores,
        },
      },
      { onSuccess: () => onOpenChange(false) },
    );
  }

  const scoreFor = (criterion: DashboardUnitCriterion): DashboardCriterionScore | undefined =>
    student.criteria.find((item) => item.criteria_id === criterion.id);

  return (
    <Dialog.Root open onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-black/30" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 max-h-[90vh] w-full max-w-lg -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-md bg-white p-6 shadow-lg">
          <Dialog.Title className="text-base font-semibold text-stone-900">
            Edit {student.name} · {unitCode}
          </Dialog.Title>
          <form onSubmit={submit} className="mt-4 space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <label className="text-sm font-medium text-stone-700">
                Name
                <input value={name} onChange={(event) => setName(event.target.value)} className="mt-1 w-full rounded border border-stone-300 px-3 py-2 font-normal" required />
              </label>
              <label className="text-sm font-medium text-stone-700">
                Email
                <input value={student.email ?? ""} readOnly className="mt-1 w-full rounded border border-stone-300 bg-stone-100 px-3 py-2 font-normal text-stone-500" />
              </label>
              <label className="text-sm font-medium text-stone-700">
                Program
                <input value={program} onChange={(event) => setProgram(event.target.value)} className="mt-1 w-full rounded border border-stone-300 px-3 py-2 font-normal" />
              </label>
              <label className="text-sm font-medium text-stone-700">
                Gender
                <input value={gender} onChange={(event) => setGender(event.target.value)} className="mt-1 w-full rounded border border-stone-300 px-3 py-2 font-normal" />
              </label>
              <label className="text-sm font-medium text-stone-700">
                Age
                <input type="number" min="1" value={age} onChange={(event) => setAge(event.target.value)} className="mt-1 w-full rounded border border-stone-300 px-3 py-2 font-normal" />
              </label>
            </div>
            <fieldset>
              <legend className="mb-2 text-sm font-semibold text-stone-800">Assessment scores</legend>
              <div className="grid grid-cols-2 gap-3">
                {criteria.filter((item) => item.category === "assessment").map((criterion) => (
                  <label key={criterion.id} className="text-sm text-stone-700">
                    {criterion.name} <span className="text-xs text-stone-400">/ {criterion.max_score}</span>
                    <input
                      type="number"
                      min="0"
                      max={criterion.max_score}
                      value={scores[criterion.id] ?? String(scoreFor(criterion)?.score ?? "")}
                      onChange={(event) => setScores({ ...scores, [criterion.id]: event.target.value })}
                      className="mt-1 w-full rounded border border-stone-300 px-3 py-2"
                    />
                  </label>
                ))}
              </div>
            </fieldset>
            {update.isError && <p className="text-sm text-red-600">{update.error instanceof Error ? update.error.message : "Could not save changes."}</p>}
            <footer className="flex justify-end gap-2">
              <Dialog.Close asChild><button type="button" className="rounded border border-stone-300 px-3 py-2 text-sm">Cancel</button></Dialog.Close>
              <button type="submit" disabled={update.isPending} className="rounded bg-stone-900 px-3 py-2 text-sm font-medium text-white disabled:opacity-50">Save changes</button>
            </footer>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
