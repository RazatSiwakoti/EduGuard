import {
  LayoutDashboard,
  Users,
  AlertTriangle,
  BarChart2,
  GraduationCap,
  FileText,
  Mail,
  Database,
} from "lucide-react";
import { NavLink } from "react-router";
import { useTheme } from "../context/ThemeContext";

const mainNavItems = [
  { icon: LayoutDashboard, label: "Dashboard", to: "/" },
  { icon: Users, label: "Students", to: "/students" },
  { icon: AlertTriangle, label: "Alerts", to: "/alerts", badge: 34 },
  { icon: BarChart2, label: "Reports", to: "/reports" },
];

{/* EdGuard System selection 
const systemNavItems = [
  { icon: Database, label: "Import", to: "/reports" },
  { icon: Mail, label: "Email Logs", to: "/alerts" },
  { icon: FileText, label: "Reports Export", to: "/reports" },
];*/}

export function SideNav() {
  const { isDark } = useTheme();

  const bg = isDark
    ? "linear-gradient(180deg, #0F1E30 0%, #0D1B27 100%)"
    : "linear-gradient(180deg, #FFFFFF 0%, #FAFAF7 100%)";
  const borderColor = isDark ? "rgba(255,255,255,0.06)" : "rgba(17,24,39,0.07)";
  const stampText = isDark ? "#CBD5E1" : "#0F172A";
  const stampSub = isDark ? "#4B6480" : "#9CA3AF";
  const labelColor = isDark ? "#4B6480" : "#9CA3AF";
  const cardBg = isDark
    ? "linear-gradient(135deg, #0B3D73 0%, #185FA5 100%)"
    : "linear-gradient(135deg, #0B3D73 0%, #185FA5 100%)";

  const navLinkStyle = (isActive: boolean) => ({
    display: "flex",
    alignItems: "center",
    gap: "12px",
    padding: "10px 12px",
    borderRadius: "10px",
    border: "none",
    cursor: "pointer",
    width: "100%",
    textAlign: "left" as const,
    position: "relative" as const,
    background: isActive
      ? isDark ? "rgba(24,95,165,0.22)" : "#EBF4FF"
      : "transparent",
    transition: "background 0.15s",
    borderLeft: isActive ? "3px solid #185FA5" : "3px solid transparent",
    textDecoration: "none",
  });

  return (
    <aside
      style={{
        width: "240px",
        background: bg,
        borderRight: `1px solid ${borderColor}`,
        display: "flex",
        flexDirection: "column",
        position: "fixed",
        top: "64px",
        left: 0,
        bottom: 0,
        zIndex: 40,
        paddingTop: "18px",
        paddingBottom: "20px",
        boxShadow: isDark ? "1px 0 0 rgba(255,255,255,0.02)" : "1px 0 0 rgba(17,24,39,0.02)",
        transition: "background 0.3s ease",
      }}
    >
      {/* Editorial stamp */}
      <div style={{ padding: "0 20px 14px 20px", borderBottom: `1px dashed ${isDark ? "rgba(255,255,255,0.08)" : "rgba(17,24,39,0.1)"}`, marginBottom: 14 }}>
        <div style={{ fontFamily: "'Instrument Serif', serif", fontStyle: "italic", fontSize: "15px", color: stampText, lineHeight: 1.1 }}>
          Risk Intelligence
        </div>
        <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: "9px", color: stampSub, letterSpacing: "0.14em", marginTop: 4, textTransform: "uppercase" }}>
          Faculty Console / 01
        </div>
      </div>

      {/* Nav label */}
      <div style={{ padding: "0 16px 8px 16px" }}>
        <span style={{ color: labelColor, fontSize: "10px", fontWeight: "600", letterSpacing: "0.08em", textTransform: "uppercase" }}>
          Main Menu
        </span>
      </div>

      {/* Nav items */}
      <nav style={{ flex: 1, padding: "4px 12px", display: "flex", flexDirection: "column", gap: "2px" }}>
        {mainNavItems.map(({ icon: Icon, label, to, badge }) => (
          <NavLink
            key={label}
            to={to}
            end={to === "/"}
            style={({ isActive }) => navLinkStyle(isActive)}
          >
            {({ isActive }) => (
              <>
                <Icon
                  size={18}
                  color={isActive ? "#185FA5" : isDark ? "#64748B" : "#6B7280"}
                  strokeWidth={isActive ? 2.2 : 1.8}
                />
                <span
                  style={{
                    color: isActive ? "#185FA5" : isDark ? "#94A3B8" : "#6B7280",
                    fontSize: "14px",
                    fontWeight: isActive ? "600" : "400",
                    flex: 1,
                  }}
                >
                  {label}
                </span>
                {badge && (
                  <span
                    style={{
                      background: "#E24B4A",
                      color: "#FFFFFF",
                      fontSize: "10px",
                      fontWeight: "700",
                      padding: "1px 6px",
                      borderRadius: "999px",
                      minWidth: "20px",
                      textAlign: "center",
                    }}
                  >
                    {badge}
                  </span>
                )}
              </>
            )}
          </NavLink>
        ))}

        {/* EdGuard System Section 
        <div style={{ padding: "16px 0 8px 0", marginTop: "8px", borderTop: `1px solid ${isDark ? "rgba(255,255,255,0.07)" : "#E5E7EB"}` }}>
          <span
            style={{
              color: labelColor,
              fontSize: "10px",
              fontWeight: "600",
              letterSpacing: "0.08em",
              textTransform: "uppercase",
              paddingLeft: "12px",
            }}
          >
            EdGuard System
          </span>
        </div>

        {systemNavItems.map(({ icon: Icon, label, to }) => (
          <NavLink
            key={label}
            to={to}
            style={({ isActive }) => navLinkStyle(isActive)}
          >
            {({ isActive }) => (
              <>
                <Icon
                  size={18}
                  color={isActive ? "#185FA5" : isDark ? "#64748B" : "#6B7280"}
                  strokeWidth={isActive ? 2.2 : 1.8}
                />
                <span
                  style={{
                    color: isActive ? "#185FA5" : isDark ? "#94A3B8" : "#6B7280",
                    fontSize: "14px",
                    fontWeight: isActive ? "600" : "400",
                    flex: 1,
                  }}
                >
                  {label}
                </span>
              </>
            )}
          </NavLink>
        ))}*/}
      </nav>

      {/* Bottom: Academic Year */}
      <div
        style={{
          margin: "0 12px",
          padding: "14px 14px 12px",
          background: cardBg,
          borderRadius: "12px",
          display: "flex",
          flexDirection: "column",
          gap: "6px",
          position: "relative",
          overflow: "hidden",
          boxShadow: "0 8px 20px -10px rgba(24,95,165,0.55)",
        }}
      >
        <div aria-hidden style={{ position: "absolute", right: -18, top: -18, width: 90, height: 90, borderRadius: "50%", background: "radial-gradient(closest-side, rgba(239,159,39,0.35), transparent 70%)" }} />
        <div style={{ display: "flex", alignItems: "center", gap: "8px", zIndex: 1 }}>
          <GraduationCap size={15} color="#FFD799" />
          <span style={{ color: "#FFFFFF", fontSize: "12px", fontWeight: 700, letterSpacing: "0.02em" }}>
            Term 1 · 2026
          </span>
        </div>
        <span style={{ fontFamily: "'Instrument Serif', serif", fontStyle: "italic", color: "rgba(255,255,255,0.85)", fontSize: "12px", zIndex: 1 }}>
          Active academic period
        </span>
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 4, zIndex: 1 }}>
          <div style={{ flex: 1, height: 3, background: "rgba(255,255,255,0.2)", borderRadius: 2, overflow: "hidden" }}>
            <div style={{ width: "67%", height: "100%", background: "linear-gradient(90deg,#FFD799,#FFFFFF)", borderRadius: 2 }} />
          </div>
          <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 9, color: "rgba(255,255,255,0.9)", fontWeight: 600 }}>W8/12</span>
        </div>
      </div>

      <div style={{ padding: "12px 20px 0 20px", display: "flex", alignItems: "center", gap: 6 }}>
        <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 9, color: isDark ? "#4B6480" : "#9CA3AF", letterSpacing: "0.12em", textTransform: "uppercase" }}>
          KOI · Sydney
        </span>
        <div style={{ flex: 1, height: 1, background: isDark ? "rgba(255,255,255,0.06)" : "rgba(17,24,39,0.08)" }} />
        <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 9, color: isDark ? "#4B6480" : "#9CA3AF" }}>↗</span>
      </div>
    </aside>
  );
}