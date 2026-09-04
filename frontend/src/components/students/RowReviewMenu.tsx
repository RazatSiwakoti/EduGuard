import { useState } from "react";
import * as AlertDialog from "@radix-ui/react-alert-dialog";
import * as Dialog from "@radix-ui/react-dialog";
import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { MoreVertical } from "lucide-react";
import type { DashboardStudent, DashboardUnitCriterion, RiskTier } from "../../types/dashboard";
import { BUCKET_LABELS } from "../../utils/dashboardAggregations";
import { BUCKET_STYLES } from "../dashboard/chartTheme";
import { useDeleteStudent, useSubmitRowReview } from "../../hooks/useStudentDetail";
import EditStudentDialog from "./EditStudentDialog";

interface Props {
  student: DashboardStudent;
  unitCode: string;
  criteria?: DashboardUnitCriterion[];
}

const tiers: RiskTier[] = ["safe", "low_risk", "high_risk"];

export default function RowReviewMenu({ student, unitCode, criteria = [] }: Props) {
  const [reviewTier, setReviewTier] = useState<RiskTier | null>(null);
  const [comment, setComment] = useState("");
  const [editOpen, setEditOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [confirmation, setConfirmation] = useState("");
  const review = useSubmitRowReview(student.student_id, student.unit_id);
  const deletion = useDeleteStudent();

  function saveReview(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!reviewTier) return;
    review.mutate({ decision: reviewTier, comment: comment.trim() || undefined }, {
      onSuccess: () => { setReviewTier(null); setComment(""); },
    });
  }

  function deleteStudent() {
    deletion.mutate(
      { studentId: student.student_id, unitId: student.unit_id },
      { onSuccess: () => setDeleteOpen(false) },
    );
  }

  return (
    <>
      <DropdownMenu.Root>
        <DropdownMenu.Trigger asChild>
          <button
            type="button"
            aria-label={`Review ${student.name}`}
            onClick={(event) => event.stopPropagation()}
            className="rounded p-1.5 text-stone-500 hover:bg-stone-100 hover:text-stone-900"
          >
            <MoreVertical className="h-4 w-4" aria-hidden="true" />
          </button>
        </DropdownMenu.Trigger>
        <DropdownMenu.Portal>
          <DropdownMenu.Content align="end" className="z-50 min-w-44 rounded-md border border-stone-200 bg-white p-1 shadow-lg">
            {tiers.map((tier) => (
              <DropdownMenu.Item key={tier} onSelect={() => setReviewTier(tier)} className="flex cursor-pointer items-center gap-2 rounded px-3 py-2 text-sm outline-none hover:bg-stone-100">
                <span className={`h-2 w-2 rounded-full ${BUCKET_STYLES[tier].dot}`} />
                Mark as {BUCKET_LABELS[tier]}
              </DropdownMenu.Item>
            ))}
            <DropdownMenu.Separator className="my-1 h-px bg-stone-200" />
            <DropdownMenu.Item onSelect={() => setEditOpen(true)} className="cursor-pointer rounded px-3 py-2 text-sm outline-none hover:bg-stone-100">Edit student data</DropdownMenu.Item>
            <DropdownMenu.Item onSelect={() => setDeleteOpen(true)} className="cursor-pointer rounded px-3 py-2 text-sm text-red-600 outline-none hover:bg-red-50">Delete from this unit</DropdownMenu.Item>
          </DropdownMenu.Content>
        </DropdownMenu.Portal>
      </DropdownMenu.Root>

      {reviewTier && (
        <Dialog.Root open onOpenChange={(open) => !open && setReviewTier(null)}>
          <Dialog.Portal>
            <Dialog.Overlay className="fixed inset-0 z-40 bg-black/30" />
            <Dialog.Content className="fixed left-1/2 top-1/2 z-50 w-full max-w-sm -translate-x-1/2 -translate-y-1/2 rounded-md bg-white p-6 shadow-lg">
              <Dialog.Title className="text-base font-semibold">Review {student.name}</Dialog.Title>
              <p className="mt-1 text-sm text-stone-500">{unitCode}</p>
              <span className={`mt-3 inline-flex rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset ${BUCKET_STYLES[reviewTier].pill}`}>
                {BUCKET_LABELS[reviewTier]}
              </span>
              <form onSubmit={saveReview} className="mt-4 space-y-3">
                <label className="block text-sm font-medium text-stone-700">
                  Comment (optional)
                  <textarea value={comment} onChange={(event) => setComment(event.target.value)} rows={3} className="mt-1 w-full rounded border border-stone-300 px-3 py-2 font-normal" />
                </label>
                {review.isError && <p className="text-sm text-red-600">Could not save this decision.</p>}
                <footer className="flex justify-end gap-2">
                  <button type="button" onClick={() => setReviewTier(null)} className="rounded border border-stone-300 px-3 py-2 text-sm">Cancel</button>
                  <button type="submit" disabled={review.isPending} className="rounded bg-stone-900 px-3 py-2 text-sm font-medium text-white disabled:opacity-50">Save decision</button>
                </footer>
              </form>
            </Dialog.Content>
          </Dialog.Portal>
        </Dialog.Root>
      )}

      {editOpen && <EditStudentDialog student={student} unitCode={unitCode} criteria={criteria} onOpenChange={setEditOpen} />}

      <AlertDialog.Root open={deleteOpen} onOpenChange={setDeleteOpen}>
        <AlertDialog.Portal>
          <AlertDialog.Overlay className="fixed inset-0 z-40 bg-black/30" />
          <AlertDialog.Content className="fixed left-1/2 top-1/2 z-50 w-full max-w-sm -translate-x-1/2 -translate-y-1/2 rounded-md bg-white p-6 shadow-lg">
            <AlertDialog.Title className="text-base font-semibold text-red-700">Delete from {unitCode}?</AlertDialog.Title>
            <AlertDialog.Description className="mt-2 text-sm text-stone-600">This permanently deletes this unit's data. Type {student.student_number} to confirm.</AlertDialog.Description>
            <input value={confirmation} onChange={(event) => setConfirmation(event.target.value)} className="mt-4 w-full rounded border border-stone-300 px-3 py-2" />
            {deletion.isError && <p className="mt-2 text-sm text-red-600">Could not delete this student.</p>}
            <footer className="mt-4 flex justify-end gap-2">
              <AlertDialog.Cancel asChild><button className="rounded border border-stone-300 px-3 py-2 text-sm">Cancel</button></AlertDialog.Cancel>
              <AlertDialog.Action asChild>
                <button disabled={confirmation !== student.student_number || deletion.isPending} onClick={deleteStudent} className="rounded bg-red-600 px-3 py-2 text-sm font-medium text-white disabled:opacity-50">Delete permanently</button>
              </AlertDialog.Action>
            </footer>
          </AlertDialog.Content>
        </AlertDialog.Portal>
      </AlertDialog.Root>
    </>
  );
}