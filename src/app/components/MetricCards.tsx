import { Users, AlertTriangle, Bell, Brain, TrendingUp, TrendingDown } from "lucide-react";
import { useEffect, useState } from "react";
import {fetchDashboardSummary, type DashboardSummary,} from "../api/dashboard";

interface MetricCardProps {
  icon: React.ReactNode;
  kicker: string;
  title: string;
  value: string;
  unit?: string;
  subtitle: string;
  valueColor: string;
  iconBg: string;
  iconBorder: string;
  spark: number[];
  sparkColor: string;
  trend?: { value: string; up: boolean; good: boolean };
  delay: number;
}

function Sparkline({ data, color }: { data: number[]; color: string }) {
  const w = 96, h = 30;
  const max = Math.max(...data), min = Math.min(...data);
  const range = max - min || 1;
  const pts = data.map((v, i) => {
    const x = (i / (data.length - 1)) * w;
    const y = h - ((v - min) / range) * h;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");
  const area = `0,${h} ${pts} ${w},${h}`;
  const id = `sp-${color.replace("#", "")}`;
  return (
    <svg width={w} height={h} style={{ display: "block" }}>
      <defs>
        <linearGradient id={id} x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.28" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <polygon points={area} fill={`url(#${id})`} />
      <polyline
        points={pts}
        fill="none"
        stroke={color}
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
        style={{ strokeDasharray: 200, animation: "drawLine 1.4s ease-out forwards" }}
      />
      <circle cx={w} cy={h - ((data[data.length - 1] - min) / range) * h} r="2.5" fill={color} />
    </svg>
  );
}

function MetricCard(props: MetricCardProps) {
  const [hover, setHover] = useState(false);
  const { icon, kicker, title, value, unit, subtitle, valueColor, iconBg, iconBorder, spark, sparkColor, trend, delay } = props;
  return (
    <div
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        background: "#FFFFFF",
        borderRadius: "14px",
        padding: "18px 18px 14px",
        border: "1px solid rgba(17,24,39,0.06)",
        boxShadow: hover
          ? "0 14px 40px -18px rgba(17,24,39,0.22), 0 2px 6px rgba(17,24,39,0.05)"
          : "0 1px 2px rgba(17,24,39,0.04), 0 1px 10px -6px rgba(17,24,39,0.06)",
        flex: 1,
        display: "flex",
        flexDirection: "column",
        gap: "10px",
        minWidth: 0,
        position: "relative",
        overflow: "hidden",
        transform: hover ? "translateY(-2px)" : "translateY(0)",
        transition: "transform 0.25s cubic-bezier(.2,.7,.2,1), box-shadow 0.25s",
        animation: `fadeInUp 0.5s ${delay}ms both cubic-bezier(.2,.7,.2,1)`,
      }}
    >
      {/* Corner accent number */}
      <span style={{
        position: "absolute", top: 10, right: 14,
        fontFamily: "'JetBrains Mono', monospace", fontSize: 9, color: "#D1D5DB",
        letterSpacing: "0.14em"
      }}>
        {kicker}
      </span>

      {/* Icon + title */}
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <div
          style={{
            width: "34px", height: "34px",
            background: iconBg,
            borderRadius: "9px",
            display: "flex", alignItems: "center", justifyContent: "center",
            flexShrink: 0,
            border: `1px solid ${iconBorder}`,
          }}
        >
          {icon}
        </div>
        <div style={{ display: "flex", flexDirection: "column", lineHeight: 1.1 }}>
          <span style={{ color: "#4B5563", fontSize: "12px", fontWeight: 600, letterSpacing: "0.01em" }}>
            {title}
          </span>
          <span style={{ fontFamily: "'Instrument Serif', serif", fontStyle: "italic", color: "#9CA3AF", fontSize: "11px", marginTop: 2 }}>
            {subtitle}
          </span>
        </div>
      </div>

      {/* Value + sparkline row */}
      <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", gap: 10, marginTop: 2 }}>
        <div style={{ display: "flex", alignItems: "baseline", gap: 4 }}>
          <span
            className="tabular"
            style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: "30px",
              fontWeight: 600,
              color: valueColor,
              lineHeight: 1,
              letterSpacing: "-0.03em",
            }}
          >
            {value}
          </span>
          {unit && (
            <span style={{ fontFamily: "'Instrument Serif', serif", fontStyle: "italic", color: "#9CA3AF", fontSize: 14 }}>
              {unit}
            </span>
          )}
        </div>
        <Sparkline data={spark} color={sparkColor} />
      </div>

      {/* Trend pill */}
      {trend && (
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 2 }}>
          <span style={{
            display: "inline-flex", alignItems: "center", gap: 3,
            fontSize: "10.5px", fontWeight: 700,
            color: trend.good ? "#047857" : "#B91C1C",
            background: trend.good ? "rgba(16,185,129,0.09)" : "rgba(239,68,68,0.08)",
            padding: "2px 7px 2px 5px", borderRadius: "999px",
            fontFamily: "'JetBrains Mono', monospace", letterSpacing: "0.02em"
          }}>
            {trend.up ? <TrendingUp size={10} /> : <TrendingDown size={10} />}
            {trend.value}
          </span>
          <span style={{ color: "#9CA3AF", fontSize: 11 }}>vs. Week 4</span>
        </div>
      )}
    </div>
  );
}

