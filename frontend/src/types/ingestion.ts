/**
 * Types for the bulk import pipeline.
 *
 * Mirrors app/schemas/ingestion.py. Two endpoints are involved and they
 * are deliberately separate calls:
 *
 *   POST /units/{id}/ingest/preview  — reads the file, stores nothing
 *   POST /units/{id}/ingest/bulk     — applies a mapping and stores
 *
 * The split exists because a lecturer cannot map columns to criteria
 * until they can see what columns their file actually has, and /bulk
 * requires the mapping and the file in the same request.
 */

/** Response from POST /units/{id}/ingest/preview. */
export interface FilePreviewResult {
  filename: string;
  columns: string[];
  total_rows: number;
  /** Values are whatever the cell held — string, number, or null. */
  sample_rows: Record<string, unknown>[];
}

/**
 * The mapping sent to /bulk, as a JSON string in a multipart form field.
 *
 * `criteria_column_map` is criteria_id → one column name, for
 * single-value criteria (assessments, Moodle).
 *
 * `weekly_criteria_column_map` is criteria_id → an ORDERED list of
 * column names. Order is not cosmetic: the backend reads the list
 * positionally as week 1, week 2, … and computes the early-vs-late
 * trend from those positions. Shuffle the list and the percentage still
 * comes out right while the trend value becomes meaningless.
 */
export interface BulkIngestionMapping {
  student_number_col: string;
  name_col: string;
  email_col?: string | null;
  program_col?: string | null;
  gender_col?: string | null;
  age_col?: string | null;
  criteria_column_map: Record<number, string>;
  weekly_criteria_column_map: Record<number, string[]>;
}

export interface IngestionRowError {
  row: number | null;
  student_number: string | null;
  criteria: string | null;
  reason: string;
}

export interface IngestionRowWarning {
  row: number | null;
  student_number: string | null;
  message: string;
}

/** One student's outcome from the analysis that runs after import. */
export interface StudentAnalysisResult {
  student_id: number;
  rule_level: string;
  ml_level: string;
  final_tier: string | null;
  requires_review: boolean;
}

export interface AnalysisSummary {
  total_students: number;
  succeeded: number;
  failed: number;
  results: StudentAnalysisResult[];
  errors: Record<string, unknown>[];
}

/**
 * Response from POST /units/{id}/ingest/bulk.
 *
 * Note `values_stored` and `values_failed` count individual criterion
 * VALUES, not rows — one row with four mapped criteria contributes up
 * to four values. `total_rows` is the only row-level count.
 */
export interface BulkIngestionResult {
  batch_id: number;
  filename: string;
  total_rows: number;
  rows_with_errors: number;
  values_stored: number;
  values_failed: number;
  errors: IngestionRowError[];
  warnings: IngestionRowWarning[];
  /** Null only when no student had a single value stored. */
  analysis_summary: AnalysisSummary | null;
}

/* ------------------------------------------------------------------ */
/* Manual single-student entry                                         */
/* ------------------------------------------------------------------ */

/**
 * Body for POST /units/{id}/ingest/manual.
 *
 * `scores` is criteria_id → one number, for single-value criteria.
 *
 * `weekly_scores` is criteria_id → RAW STRINGS in week order, not
 * numbers. The backend runs each value through the same
 * parse_attendance_cell / parse_tutorial_cell used by bulk upload, so
 * manual entry and CSV import can never compute a percentage
 * differently from one another.
 */
export interface ManualEntryCreate {
  student_number: string;
  name?: string | null;
  email?: string | null;
  program?: string | null;
  gender?: string | null;
  age?: number | null;
  scores: Record<number, number>;
  weekly_scores: Record<number, string[]>;
}

export interface ManualEntryResult {
  student_number: string;
  events_created: number;
  errors: IngestionRowError[];
  warnings: IngestionRowWarning[];
  /** Null when no events were created — nothing to analyse. */
  analysis_result: StudentAnalysisResult | null;
    student_created: boolean;
    enrollment_created: boolean;
}

/**
 * The exact strings parse_attendance_cell() treats as present.
 * Anything else — including a blank — counts as absent.
 */
export const ATTENDANCE_PRESENT = "yes";
export const ATTENDANCE_ABSENT = "no";

/**
 * The three tutorial statuses, matching TUTORIAL_STATUS_CREDIT's keys
 * on the backend. "late" earns 0.8 credit, which is why it is a
 * distinct option rather than being folded into submitted or missed.
 */
export const TUTORIAL_STATUSES = [
  { value: "submitted", label: "Submitted", credit: "full credit" },
  { value: "late", label: "Late", credit: "80% credit" },
  { value: "not_submitted", label: "Not submitted", credit: "no credit" },
] as const;
/** Which step of the wizard is on screen. */
export type ImportStep = "file" | "identity" | "criteria" | "review" | "result";

/**
 * The identity columns, held separately from criteria mapping because
 * they describe the PERSON rather than their performance, and because
 * only the first two are mandatory.
 */
export interface IdentityMapping {
  student_number_col: string;
  name_col: string;
  email_col: string;
  program_col: string;
  gender_col: string;
  age_col: string;
}

/** Empty identity mapping — "" means "not mapped". */
export const EMPTY_IDENTITY: IdentityMapping = {
  student_number_col: "",
  name_col: "",
  email_col: "",
  program_col: "",
  gender_col: "",
  age_col: "",
};
