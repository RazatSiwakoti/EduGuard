import type { ReactNode } from "react";

interface ChartCardProps {
  title: string;
  /** One line explaining what the reader is looking at. */
  subtitle?: string;
  /**
   * Compact right-aligned slot — a single figure or a two-item key.
   * Anything wider belongs in `legend`: a wide node here competes with
   * the title for horizontal space and squeezes it into a narrow column.
   */
  action?: ReactNode;
  /**
   * Full-width row beneath the header, for legends with enough items
   * that they cannot sit beside the title without wrecking it.
   */
  legend?: ReactNode;
  /** Rendered instead of children when there is genuinely no data. */
  empty?: boolean;
  emptyMessage?: string;
  /** Makes the card span both grid columns. */
  wide?: boolean;
  children: ReactNode;
}

/**
 * The shared shell every chart sits in.
 *
 * Exists so all six visuals get identical padding, heading weight and
 * empty-state behaviour without each one re-inventing them — and so a
 * spacing change happens once rather than six times.
 *
 * The empty state is a first-class prop rather than an afterthought.
 * A cross-filtering dashboard produces empty combinations constantly
 * (filter to one unit, then to "Needs Review", and a chart legitimately
 * has nothing to draw). Rendering an explanatory message beats
 * rendering an axis with no marks, which just looks broken.
 */
export default function ChartCard({
  title,
  subtitle,
  action,
  legend,
  empty = false,
  emptyMessage = "No data for the current filters.",
  wide = false,
  children,
}: ChartCardProps) {
  return (
    <section
      className={`flex flex-col rounded-lg border border-stone-200 bg-white p-5 ${
        wide ? "lg:col-span-2" : ""
      }`}
    >
      <header className="mb-4">
        <div className="flex items-start justify-between gap-4">
          {/* min-w-0 lets the heading block shrink and wrap normally
              instead of being forced into a sliver by a wide action. */}
          <div className="min-w-0">
            <h2 className="text-sm font-semibold text-stone-900">{title}</h2>
            {subtitle && (
              <p className="mt-0.5 text-xs leading-relaxed text-stone-500">{subtitle}</p>
            )}
          </div>
          {action && <div className="shrink-0">{action}</div>}
        </div>

        {legend && (
          <div className="mt-3 flex flex-wrap items-center gap-1.5">{legend}</div>
        )}
      </header>

      {empty ? (
        <div className="flex flex-1 items-center justify-center py-10">
          <p className="max-w-xs text-center text-xs text-stone-400">{emptyMessage}</p>
        </div>
      ) : (
        <div className="flex-1">{children}</div>
      )}
    </section>
  );
}