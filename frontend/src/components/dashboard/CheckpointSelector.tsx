interface CheckpointSelectorProps {
  value: number;
  available?: number[];
  onChange: (week: number) => void;
}

export default function CheckpointSelector({
  value,
  available = [],
  onChange,
}: CheckpointSelectorProps) {
  return (
    <div className="inline-flex rounded-lg border border-stone-200 bg-white p-1" aria-label="Checkpoint">
      {[4, 8, 12].map((week) => {
        const enabled = available.includes(week);
        return (
          <button
            key={week}
            type="button"
            disabled={!enabled}
            title={enabled ? `Week ${week}` : "Analysis has not been run for this checkpoint"}
            onClick={() => onChange(week)}
            className={`rounded-md px-3 py-1.5 text-xs font-medium ${
              value === week ? "bg-stone-900 text-white" : "text-stone-600"
            } disabled:cursor-not-allowed disabled:opacity-40`}
          >
            Week {week}
          </button>
        );
      })}
    </div>
  );
}
