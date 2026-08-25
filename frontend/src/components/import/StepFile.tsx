import { useRef, useState } from "react";
import { FileSpreadsheet, Loader2, Upload } from "lucide-react";
import type { FilePreviewResult } from "../../types/ingestion";

interface StepFileProps {
  file: File | null;
  preview: FilePreviewResult | null;
  isLoading: boolean;
  onFileChosen: (file: File) => void;
}

/**
 * Step 1 — pick a file and confirm it parsed correctly.
 *
 * The preview is the point of this step. Uploading a spreadsheet and
 * only finding out afterwards that the delimiter was wrong, or that row
 * 1 was a title rather than headers, is how people end up with a
 * cohort full of garbage. Showing the detected columns and the first
 * few rows back BEFORE anything is stored turns that into a two-second
 * visual check.
 *
 * Nothing is written to the database by this step.
 */
export default function StepFile({
  file,
  preview,
  isLoading,
  onFileChosen,
}: StepFileProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);

  function handleFiles(files: FileList | null) {
    const chosen = files?.[0];
    if (chosen) onFileChosen(chosen);
  }

  return (
    <div className="space-y-5">
      <div
        // Drag-and-drop AND click-to-browse. The drop zone is the whole
        // panel rather than a small target, since a dragged file is
        // aimed roughly.
        onDragOver={(event) => {
          event.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setIsDragging(false);
          handleFiles(event.dataTransfer.files);
        }}
        className={`rounded-lg border-2 border-dashed p-8 text-center transition ${
          isDragging ? "border-stone-400 bg-stone-50" : "border-stone-300 bg-white"
        }`}
      >
        <Upload className="mx-auto h-7 w-7 text-stone-300" aria-hidden="true" />

        <p className="mt-3 text-sm text-stone-600">
          Drop a spreadsheet here, or{" "}
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            className="font-medium text-stone-900 underline underline-offset-2"
          >
            browse for one
          </button>
        </p>
        <p className="mt-1 text-xs text-stone-400">
          .csv, .xlsx or .xls · nothing is saved until you confirm the mapping
        </p>

        <input
          ref={inputRef}
          type="file"
          accept=".csv,.xlsx,.xls"
          className="hidden"
          onChange={(event) => handleFiles(event.target.files)}
        />
      </div>

      {isLoading && (
        <p className="flex items-center justify-center gap-2 text-sm text-stone-500">
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
          Reading your file…
        </p>
      )}

      {file && preview && !isLoading && (
        <div className="rounded-lg border border-stone-200 bg-white">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 border-b border-stone-200 px-4 py-3">
            <FileSpreadsheet className="h-4 w-4 text-stone-400" aria-hidden="true" />
            <span className="text-sm font-medium text-stone-900">
              {preview.filename}
            </span>
            <span className="text-xs text-stone-500">
              {preview.total_rows} row{preview.total_rows === 1 ? "" : "s"} ·{" "}
              {preview.columns.length} columns
            </span>
          </div>

          {/* Scrolls inside its own container so a 40-column file never
              makes the whole page scroll sideways. */}
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-stone-50 text-stone-500">
                <tr>
                  {preview.columns.map((column) => (
                    <th
                      key={column}
                      className="whitespace-nowrap px-3 py-2 font-medium"
                    >
                      {column}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-100">
                {preview.sample_rows.map((row, index) => (
                  <tr key={index}>
                    {preview.columns.map((column) => (
                      <td
                        key={column}
                        className="whitespace-nowrap px-3 py-2 text-stone-600"
                      >
                        {/* A blank cell arrives as null and is shown as
                            an em dash — visibly empty rather than
                            invisibly missing. */}
                        {row[column] === null || row[column] === undefined
                          ? "—"
                          : String(row[column])}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <p className="border-t border-stone-200 px-4 py-2.5 text-[11px] text-stone-400">
            Showing the first {preview.sample_rows.length} row
            {preview.sample_rows.length === 1 ? "" : "s"}. Check the columns look right
            before continuing.
          </p>
        </div>
      )}
    </div>
  );
}
