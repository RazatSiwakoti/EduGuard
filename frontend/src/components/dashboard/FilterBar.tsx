import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { Check, ChevronDown, Filter, X } from "lucide-react";
import type { DashboardFilters, DashboardUnit, RiskBucket } from "../../types/dashboard";
import { BUCKET_LABELS, BUCKET_ORDER } from "../../utils/dashboardAggregations";
import { BUCKET_ICONS } from "./BucketBadge";
import { BUCKET_STYLES } from "./chartTheme";

interface FilterBarProps {
  units: DashboardUnit[];
  filters: DashboardFilters;
  onChange: (next: DashboardFilters) => void;
  /** Buckets actually present in the data — the rest are not offered. */
  availableBuckets: RiskBucket[];
  visibleCount: number;
  totalCount: number;
}

/**
 * The dashboard's single control row, sitting above every chart.
 *
 * Both filters live here AND are settable by clicking marks in the
 * charts themselves. Keeping one shared filter object as the source of
 * truth is what makes that work: a click on a donut segment and a click
 * on this dropdown are the same state change, so the two can never
 * disagree about what is currently selected.
 *
 * Risk chips TOGGLE rather than accumulate. Clicking the already-active
 * chip clears it, which gives an obvious way back to "show everything"
 * without hunting for the reset button.
 */
export default function FilterBar({
  units,
  filters,
  onChange,
  availableBuckets,
  visibleCount,
  totalCount,
}: FilterBarProps) {
  const selectedUnit = units.find((u) => u.id === filters.unitId) ?? null;
  const hasActiveFilter = filters.unitId !== null || filters.bucket !== null;

  // Chips are ordered by severity, and only offered for buckets that
  // actually occur — a chip that can only ever return zero students is
  // noise, not a control.
  const bucketChips = BUCKET_ORDER.filter((bucket) => availableBuckets.includes(bucket));

  return (
    <div className="mb-5 flex flex-wrap items-center gap-3 rounded-lg border border-stone-200 bg-white px-4 py-3">
      <div className="flex items-center gap-2 text-stone-400">
        <Filter className="h-4 w-4" aria-hidden="true" />
        <span className="text-xs font-medium uppercase tracking-wide">Filters</span>
      </div>

      {/* ---------- Unit filter ---------- */}
      <DropdownMenu.Root>
        <DropdownMenu.Trigger asChild>
          <button
            type="button"
            className="flex items-center gap-2 rounded-md border border-stone-200 px-3 py-1.5 text-sm text-stone-700 transition hover:bg-stone-50"
          >
            <span className="font-medium">
              {selectedUnit ? selectedUnit.unit_code : "All units"}
            </span>
            <ChevronDown className="h-4 w-4 text-stone-400" aria-hidden="true" />
          </button>
        </DropdownMenu.Trigger>

        <DropdownMenu.Portal>
          <DropdownMenu.Content
            align="start"
            sideOffset={6}
            className="z-50 max-h-80 w-72 overflow-y-auto rounded-md border border-stone-200 bg-white p-1 shadow-lg"
          >
            <DropdownMenu.Item
              onSelect={() => onChange({ ...filters, unitId: null })}
              className="flex cursor-pointer items-center justify-between rounded px-3 py-2 text-sm text-stone-700 outline-none hover:bg-stone-100"
            >
              <span className="font-medium">All units</span>
              {filters.unitId === null && <Check className="h-4 w-4 text-stone-900" />}
            </DropdownMenu.Item>

            <DropdownMenu.Separator className="my-1 h-px bg-stone-200" />

            {units.map((unit) => (
              <DropdownMenu.Item
                key={unit.id}
                onSelect={() => onChange({ ...filters, unitId: unit.id })}
                className="flex cursor-pointer items-start justify-between gap-3 rounded px-3 py-2 text-sm text-stone-700 outline-none hover:bg-stone-100"
              >
                <span className="min-w-0">
                  <span className="block font-medium">{unit.unit_code}</span>
                  <span className="block truncate text-xs text-stone-500">
                    {unit.unit_name}
                    {unit.teaching_period ? ` · ${unit.teaching_period}` : ""}
                    {unit.year ? ` ${unit.year}` : ""}
                  </span>
                </span>
                {filters.unitId === unit.id && (
                  <Check className="mt-0.5 h-4 w-4 shrink-0 text-stone-900" />
                )}
              </DropdownMenu.Item>
            ))}
          </DropdownMenu.Content>
        </DropdownMenu.Portal>
      </DropdownMenu.Root>

      {/* ---------- Risk level chips ---------- */}
      <div className="flex flex-wrap items-center gap-1.5">
        {bucketChips.map((bucket) => {
          const Icon = BUCKET_ICONS[bucket];
          const isActive = filters.bucket === bucket;

          return (
            <button
              key={bucket}
              type="button"
              // Clicking the active chip clears it — see component docstring.
              onClick={() =>
                onChange({ ...filters, bucket: isActive ? null : bucket })
              }
              aria-pressed={isActive}
              title={BUCKET_STYLES[bucket].hint}
              className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset transition ${
                isActive
                  ? BUCKET_STYLES[bucket].pill
                  : "text-stone-500 ring-stone-200 hover:bg-stone-50"
              }`}
            >
              <Icon
                className="h-3.5 w-3.5"
                aria-hidden="true"
                // The icon keeps its tier colour even when the chip is
                // inactive, so the legend mapping stays learnable.
                style={isActive ? undefined : { color: BUCKET_STYLES[bucket].fill }}
              />
              {BUCKET_LABELS[bucket]}
            </button>
          );
        })}
      </div>

      {/* ---------- Result count + reset ---------- */}
      <div className="ml-auto flex items-center gap-3">
        <p className="text-xs text-stone-500">
          <span className="font-semibold text-stone-900">{visibleCount}</span>
          {visibleCount !== totalCount && <> of {totalCount}</>} student
          {visibleCount === 1 ? "" : "s"}
        </p>

        {hasActiveFilter && (
          <button
            type="button"
            onClick={() => onChange({ unitId: null, bucket: null })}
            className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium text-stone-600 transition hover:bg-stone-100"
          >
            <X className="h-3.5 w-3.5" aria-hidden="true" />
            Clear
          </button>
        )}
      </div>
    </div>
  );
}