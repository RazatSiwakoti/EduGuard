import api from "./api";
import type {
  BulkIngestionMapping,
  BulkIngestionResult,
  FilePreviewResult,
  ManualEntryCreate,
  ManualEntryResult,
} from "../types/ingestion";

/**
 * Bulk import for one unit.
 *
 * Both calls send multipart form data, not JSON, because they carry a
 * file. `Content-Type` is explicitly set to `undefined` on each request
 * to REMOVE the `application/json` default that api.ts sets globally —
 * axios then detects the FormData body and writes the correct
 * `multipart/form-data` header including its boundary parameter.
 *
 * Setting `"multipart/form-data"` by hand would be worse than leaving
 * the default: the header would arrive with no boundary, and the server
 * cannot split the parts without one.
 */
export const ingestionService = {
  /**
   * Reads a file and returns its columns and a few sample rows.
   * Stores nothing — safe to call repeatedly while a lecturer decides
   * whether they picked the right file.
   */
  preview: async (unitId: number, file: File): Promise<FilePreviewResult> => {
    const form = new FormData();
    form.append("file", file);

    const res = await api.post<FilePreviewResult>(
      `/units/${unitId}/ingest/preview`,
      form,
      { headers: { "Content-Type": undefined } },
    );
    return res.data;
  },

  /**
   * Applies a mapping and stores the data, then runs the full risk
   * analysis for every student touched.
   *
   * The mapping travels as a JSON STRING in a form field rather than as
   * a JSON body, because a multipart request can carry the file and the
   * mapping together — which is what the backend's signature expects
   * (`mapping: str = Form(...)`).
   */
  bulk: async (
    unitId: number,
    file: File,
    mapping: BulkIngestionMapping,
  ): Promise<BulkIngestionResult> => {
    const form = new FormData();
    form.append("file", file);
    form.append("mapping", JSON.stringify(mapping));

    const res = await api.post<BulkIngestionResult>(
      `/units/${unitId}/ingest/bulk`,
      form,
      { headers: { "Content-Type": undefined } },
    );
    return res.data;
  },

    /**
   * Adds or updates ONE student by hand, then scores them.
   *
   * Ordinary JSON, not multipart — there is no file involved, so the
   * Content-Type override the other two need does not apply here.
   *
   * Goes through the exact same ingestion service as bulk upload, so a
   * student entered by hand is indistinguishable downstream from one
   * that arrived in a spreadsheet. The response carries that student's
   * full analysis result, which makes this the quickest way to confirm
   * the whole rule → ML → hybrid pipeline is working.
   */
  manual: async (
    unitId: number,
    payload: ManualEntryCreate,
  ): Promise<ManualEntryResult> => {
    const res = await api.post<ManualEntryResult>(
      `/units/${unitId}/ingest/manual`,
      payload,
    );
    return res.data;
  },
};
