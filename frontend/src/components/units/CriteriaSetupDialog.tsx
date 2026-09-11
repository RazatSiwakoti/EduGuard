import { useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { useUnitShape } from "../../hooks/useUnitShape";
import CriteriaShapeForm from "./CriteriaShapeForm";
import UnlockCriteriaDialog from "./UnlockCriteriaDialog";

interface CriteriaSetupDialogProps {
  unitId: number | null;
  unitCode: string;
  unitName: string;
  onOpenChange: (open: boolean) => void;
}

/**
 * "Set up criteria" — the coordinator's whole configuration screen for
 * one unit.
 *
 * This component owns the read, the lock banner and the unlock path.
 * `CriteriaShapeForm` owns the editing. The split is not cosmetic: the
 * form is remounted with a fresh `key` whenever the server's copy of
 * the shape genuinely changes, which is how its state re-derives from
 * the loaded data without an effect that could overwrite what someone
 * is typing.
 *
 * ONE REQUEST, NOT TWO. The shape and the lock state arrive together
 * from `GET /admin/units/{id}/criteria`, because a disabled input and
 * an editable one are not the same screen — fetching them separately
 * guarantees a first paint that is wrong and then corrects itself in
 * front of the user.
 */
export default function CriteriaSetupDialog({
  unitId,
  unitCode,
  unitName,
  onOpenChange,
}: CriteriaSetupDialogProps) {
  const [unlockOpen, setUnlockOpen] = useState(false);

  const open = unitId !== null;
  // staleTime 0: always re-read the lock state when the dialog opens.
  // The cached copy from the row badge still paints immediately — this
  // only makes sure a unit that locked in the last minute is not shown
  // as editable. See `useUnitShape`.
  const { data: shape, isLoading, isError, refetch } = useUnitShape(unitId, open, 0);

  /**
   * Remount the form only when the SERVER's shape changed.
   *
   * `criteria_updated_at` moves on a real shape save and deliberately
   * does not move on a rename, so a labels-only save leaves the form
   * standing with state that already matches what was stored. A plain
   * `dataUpdatedAt` key would remount on every background refetch and
   * throw away half-typed input.
   */
  const formKey = shape
    ? [
        shape.unit_id,
        shape.lock.criteria_updated_at ?? "never",
        shape.tutorials_enabled,
        shape.assessments.map((row) => row.id).join(","),
      ].join("|")
    : "empty";

  return (
    <>
      <Dialog.Root open={open} onOpenChange={(next) => !next && onOpenChange(false)}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 z-30 bg-black/30" />
          <Dialog.Content className="fixed left-1/2 top-1/2 z-30 max-h-[90vh] w-full max-w-2xl -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-md bg-white p-6 shadow-lg">
            <Dialog.Title className="text-base font-semibold text-stone-900">
              Set up criteria — {unitCode}
            </Dialog.Title>
            <Dialog.Description className="mt-1 text-sm text-stone-500">
              {unitName}. Decide what this unit is marked on. Attendance and
              Moodle activity are added automatically and are not part of the
              mark total.
            </Dialog.Description>

            {isLoading && (
              <p className="mt-6 text-sm text-stone-500">Loading criteria…</p>
            )}

            {isError && (
              <div className="mt-6 rounded border border-red-200 bg-red-50 p-4">
                <p className="text-sm text-red-700">
                  Could not load this unit's criteria.
                </p>
                <button
                  type="button"
                  onClick={() => refetch()}
                  className="mt-2 rounded border border-red-300 px-2.5 py-1 text-xs font-medium text-red-700 hover:bg-red-100"
                >
                  Try again
                </button>
              </div>
            )}

            {shape && (
              <>
                {/* Locked: say why, in the server's words, and offer the
                    one action that changes it. The reasons are finished
                    sentences from the backend — rebuilding them here
                    would be a second description of the same rule. */}
                {shape.lock.locked && (
                  <div
                    className="mt-4 rounded border border-amber-300 bg-amber-50 p-3"
                    data-testid="lock-banner"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-sm font-semibold text-amber-900">
                          These criteria are locked
                        </p>
                        <ul className="mt-1 list-disc space-y-0.5 pl-5 text-sm text-amber-900">
                          {shape.lock.reasons.map((reason) => (
                            <li key={reason}>{reason}</li>
                          ))}
                        </ul>
                        <p className="mt-1.5 text-xs text-amber-800">
                          Every risk score in this unit was calculated from the
                          shape below. Renaming an item is still allowed.
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={() => setUnlockOpen(true)}
                        className="shrink-0 rounded border border-amber-400 bg-white px-2.5 py-1.5 text-xs font-medium text-amber-900 hover:bg-amber-100"
                        data-testid="open-unlock"
                      >
                        Unlock…
                      </button>
                    </div>
                  </div>
                )}

                {/* Unlocked: the window is open and it is one-shot. Saying
                    so matters — the next save closes it, and a rename
                    does not. */}
                {shape.lock.unlock_active && (
                  <div
                    className="mt-4 rounded border border-emerald-300 bg-emerald-50 p-3 text-sm text-emerald-900"
                    data-testid="unlock-banner"
                  >
                    <span className="font-semibold">Unlocked for one edit.</span>{" "}
                    The next saved change re-locks this unit and marks its
                    existing risk results as computed against an older shape.
                  </div>
                )}

                <div className="mt-5">
                  <CriteriaShapeForm
                    key={formKey}
                    shape={shape}
                    onLocked={() => setUnlockOpen(true)}
                  />
                </div>
              </>
            )}
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>

      {unitId !== null && (
        <UnlockCriteriaDialog
          unitId={unitId}
          unitCode={unitCode}
          open={unlockOpen}
          onOpenChange={setUnlockOpen}
          onUnlocked={() => refetch()}
        />
      )}
    </>
  );
}