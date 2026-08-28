import { useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import {
  useUnlockPreview,
  useUnlockUnitShape,
  detailOf,
  statusOf,
} from "../../hooks/useUnitShape";

interface UnlockCriteriaDialogProps {
  unitId: number;
  unitCode: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Fired after a successful unlock so the form can re-enable itself. */
  onUnlocked: () => void;
}

/**
 * The admin unlock path: state the cost, THEN ask for the confirmation.
 *
 * ORDER IS THE WHOLE DESIGN. The consequence sentence is fetched and
 * shown before the input is reachable, because a typed confirmation
 * that appears before the price is asking someone to agree to a number
 * they have not been told.
 *
 * The sentence itself comes from the server (`consequence`) and is
 * printed verbatim. It is written there because only the server knows
 * how many verdicts are still valid, and because a second wording in
 * the client is a second description of what an unlock does.
 *
 * WHAT THIS DIALOG DOES NOT DO
 * ----------------------------
 * It does not mark anything stale. Unlocking opens a one-shot window
 * and changes no numbers; the staleness lands on the SAVE that follows.
 * That is why the copy says "saving a change will…" and not "this will…".
 */
export default function UnlockCriteriaDialog({
  unitId,
  unitCode,
  open,
  onOpenChange,
  onUnlocked,
}: UnlockCriteriaDialogProps) {
  const [typed, setTyped] = useState("");

  const { data: preview, isLoading, isError } = useUnlockPreview(unitId, open);
  const unlock = useUnlockUnitShape(unitId);

  // Case-insensitive and whitespace-trimmed, matching the server. The
  // confirmation exists to prove the admin knows WHICH unit they are
  // opening; rejecting "ict729" for "ICT729" tests a shift key.
  const matches = typed.trim().toLowerCase() === unitCode.trim().toLowerCase();

  // A 400 from the unlock endpoint means the typed code did not match,
  // so it belongs under the input rather than in a toast that vanishes.
  const confirmationError =
    unlock.isError && statusOf(unlock.error) === 400
      ? detailOf(unlock.error, "That is not the unit code.")
      : null;

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!matches) return;
    unlock.mutate(typed, {
      onSuccess: () => {
        setTyped("");
        onOpenChange(false);
        onUnlocked();
      },
    });
  }

  return (
    <Dialog.Root
      open={open}
      onOpenChange={(next) => {
        if (!next) setTyped("");
        onOpenChange(next);
      }}
    >
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-black/40" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-md bg-white p-6 shadow-lg">
          <Dialog.Title className="text-base font-semibold text-stone-900">
            Unlock {unitCode} for one edit
          </Dialog.Title>

          <Dialog.Description className="mt-2 text-sm text-stone-600">
            This unit has been used. Unlocking allows{" "}
            <strong className="font-semibold text-stone-900">
              one saved change
            </strong>{" "}
            to its criteria, then locks again.
          </Dialog.Description>

          {isLoading && (
            <p className="mt-4 text-sm text-stone-500">Checking what this affects…</p>
          )}

          {isError && (
            <p className="mt-4 rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700">
              Could not work out what unlocking would affect. Close this and try
              again rather than unlocking blind.
            </p>
          )}

          {preview && (
            <div className="mt-4 space-y-3">
              {/* The cost, in the server's own words. */}
              <p className="rounded border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
                {preview.consequence}
              </p>

              <dl className="grid grid-cols-3 gap-2 text-center">
                <div className="rounded border border-stone-200 p-2">
                  <dt className="text-xs text-stone-500">Results affected</dt>
                  <dd className="text-lg font-semibold text-stone-900">
                    {preview.verdicts_currently_valid}
                  </dd>
                </div>
                <div className="rounded border border-stone-200 p-2">
                  <dt className="text-xs text-stone-500">Students</dt>
                  <dd className="text-lg font-semibold text-stone-900">
                    {preview.students_affected}
                  </dd>
                </div>
                <div className="rounded border border-stone-200 p-2">
                  {/* Counted separately: re-invalidating something already
                      invalid costs nothing, and folding it into the number
                      above would overstate the damage. */}
                  <dt className="text-xs text-stone-500">Already stale</dt>
                  <dd className="text-lg font-semibold text-stone-500">
                    {preview.verdicts_already_stale}
                  </dd>
                </div>
              </dl>

              <form onSubmit={handleSubmit} className="space-y-2">
                <label
                  htmlFor="unlock-confirm"
                  className="block text-sm font-medium text-stone-700"
                >
                  Type <span className="font-mono">{unitCode}</span> to confirm
                </label>
                <input
                  id="unlock-confirm"
                  value={typed}
                  onChange={(event) => setTyped(event.target.value)}
                  autoComplete="off"
                  placeholder={unitCode}
                  className="w-full rounded border border-stone-300 px-3 py-2 font-mono text-sm outline-none focus:border-stone-500"
                />

                {confirmationError && (
                  <p className="text-sm text-red-600">{confirmationError}</p>
                )}

                <div className="flex justify-end gap-2 pt-2">
                  <Dialog.Close asChild>
                    <button
                      type="button"
                      className="rounded border border-stone-300 px-3 py-1.5 text-sm font-medium text-stone-700 hover:bg-stone-100"
                    >
                      Cancel
                    </button>
                  </Dialog.Close>
                  <button
                    type="submit"
                    disabled={!matches || unlock.isPending}
                    className="rounded bg-amber-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-amber-700 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {unlock.isPending ? "Unlocking…" : "Unlock for one edit"}
                  </button>
                </div>
              </form>
            </div>
          )}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}