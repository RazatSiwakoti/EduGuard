import { useEffect, useState } from "react";
import { evaluationService, type ModelEvaluation } from "../services/evaluationService";
import { sequentialStep } from "../components/dashboard/chartTheme";

const gloss: Record<string, string> = {
  precision: "of flagged students, how many failed or withdrew",
  recall: "of students who failed, how many we flagged",
  f1: "balance between precision and recall",
  specificity: "of students who passed, how many stayed unflagged",
  base_rate: "share of resolved students who failed or withdrew",
};

export default function ModelPerformancePage() {
  const [data, setData] = useState<ModelEvaluation | null>(null);
  useEffect(() => { evaluationService.get().then(setData).catch(() => setData(null)); }, []);
  if (!data) return <div className="p-8 text-stone-500">Loading model performance…</div>;
  const m = data.metrics;
  const matrix = data.confusion_matrix;
  const max = Math.max(matrix.tp, matrix.fp, matrix.tn, matrix.fn, 1);
  return <main className="min-h-screen bg-stone-50 px-6 py-8"><div className="mx-auto max-w-6xl space-y-6">
    <h1 className="text-2xl font-semibold">Model performance</h1>
    <div className="rounded-lg border border-blue-200 bg-blue-50 p-4">
      Based on {data.coverage.resolved} of {data.coverage.total} enrolments with recorded outcomes ({Math.round(data.coverage.percentage * 100)}%).
    </div>
    {m.suppressed && <div className="rounded border border-amber-200 bg-amber-50 p-3 text-sm">{String(m.reason)}</div>}
    <section><h2 className="mb-2 font-medium">Confusion matrix</h2><div className="grid max-w-md grid-cols-2 gap-2">
      {(["tp", "fp", "fn", "tn"] as const).map(k => <div key={k} style={{ background: sequentialStep(matrix[k], max) || "#fff" }} className="rounded p-5 text-center"><b>{k.toUpperCase()}</b><div className="text-2xl">{matrix[k]}</div></div>)}
    </div></section>
    <section><h2 className="mb-2 font-medium">Hybrid metrics</h2><div className="grid grid-cols-2 gap-3 md:grid-cols-5">{["precision","recall","f1","specificity","base_rate"].map(k => <div className="rounded border bg-white p-3" key={k}><div className="text-xl font-semibold">{typeof m[k] === "number" ? `${Math.round(Number(m[k]) * 100)}%` : "—"}</div><div className="text-xs text-stone-500">{k}</div><p className="mt-1 text-xs">{gloss[k]}</p></div>)}</div></section>
    <section><h2 className="mb-2 font-medium">Engine comparison</h2><table className="w-full bg-white text-left text-sm"><thead><tr><th className="p-2">Engine</th><th>Precision</th><th>Recall</th><th>F1</th><th>Specificity</th></tr></thead><tbody>{Object.entries(data.per_engine_metrics).map(([name, row]) => <tr key={name} className="border-t"><td className="p-2 font-medium">{name}</td>{["precision","recall","f1","specificity"].map(k => <td key={k}>{typeof row[k] === "number" ? `${Math.round(Number(row[k]) * 100)}%` : "—"}</td>)}</tr>)}</tbody></table></section>
    <section><h2 className="mb-2 font-medium">Lead time</h2><p>{data.lead_time.length ? `${data.lead_time.join(", ")} weeks of warning for true positives.` : "No true positives with lead-time data."}</p></section>
    <section><h2 className="mb-2 font-medium">Calibration</h2><p className="text-sm text-stone-500">{data.calibration.length ? "Predicted vs observed failure rate." : "Calibration is unavailable until prediction probabilities are persisted."}</p></section>
  </div></main>;
}