export function MetricCards() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

 useEffect(() => {
  async function loadSummary() {
    try {
      setIsLoading(true);

      const data = await fetchDashboardSummary();

      setSummary(data);
      setError(null);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to load dashboard summary."
      );
    } finally {
      setIsLoading(false);
    }
  }

  loadSummary();
 }, []);

  const cards: MetricCardProps[] = [
    {
      icon: <Users size={16} color="#185FA5" strokeWidth={2} />,
      kicker: "01 / COHORT",
      title: "Total Students",
      value: summary?.total_students.toString() ?? "0",
      subtitle: "enrolled this term",
      valueColor: "#0F172A",
      iconBg: "#EBF4FF", iconBorder: "rgba(24,95,165,0.18)",
      spark: [220, 226, 230, 234, 238, 241, 245, 248],
      sparkColor: "#185FA5",
      trend: { value: "+12 new", up: true, good: true },
      delay: 0,
    },
    {
      icon: <AlertTriangle size={16} color="#DC2626" strokeWidth={2} />,
      kicker: "02 / RISK",
      title: "At-Risk Students",
      value: summary?.at_risk_students.toString() ?? "0",
      subtitle: "require intervention",
      valueColor: "#B91C1C",
      iconBg: "#FEF2F2", iconBorder: "rgba(220,38,38,0.18)",
      spark: [68, 72, 74, 78, 82, 85, 87, 89],
      sparkColor: "#DC2626",
      trend: { value: "+7 more", up: true, good: false },
      delay: 80,
    },
    {
      icon: <Bell size={16} color="#B45309" strokeWidth={2} />,
      kicker: "03 / SMTP",
      title: "Alerts Dispatched",
      value: summary?.alerts_dispatched.toString() ?? "0",
      subtitle: "sent this week",
      valueColor: "#B45309",
      iconBg: "#FFFBEB", iconBorder: "rgba(180,83,9,0.18)",
      spark: [6, 12, 14, 20, 24, 28, 31, 34],
      sparkColor: "#EF9F27",
      trend: { value: "+5 today", up: true, good: true },
      delay: 160,
    },
    {
      icon: <Brain size={16} color="#047857" strokeWidth={2} />,
      kicker: "04 / ML MODEL",
      title: "Model Accuracy",
      value: summary?.model_accuracy?.toString() ?? "0",
      unit: "%",
      subtitle: "F1 · SHAP verified",
      valueColor: "#047857",
      iconBg: "#ECFDF5", iconBorder: "rgba(4,120,87,0.18)",
      spark: [66, 68, 69, 70, 71, 72, 73, 74],
      sparkColor: "#10B981",
      trend: { value: "+2.1%", up: true, good: true },
      delay: 240,
    },
  ];
  
  if (isLoading) {
  return <div>Loading dashboard metrics...</div>;
 }

 if (error) {
  return <div>Unable to load dashboard metrics: {error}</div>;
 }

  return (
    <div style={{ display: "flex", gap: "16px" }}>
      {cards.map((card) => (
        <MetricCard key={card.title} {...card} />
      ))}
    </div>
  );
}