import { Bell, X, ChevronDown, Settings, LogOut } from "lucide-react";
import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router";
import { useTheme } from "../context/ThemeContext";

const notifItems = [
  { id: 1, text: "Sarah Johnson flagged as HIGH risk", time: "2h ago", color: "#E24B4A", bg: "#FEE2E2" },
  { id: 2, text: "Moodle sync completed — 248 records", time: "10m ago", color: "#185FA5", bg: "#EBF4FF" },
  { id: 3, text: "Weekly report is ready to download", time: "1d ago", color: "#97C459", bg: "#ECFDF5" },
];

export function TopNav() {
  const [showNotifs, setShowNotifs] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [dismissed, setDismissed] = useState<number[]>([]);
  const notifRef = useRef<HTMLDivElement>(null);
  const userMenuRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  const { isDark } = useTheme();

  const visible = notifItems.filter((n) => !dismissed.includes(n.id));

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) setShowNotifs(false);
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) setShowUserMenu(false);
    };
    if (showNotifs || showUserMenu) document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [showNotifs, showUserMenu]);

  const handleLogout = () => {
    localStorage.removeItem("edguard_auth");
    localStorage.removeItem("edguard_user");
    navigate("/login");
    setShowUserMenu(false);
  };

  const handleSettings = () => {
    navigate("/settings");
    setShowUserMenu(false);
  };

  const bg = isDark ? "rgba(13,27,42,0.92)" : "rgba(255,255,255,0.82)";
  const border = isDark ? "rgba(255,255,255,0.07)" : "rgba(17,24,39,0.08)";
  const titleColor = isDark ? "#F1F5F9" : "#0F172A";
  const subColor = isDark ? "#94A3B8" : "#6B7280";
  const btnBg = isDark ? "#1A2E45" : "#FFFFFF";
  const btnHoverBg = isDark ? "#1E3550" : "#EBF4FF";
  const btnBorder = isDark ? "rgba(255,255,255,0.1)" : "#E5E7EB";
  const dropdownBg = isDark ? "#162232" : "#FFFFFF";
  const dropdownBorder = isDark ? "rgba(255,255,255,0.07)" : "#E5E7EB";
  const dropdownHover = isDark ? "#1A2D45" : "#F9FAFB";
  const dividerColor = isDark ? "rgba(255,255,255,0.08)" : "#E5E7EB";
  const textPrimary = isDark ? "#F1F5F9" : "#1A1A2E";
  const textSecondary = isDark ? "#94A3B8" : "#6B7280";

  return (
    <header
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        height: "64px",
        background: bg,
        backdropFilter: "saturate(180%) blur(16px)",
        WebkitBackdropFilter: "saturate(180%) blur(16px)",
        borderBottom: `1px solid ${border}`,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0 24px",
        zIndex: 1000,
        transition: "background 0.3s ease, border-color 0.3s ease",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
        <div
          style={{
            position: "relative",
            width: "38px",
            height: "38px",
            background: "linear-gradient(140deg, #0B3D73 0%, #185FA5 55%, #2E8FD4 100%)",
            borderRadius: "10px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            boxShadow: "0 6px 16px -4px rgba(24,95,165,0.45), inset 0 1px 0 rgba(255,255,255,0.25)",
          }}
        >
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
            <path d="M12 2 L21 6 V12 C21 17 17 21 12 22 C7 21 3 17 3 12 V6 Z"
                  stroke="#FFFFFF" strokeWidth="1.6" strokeLinejoin="round" fill="rgba(255,255,255,0.08)"/>
            <path d="M8.5 12.2 L11 14.7 L15.8 9.8" stroke="#FFFFFF" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          <span style={{ position: "absolute", top: -3, right: -3, width: 8, height: 8, background: "#EF9F27", borderRadius: "50%", boxShadow: "0 0 0 2px " + (isDark ? "#0D1B2A" : "#fff") }} />
        </div>
        <div style={{ display: "flex", flexDirection: "column", lineHeight: 1 }}>
          <div style={{ display: "flex", alignItems: "baseline", gap: "8px" }}>
            <span style={{ fontSize: "22px", fontWeight: 700, color: titleColor, letterSpacing: "-0.03em" }}>
              Ed<span style={{ fontFamily: "'Instrument Serif', serif", fontStyle: "italic", fontWeight: 400, color: "#185FA5" }}>Guard</span>
            </span>
            <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: "9px", color: subColor, letterSpacing: "0.1em", textTransform: "uppercase", paddingTop: 2 }}>
              KOI · v2.4
            </span>
          </div>
          <div style={{ fontFamily: "'Instrument Serif', serif", fontStyle: "italic", fontSize: "12px", color: subColor, marginTop: 2, letterSpacing: "0.005em" }}>
            Early Detection · Timely Action · Better Outcomes
          </div>
        </div>
      </div>

      {/* Right */}
      <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
        {/* Bell */}
        <div style={{ position: "relative" }} ref={notifRef}>
          <button
            onClick={() => setShowNotifs((v) => !v)}
            style={{ width: "40px", height: "40px", borderRadius: "10px", border: `1px solid ${btnBorder}`, background: showNotifs ? btnHoverBg : btnBg, display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", transition: "background 0.15s" }}
          >
            <Bell size={18} color={showNotifs ? "#185FA5" : subColor} />
          </button>
          {visible.length > 0 && (
            <span style={{ position: "absolute", top: "7px", right: "7px", width: "9px", height: "9px", background: "#E24B4A", borderRadius: "50%", border: `2px solid ${isDark ? "#0D1B2A" : "#FFFFFF"}` }} />
          )}

          {/* Dropdown */}
          {showNotifs && (
            <div
              style={{
                position: "absolute",
                top: "calc(100% + 8px)",
                right: 0,
                width: "320px",
                background: dropdownBg,
                borderRadius: "12px",
                boxShadow: isDark ? "0 8px 32px rgba(0,0,0,0.45)" : "0 8px 32px rgba(0,0,0,0.14)",
                border: `1px solid ${dropdownBorder}`,
                overflow: "hidden",
                zIndex: 200,
              }}
            >
              <div style={{ padding: "14px 16px", borderBottom: `1px solid ${dropdownBorder}`, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ color: textPrimary, fontSize: "14px", fontWeight: "600" }}>Notifications</span>
                {visible.length > 0 && (
                  <span style={{ background: "#FEE2E2", color: "#E24B4A", fontSize: "11px", fontWeight: "700", padding: "2px 7px", borderRadius: "999px" }}>
                    {visible.length}
                  </span>
                )}
              </div>
              {visible.length === 0 ? (
                <div style={{ padding: "24px 16px", textAlign: "center", color: textSecondary, fontSize: "13px" }}>
                  All caught up! 🎉
                </div>
              ) : (
                visible.map((n) => (
                  <div
                    key={n.id}
                    style={{ display: "flex", alignItems: "flex-start", gap: "10px", padding: "12px 16px", borderBottom: `1px solid ${dropdownBorder}`, background: dropdownBg, transition: "background 0.1s" }}
                    onMouseEnter={(e) => ((e.currentTarget as HTMLDivElement).style.background = dropdownHover)}
                    onMouseLeave={(e) => ((e.currentTarget as HTMLDivElement).style.background = dropdownBg)}
                  >
                    <div style={{ width: "8px", height: "8px", borderRadius: "50%", background: n.color, marginTop: "5px", flexShrink: 0 }} />
                    <div style={{ flex: 1 }}>
                      <p style={{ color: textPrimary, fontSize: "12px", margin: "0 0 3px 0", lineHeight: "1.4" }}>{n.text}</p>
                      <span style={{ color: textSecondary, fontSize: "11px" }}>{n.time}</span>
                    </div>
                    <button
                      onClick={() => setDismissed((d) => [...d, n.id])}
                      style={{ background: "none", border: "none", cursor: "pointer", padding: "2px", borderRadius: "4px", flexShrink: 0 }}
                    >
                      <X size={12} color={textSecondary} />
                    </button>
                  </div>
                ))
              )}
              <div style={{ padding: "10px 16px", background: dropdownBg }}>
                <button
                  onClick={() => setDismissed(notifItems.map((n) => n.id))}
                  style={{ width: "100%", padding: "7px", border: `1.5px solid ${dropdownBorder}`, borderRadius: "7px", background: "transparent", color: textSecondary, fontSize: "12px", fontWeight: "600", cursor: "pointer" }}
                >
                  Mark all as read
                </button>
              </div>
            </div>
          )}
        </div>

        <div style={{ width: "1px", height: "28px", background: dividerColor }} />

        {/* Avatar with dropdown */}
        <div style={{ position: "relative" }} ref={userMenuRef}>
          <button
            onClick={() => setShowUserMenu((v) => !v)}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "10px",
              background: "transparent",
              border: "none",
              cursor: "pointer",
              padding: "4px",
              borderRadius: "8px",
              transition: "background 0.15s",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.background = isDark ? "#1A2D45" : "#F9FAFB")}
            onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
          >
            <div style={{ width: "38px", height: "38px", background: "linear-gradient(135deg, #185FA5, #2478C8)", borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
              <span style={{ color: "#FFFFFF", fontSize: "13px", fontWeight: "600" }}>JD</span>
            </div>
            <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-start" }}>
              <span style={{ color: textPrimary, fontSize: "13px", fontWeight: "600", lineHeight: "1.2" }}>Dr. Jane Davies</span>
              <span style={{ color: textSecondary, fontSize: "11px", lineHeight: "1.2" }}>Lecturer</span>
            </div>
            <ChevronDown size={16} color={textSecondary} style={{ transition: "transform 0.2s", transform: showUserMenu ? "rotate(180deg)" : "rotate(0deg)" }} />
          </button>

          {/* User dropdown menu */}
          {showUserMenu && (
            <div
              style={{
                position: "absolute",
                top: "calc(100% + 8px)",
                right: 0,
                width: "200px",
                background: dropdownBg,
                borderRadius: "12px",
                boxShadow: isDark ? "0 8px 32px rgba(0,0,0,0.45)" : "0 8px 32px rgba(0,0,0,0.14)",
                border: `1px solid ${dropdownBorder}`,
                overflow: "hidden",
                zIndex: 200,
              }}
            >
              <button
                onClick={handleSettings}
                style={{
                  width: "100%",
                  display: "flex",
                  alignItems: "center",
                  gap: "10px",
                  padding: "12px 16px",
                  background: "transparent",
                  border: "none",
                  cursor: "pointer",
                  textAlign: "left",
                  borderBottom: `1px solid ${dropdownBorder}`,
                  transition: "background 0.1s",
                }}
                onMouseEnter={(e) => (e.currentTarget.style.background = dropdownHover)}
                onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
              >
                <Settings size={16} color={textSecondary} />
                <span style={{ color: textPrimary, fontSize: "13px", fontWeight: "500" }}>Settings</span>
              </button>
              <button
                onClick={handleLogout}
                style={{
                  width: "100%",
                  display: "flex",
                  alignItems: "center",
                  gap: "10px",
                  padding: "12px 16px",
                  background: "transparent",
                  border: "none",
                  cursor: "pointer",
                  textAlign: "left",
                  transition: "background 0.1s",
                }}
                onMouseEnter={(e) => (e.currentTarget.style.background = isDark ? "#2A1A1A" : "#FEF2F2")}
                onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
              >
                <LogOut size={16} color="#E24B4A" />
                <span style={{ color: "#E24B4A", fontSize: "13px", fontWeight: "500" }}>Log out</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}