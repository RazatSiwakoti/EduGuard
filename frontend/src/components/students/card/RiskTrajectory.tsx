import type { TrajectoryRow } from "../../../hooks/useStudentTrajectory";

const tierY: Record<string, number> = { high_risk: 12, low_risk: 40, safe: 68 };
const tierLabel: Record<string, string> = { high_risk: "High", low_risk: "Low", safe: "Safe" };

export default function RiskTrajectory({ rows }: { rows: TrajectoryRow[] }) {
  if (!rows.length) return null;
  const width = 320;
  const x = (index: number) => 34 + index * ((width - 54) / Math.max(rows.length - 1, 1));
  const line = (key: "rule_tier" | "ml_tier") =>
    rows.map((row, index) => `${x(index)},${tierY[row[key] ?? ""] ?? 82}`).join(" ");
  return (
    <div className="rounded-lg border border-stone-200 bg-white p-3">
      <p className="text-xs font-semibold text-stone-700">Risk trajectory</p>
      <svg viewBox={`0 0 ${width} 92`} className="mt-2 w-full" role="img" aria-label="Risk trajectory by checkpoint">
        {[["high_risk", 12], ["low_risk", 40], ["safe", 68]].map(([tier, y]) => (
          <text key={tier} x="0" y={Number(y) + 4} fontSize="8" fill="#78716c">{tierLabel[String(tier)]}</text>
        ))}
        <polyline points={line("rule_tier")} fill="none" stroke="#2563eb" strokeWidth="2" />
        <polyline points={line("ml_tier")} fill="none" stroke="#d97706" strokeWidth="2" strokeDasharray="4 3" />
        {rows.map((row, index) => <text key={row.checkpoint_week} x={x(index) - 9} y="90" fontSize="8" fill="#78716c">W{row.checkpoint_week}</text>)}
      </svg>
      <div className="text-[10px] text-stone-500">Rule engine · ML engine</div>
    </div>
  );
}
