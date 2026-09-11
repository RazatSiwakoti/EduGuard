import type { Preferences } from "../../types/auth";

export default function FontSizeControl({ value, onChange }: { value: Preferences["font_size"]; onChange: (value: Preferences["font_size"]) => void }) {
  return (
    <div>
      <p className="mb-2 text-sm text-stone-700">The quick brown fox jumps over the lazy dog.</p>
      <div className="grid grid-cols-4 gap-1 rounded-md border border-stone-200 p-1">
        {(["small", "default", "large", "larger"] as const).map((size) => (
          <button key={size} type="button" onClick={() => onChange(size)} className={`rounded px-2 py-1.5 text-xs capitalize ${value === size ? "bg-stone-900 text-white" : "text-stone-600 hover:bg-stone-50"}`}>{size}</button>
        ))}
      </div>
    </div>
  );
}
