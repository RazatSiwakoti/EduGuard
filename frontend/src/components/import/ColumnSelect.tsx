interface ColumnSelectProps {
  label: string;
  value: string;
  columns: string[];
  onChange: (value: string) => void;
  required?: boolean;
  /** Short hint under the label — units, expected format, consequences. */
  hint?: string;
  /** Columns already used elsewhere, shown but flagged. */
  usedElsewhere?: Set<string>;
}

/**
 * One "map this to a column" dropdown.
 *
 * A native <select> rather than a styled listbox, deliberately. There
 * can be forty columns in a spreadsheet, and a native select gives
 * type-ahead, keyboard navigation and mobile pickers for free — all
 * things a custom component would have to reimplement, badly.
 *
 * Columns already used by another field stay SELECTABLE but are marked.
 * Reusing one column for two criteria is unusual but not invalid — a
 * unit might legitimately score the same mark twice — so this warns
 * rather than blocks.
 */
export default function ColumnSelect({
  label,
  value,
  columns,
  onChange,
  required = false,
  hint,
  usedElsewhere,
}: ColumnSelectProps) {
  const isMissing = required && !value;

  return (
    <label className="block">
      <span className="block text-xs font-medium text-stone-700">
        {label}
        {required && <span className="ml-0.5 text-red-500">*</span>}
      </span>

      {hint && <span className="mt-0.5 block text-[11px] text-stone-400">{hint}</span>}

      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className={`mt-1.5 w-full rounded-md border bg-white px-2.5 py-1.5 text-sm text-stone-900 outline-none transition focus:border-stone-400 ${
          isMissing ? "border-red-300" : "border-stone-200"
        }`}
      >
        <option value="">{required ? "— select a column —" : "— not in my file —"}</option>

        {columns.map((column) => (
          <option key={column} value={column}>
            {column}
            {usedElsewhere?.has(column) && column !== value ? "  (already used)" : ""}
          </option>
        ))}
      </select>
    </label>
  );
}
