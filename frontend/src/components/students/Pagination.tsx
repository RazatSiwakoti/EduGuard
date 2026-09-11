import { ChevronLeft, ChevronRight } from "lucide-react";
import { pageItems } from "../../utils/studentsTable";

interface PaginationProps {
  page: number;
  totalPages: number;
  /** Rows across every page, for the "showing x–y of z" line. */
  totalRows: number;
  /** First and last row index shown, 1-based and inclusive. */
  firstRow: number;
  lastRow: number;
  onChange: (page: number) => void;
}

/**
 * Page controls for the students table.
 *
 * Client-side: the whole cohort is already in memory from the dashboard
 * query, so paging is a slice, not a request. A lecturer clicking
 * through pages never waits.
 *
 * The number row is windowed via `pageItems`, so the control stays a
 * fixed width whether there are three pages or forty. Prev/Next are
 * disabled rather than hidden at the ends — a control that disappears
 * makes the row reflow and moves the button the user was aiming at.
 *
 * The "showing 9–16 of 47" line matters more than it looks: with eight
 * rows per page, a lecturer needs to know how much of the cohort is
 * still below them without counting pages.
 */
export default function Pagination({
  page,
  totalPages,
  totalRows,
  firstRow,
  lastRow,
  onChange,
}: PaginationProps) {
  // One page of results needs no controls, but the count line is still
  // worth showing so the table always states its own size.
  const items = pageItems(page, totalPages);

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border-t border-stone-200 bg-stone-50/60 px-4 py-3">
      <p className="text-xs tabular-nums text-stone-500" aria-live="polite">
        Showing {firstRow}–{lastRow} of {totalRows}
      </p>

      {totalPages > 1 && (
        <nav className="flex items-center gap-1" aria-label="Students table pages">
          <button
            type="button"
            onClick={() => onChange(page - 1)}
            disabled={page === 1}
            className="flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs font-medium text-stone-600 transition hover:bg-white hover:text-stone-900 disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-transparent"
          >
            <ChevronLeft className="h-3.5 w-3.5" aria-hidden="true" />
            Prev
          </button>

          {items.map((item, index) =>
            item === "ellipsis" ? (
              // Index in the key is safe here: the array is regenerated
              // whole on every page change and has no state of its own.
              <span
                key={`gap-${index}`}
                className="px-1.5 text-xs text-stone-400"
                aria-hidden="true"
              >
                …
              </span>
            ) : (
              <button
                key={item}
                type="button"
                onClick={() => onChange(item)}
                aria-current={item === page ? "page" : undefined}
                aria-label={`Page ${item}`}
                className={`min-w-[30px] rounded-lg px-2 py-1.5 text-xs font-medium tabular-nums transition ${
                  item === page
                    ? "bg-stone-900 text-white"
                    : "text-stone-600 hover:bg-white hover:text-stone-900"
                }`}
              >
                {item}
              </button>
            ),
          )}

          <button
            type="button"
            onClick={() => onChange(page + 1)}
            disabled={page === totalPages}
            className="flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs font-medium text-stone-600 transition hover:bg-white hover:text-stone-900 disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-transparent"
          >
            Next
            <ChevronRight className="h-3.5 w-3.5" aria-hidden="true" />
          </button>
        </nav>
      )}
    </div>
  );
}