import { useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";

import { useUpdateUnit } from "../../hooks/useUnits";
import type { ClassType, Unit } from "../../types/unit";
import { CLASS_TYPES, TEACHING_PERIODS, UNIT_LEVELS } from "../../types/unit";

function isNumbered(type: ClassType | ""): boolean {
  return CLASS_TYPES.some((option) => option.value === type && option.numbered);
}

export default function EditUnitDialog({
  unit,
  onOpenChange,
}: {
  unit: Unit;
  onOpenChange: (open: boolean) => void;
}) {
  const updateUnit = useUpdateUnit();
  const [unitName, setUnitName] = useState(unit.unit_name);
  const [startDate, setStartDate] = useState(unit.start_date ?? "");
  const [year, setYear] = useState(unit.year === null ? "" : String(unit.year));
  const [teachingPeriod, setTeachingPeriod] = useState(unit.teaching_period ?? "");
  const [level, setLevel] = useState(unit.level ?? "");
  const [classType, setClassType] = useState<ClassType | "">(unit.class_type ?? "");
  const [classNumber, setClassNumber] = useState(
    unit.class_number === null ? "" : String(unit.class_number),
  );

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const type = classType === "" ? null : classType;
    const number =
      type !== null && isNumbered(type) && classNumber !== "" ? Number(classNumber) : null;

    updateUnit.mutate(
      {
        id: unit.id,
        data: {
          unit_name: unitName,
          start_date: startDate,
          year: year === "" ? null : Number(year),
          teaching_period: teachingPeriod || null,
          level: level || null,
          class_type: type,
          class_number: number,
        },
      },
      { onSuccess: () => onOpenChange(false) },
    );
  }

  return (
    <Dialog.Root open={true} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/30" />
        <Dialog.Content className="fixed left-1/2 top-1/2 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-md bg-white p-6 shadow-lg">
          <Dialog.Title className="text-base font-semibold text-stone-900">
            Edit Unit
          </Dialog.Title>

          <form onSubmit={handleSubmit} className="mt-4 space-y-3">
            <div>
              <label className="mb-1 block text-sm font-medium text-stone-700">
                Unit code
              </label>
              <input
                value={unit.unit_code}
                disabled
                className="w-full rounded border border-stone-300 bg-stone-100 px-3 py-2 text-sm uppercase text-stone-500"
              />
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-stone-700">
                Unit name
              </label>
              <input
                value={unitName}
                onChange={(event) => setUnitName(event.target.value)}
                className="w-full rounded border border-stone-300 px-3 py-2 text-sm outline-none focus:border-stone-500"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="mb-1 block text-sm font-medium text-stone-700">
                  Year
                </label>
                <input
                  type="number"
                  value={year}
                  onChange={(event) => setYear(event.target.value)}
                  className="w-full rounded border border-stone-300 px-3 py-2 text-sm outline-none focus:border-stone-500"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-stone-700">
                  Teaching period
                </label>
                <select
                  value={teachingPeriod}
                  onChange={(event) => setTeachingPeriod(event.target.value)}
                  className="w-full rounded border border-stone-300 px-3 py-2 text-sm outline-none focus:border-stone-500"
                >
                  <option value="">Select period</option>
                  {TEACHING_PERIODS.map((period) => (
                    <option key={period} value={period}>
                      {period}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="mb-1 block text-sm font-medium text-stone-700">
                  Level
                </label>
                <select
                  value={level}
                  onChange={(event) => setLevel(event.target.value)}
                  className="w-full rounded border border-stone-300 px-3 py-2 text-sm outline-none focus:border-stone-500"
                >
                  <option value="">Select level</option>
                  {UNIT_LEVELS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-stone-700">
                  Start date
                </label>
                <input
                  type="date"
                  value={startDate}
                  onChange={(event) => setStartDate(event.target.value)}
                  className="w-full rounded border border-stone-300 px-3 py-2 text-sm outline-none focus:border-stone-500"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="mb-1 block text-sm font-medium text-stone-700">
                  Class type <span className="font-normal text-stone-400">(optional)</span>
                </label>
                <select
                  value={classType}
                  onChange={(event) => {
                    const next = event.target.value as ClassType | "";
                    setClassType(next);
                    if (!isNumbered(next)) setClassNumber("");
                  }}
                  className="w-full rounded border border-stone-300 px-3 py-2 text-sm outline-none focus:border-stone-500"
                >
                  <option value="">No class split</option>
                  {CLASS_TYPES.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>

              {isNumbered(classType) && (
                <div>
                  <label className="mb-1 block text-sm font-medium text-stone-700">
                    Class number
                  </label>
                  <input
                    type="number"
                    min={1}
                    max={99}
                    value={classNumber}
                    onChange={(event) => setClassNumber(event.target.value)}
                    required
                    className="w-full rounded border border-stone-300 px-3 py-2 text-sm outline-none focus:border-stone-500"
                  />
                </div>
              )}
            </div>

            {classType && (
              <p className="-mt-1 font-mono text-xs text-stone-500">
                This unit will be{" "}
                <span className="font-bold text-brand">
                  {unit.unit_code || "CODE"}
                  {classType}
                  {isNumbered(classType) ? classNumber : ""}
                </span>
              </p>
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
                disabled={updateUnit.isPending}
                className="rounded bg-stone-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-stone-800 disabled:opacity-50"
              >
                {updateUnit.isPending ? "Saving…" : "Save changes"}
              </button>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
