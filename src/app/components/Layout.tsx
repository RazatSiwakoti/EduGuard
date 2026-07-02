import { Outlet, Navigate, useLocation } from "react-router";
import { Toaster } from "sonner";
import { TopNav } from "./TopNav";
import { SideNav } from "./SideNav";
import { useTheme } from "../context/ThemeContext";

export function Layout() {
  const isAuth = localStorage.getItem("edguard_auth") === "true";
  if (!isAuth) return <Navigate to="/login" replace />;

  const location = useLocation();
  const isSettings = location.pathname === "/settings";
  const { isDark } = useTheme();

  return (
    <div
      style={{
        minHeight: "100vh",
        background: isDark ? "#0D1B2A" : "#F6F5F1",
        backgroundImage: isDark
          ? `radial-gradient(1200px 600px at 85% -10%, rgba(24,95,165,0.15), transparent 60%),
             radial-gradient(900px 500px at -10% 110%, rgba(239,159,39,0.07), transparent 55%)`
          : `radial-gradient(1200px 600px at 85% -10%, rgba(24,95,165,0.08), transparent 60%),
             radial-gradient(900px 500px at -10% 110%, rgba(239,159,39,0.06), transparent 55%),
             url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='160' height='160'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/><feColorMatrix values='0 0 0 0 0.09  0 0 0 0 0.11  0 0 0 0 0.15  0 0 0 0.035 0'/></filter><rect width='100%25' height='100%25' filter='url(%23n)'/></svg>")`,
        fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'SF Pro Display', sans-serif",
        color: isDark ? "#F1F5F9" : "#121826",
        transition: "background 0.3s ease, color 0.3s ease",
      }}
    >
      <Toaster position="top-right" richColors closeButton />
      {!isSettings && <TopNav />}
      {!isSettings && <SideNav />}
      <main
        style={{
          marginLeft: isSettings ? "0" : "240px",
          marginTop: isSettings ? "0" : "64px",
          padding: isSettings ? "0" : "28px 32px 48px",
          minHeight: "100vh",
          position: "relative",
        }}
      >
        <Outlet />
      </main>
      <style>{`
        @keyframes pulse { 0%, 100% { opacity: 1; transform: scale(1);} 50% { opacity: 0.5; transform: scale(1.15);} }
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes fadeInUp { from { opacity: 0; transform: translateY(14px);} to { opacity: 1; transform: translateY(0);} }
        @keyframes slideIn { from { opacity: 0; transform: translateX(-8px);} to { opacity: 1; transform: translateX(0);} }
        @keyframes shimmer { 0% { background-position: -200% 0;} 100% { background-position: 200% 0;} }
        @keyframes drawLine { from { stroke-dashoffset: 200; } to { stroke-dashoffset: 0; } }
        @keyframes riseBar { from { transform: scaleY(0); opacity: 0;} to { transform: scaleY(1); opacity: 1;} }
        @keyframes float { 0%,100% { transform: translateY(0);} 50% { transform: translateY(-3px);} }
        * { box-sizing: border-box; }
        body { margin: 0; }
        ::-webkit-scrollbar { width: 7px; height: 7px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #D1D5DB; border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: #9CA3AF; }
        ::selection { background: #185FA5; color: #fff; }
      `}</style>
    </div>
  );
}