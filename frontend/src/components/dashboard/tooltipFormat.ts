/**
 * Small coercion helpers for Recharts tooltip and label callbacks.
 *
 * WHY THESE EXIST
 * ---------------
 * Recharts types its formatter callbacks against the widest possible
 * shapes — `ValueType | undefined`, `NameType | undefined`, `ReactNode`
 * — because a chart can in principle be fed strings, numbers, arrays or
 * nothing at all. TypeScript enforces that contract contravariantly:
 * a callback declared as `(value: number) => …` is NOT assignable,
 * because Recharts is entitled to hand it `undefined`.
 *
 * The wrong fix is `as never` or `any` on every chart, which silences
 * the checker and hides real mistakes. The right fix is to accept the
 * wide type honestly and narrow it in ONE place — here — so each chart
 * stays readable and every coercion is written down exactly once.
 *
 * Our own data is already strongly typed on the way in, so these are
 * defensive conversions at the library boundary, not guesswork about
 * what the values might be.
 */

/** Coerces a Recharts value into a number, defaulting to 0. */
export function toNumber(value: unknown): number {
  if (typeof value === "number") return value;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

/** Coerces a Recharts label/name into a string, defaulting to empty. */
export function toText(value: unknown): string {
  if (typeof value === "string") return value;
  if (value === null || value === undefined) return "";
  return String(value);
}

/** Shared tooltip chrome, so all five charts present identically. */
export function tooltipContentStyle(borderColor: string, textColor: string) {
  return {
    borderRadius: 6,
    border: `1px solid ${borderColor}`,
    fontSize: 12,
    color: textColor,
  };
}

/** `n student` / `n students` — used by three of the five charts. */
export function pluralStudents(count: number): string {
  return `${count} student${count === 1 ? "" : "s"}`;
}