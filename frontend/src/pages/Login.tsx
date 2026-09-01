import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import {
  AlertTriangle,
  CheckCircle,
  ChevronRight,
  Eye,
  EyeOff,
  GraduationCap,
  Lock,
  Mail,
  RefreshCw,
  Shield,
} from "lucide-react";
import loginBg from "../assets/LBG.jpeg";
import combinedLogo from "../assets/CRr.png";
import facultyLogo from "../assets/edlogo.png";
import { login as loginRequest } from "../services/authService";
import { useAuth } from "../context/AuthContext";
import { getRedirectPath } from "../utils/getRedirectPath";

const LOADING_STEPS = [
  "Authenticating credentials…",
  "Loading risk model v1.0 (Rule engine + XGBoost) …",
  "Fetching student cohort data…",
  "Preparing dashboard…",
];

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPass, setShowPass] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [loadingStep, setLoadingStep] = useState(0);
  const [error, setError] = useState("");
  const [showForgot, setShowForgot] = useState(false);
  const [forgotEmail, setForgotEmail] = useState("");
  const [forgotSent, setForgotSent] = useState(false);
  const [showRequest, setShowRequest] = useState(false);
  const [requestName, setRequestName] = useState("");
  const [requestEmail, setRequestEmail] = useState("");
  const [requestRole, setRequestRole] = useState("");
  const [requestSent, setRequestSent] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  async function handleLogin(event?: FormEvent) {
    event?.preventDefault();

    if (!email || !password) {
      setError("Please enter your KOI email and password.");
      return;
    }

    setError("");

    try {
      const { access_token } = await loginRequest({ email, password });

      setIsLoading(true);
      for (let index = 0; index < LOADING_STEPS.length; index += 1) {
        setLoadingStep(index);
        await new Promise((resolve) => setTimeout(resolve, 550));
      }

      const loggedInUser = await login(access_token);
      navigate(getRedirectPath(loggedInUser));
    } catch {
      setError("Invalid email or password.");
      setIsLoading(false);
      setLoadingStep(0);
    }
  }

  function resetForgotModal() {
    setShowForgot(false);
    setForgotSent(false);
    setForgotEmail("");
  }

  function resetRequestModal() {
    setShowRequest(false);
    setRequestSent(false);
    setRequestName("");
    setRequestEmail("");
    setRequestRole("");
  }

  return (
    <div
      style={{
        minHeight: "100vh",
        fontFamily: "'Inter', -apple-system, sans-serif",
        position: "relative",
        overflow: "hidden",
      }}
    >
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&family=Instrument+Serif:ital@0;1&family=Playfair+Display:ital,wght@0,400;0,600;1,400;1,600&display=swap');

        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes fadeInUp { from { opacity: 0; } to { opacity: 1;  } }
        @keyframes fadeInRight { from { opacity: 0; transform: translateX(-20px); } to { opacity: 1; transform: translateX(0); } }
        @keyframes fadeInLeft { from { opacity: 0; transform: translateX(20px); } to { opacity: 1; transform: translateX(0); } }
        @keyframes float1 { 0%,100% { transform: translateY(0px) rotate(0deg); } 33% { transform: translateY(-10px) rotate(0.5deg); } 66% { transform: translateY(-5px) rotate(-0.5deg); } }
        @keyframes float2 { 0%,100% { transform: translateY(0px) rotate(0deg); } 50% { transform: translateY(-14px) rotate(-0.8deg); } }
        @keyframes float3 { 0%,100% { transform: translateY(0px); } 40% { transform: translateY(-8px); } 80% { transform: translateY(-12px); } }
        @keyframes orb1 { 0%,100% { transform: translate(0,0) scale(1); } 50% { transform: translate(40px,-30px) scale(1.08); } }
        @keyframes orb2 { 0%,100% { transform: translate(0,0) scale(1); } 50% { transform: translate(-30px,40px) scale(1.05); } }
        @keyframes orb3 { 0%,100% { transform: translate(0,0) scale(1); } 50% { transform: translate(20px,20px) scale(1.12); } }
        @keyframes stepFade { from { opacity: 0; transform: translateX(-6px); } to { opacity: 1; transform: translateX(0); } }
        @keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.5; } }
        @keyframes scanline { 0% { transform: translateY(-100%); } 100% { transform: translateY(100vh); } }
        @keyframes shimmer { 0% { background-position: -200% 0; } 100% { background-position: 200% 0; } }
        ::selection { background: #185FA5; color: #fff; }
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-thumb { background: #D1D5DB; border-radius: 3px; }
        .login-input:focus { border-color: #185FA5 !important; box-shadow: 0 0 0 3px rgba(24,95,165,0.12) !important; }
      `}</style>

      <img
        src={loginBg}
        alt=""
        aria-hidden="true"
        style={{
          position: "fixed",
          inset: 0,
          width: "100%",
          height: "100%",
          objectFit: "cover",
          objectPosition: "center 25%",
          filter: "saturate(0.5) brightness(0.75)",
          zIndex: 0,
        }}
      />

      <div
        style={{
          position: "fixed",
          inset: 0,
          background:
            "linear-gradient(150deg, rgba(4,16,40,0.96) 0%, rgba(7,27,59,0.88) 40%, rgba(10,40,80,0.82) 70%, rgba(7,27,59,0.94) 100%)",
          zIndex: 1,
        }}
      />

      <div
        style={{
          position: "fixed",
          inset: 0,
          background:
            "radial-gradient(ellipse 60% 60% at 50% 50%, rgba(24,95,165,0.18) 0%, transparent 70%)",
          zIndex: 2,
        }}
      />

      <div
        style={{
          position: "fixed",
          inset: 0,
          zIndex: 2,
          opacity: 0.25,
          backgroundImage:
            "radial-gradient(circle, rgba(255,255,255,0.35) 1px, transparent 1px)",
          backgroundSize: "32px 32px",
        }}
      />

      <div
        style={{
          position: "fixed",
          top: "8%",
          left: "12%",
          width: 500,
          height: 500,
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(24,95,165,0.22) 0%, transparent 70%)",
          zIndex: 2,
          filter: "blur(40px)",
          animation: "orb1 14s ease-in-out infinite",
          pointerEvents: "none",
        }}
      />
      <div
        style={{
          position: "fixed",
          bottom: "10%",
          right: "8%",
          width: 600,
          height: 600,
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(16,60,120,0.2) 0%, transparent 70%)",
          zIndex: 2,
          filter: "blur(50px)",
          animation: "orb2 18s ease-in-out infinite",
          pointerEvents: "none",
        }}
      />
      <div
        style={{
          position: "fixed",
          top: "40%",
          right: "20%",
          width: 360,
          height: 360,
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(226,75,74,0.1) 0%, transparent 70%)",
          zIndex: 2,
          filter: "blur(35px)",
          animation: "orb3 10s ease-in-out infinite",
          pointerEvents: "none",
        }}
      />

      <div
        style={{
          position: "relative",
          zIndex: 3,
          minHeight: "100vh",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          padding: "40px 24px",
        }}
      >
        <div
          style={{
            width: "100%",
            maxWidth: 440,
            animation: "fadeInUp 0.5s ease 0.1s both",
          }}
        >
          <div style={{ textAlign: "center", marginBottom: 50 }}>
            <div
              style={{
                width: "100%",
                margin: "0 auto 4px",
                filter: "drop-shadow(0 6px 20px rgba(0,0,0,0.5))",
                display: "flex",                
                justifyContent: "center",
              }}
            >
              <img
                src={combinedLogo}
                alt="EduGuard logo"
                style={{
                  width: "min(350px,90vw)",
                  height: "auto",
                  objectFit: "contain",
                  display: "block",
                }}
              />
            </div>            
          </div>

          <div
            style={{
              background: "rgba(255,255,255,0.97)",
              border: "1px solid rgba(255,255,255,0.18)",
              borderRadius: 22,
              boxShadow: "0 30px 80px rgba(3, 11, 25, 0.35)",
              overflow: "hidden",
              position: "relative",
            }}
          >
            {isLoading && (
              <div
                style={{
                  padding: "30px 28px 22px",
                  background: "linear-gradient(180deg, rgba(255,255,255,0.98), rgba(244,247,252,0.98))",
                  animation: "fadeInUp 0.2s ease",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    height: 76,
                    marginBottom: 18,
                  }}
                >
                  <div
                    style={{
                      width: 60,
                      height: 60,
                      borderRadius: "50%",
                      background:
                        "radial-gradient(circle at center, #EBF4FF 0%, #DDEFFF 35%, rgba(212,230,250,0.2) 100%)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      border: "1px solid rgba(24,95,165,0.14)",
                      boxShadow: "0 18px 38px rgba(24,95,165,0.14)",
                    }}
                  >
                    <RefreshCw
                      size={24}
                      color="#185FA5"
                      style={{ animation: "spin 0.8s linear infinite" }}
                    />
                  </div>
                </div>

                <div style={{ textAlign: "center" }}>
                  <div
                    style={{
                      color: "#0F172A",
                      fontSize: 18,
                      fontWeight: 700,
                      marginBottom: 6,
                    }}
                  >
                    Signing you in…
                  </div>
                  <div
                    style={{
                      color: "#6B7280",
                      fontSize: 13,
                      animation: "stepFade 0.3s ease",
                    }}
                  >
                    {LOADING_STEPS[loadingStep]}
                  </div>
                </div>
                <div
                  style={{
                    width: 260,
                    height: 3,
                    background: "#E5E7EB",
                    borderRadius: 2,
                    overflow: "hidden",
                    margin: "18px auto 12px",
                  }}
                >
                  <div
                    style={{
                      height: "100%",
                      background: "linear-gradient(90deg,#185FA5,#1A9BDC)",
                      borderRadius: 2,
                      width: `${((loadingStep + 1) / LOADING_STEPS.length) * 100}%`,
                      transition: "width 0.5s ease",
                    }}
                  />
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 7, marginTop: 2 }}>
                  {LOADING_STEPS.map((step, index) => (
                    <div
                      key={step}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 9,
                        opacity: index <= loadingStep ? 1 : 0.25,
                        transition: "opacity 0.3s ease",
                      }}
                    >
                      <CheckCircle
                        size={13}
                        color={
                          index < loadingStep
                            ? "#22C55E"
                            : index === loadingStep
                              ? "#185FA5"
                              : "#D1D5DB"
                        }
                      />
                      <span
                        style={{
                          color: index <= loadingStep ? "#374151" : "#9CA3AF",
                          fontSize: 12,
                        }}
                      >
                        {step}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {!isLoading && (
              <div style={{ padding: "28px 32px 0" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 20 }}>
                 
                  <div style={{ 
                     width: 60,
                     height: 68,
                     flexShrink: 0,                      
                     display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      overflow: "visible",

                     }}>
                    <img
                      src={facultyLogo}
                      alt="Faculty portal logo"
                      style={{
                        width: "100%",
                        height: "100%",
                        objectFit: "contain",
                        display: "block",
                        borderRadius: 18,
                        transform: "scale(5.5) translateY(3px)",
                        
                      }}
                    />

                  </div>
                  <div>
                    <div
                      style={{
                        fontFamily: "'JetBrains Mono',monospace",
                        fontSize: 9,
                        color: "#185FA5",
                        letterSpacing: "0.16em",
                        textTransform: "uppercase",
                        lineHeight: 1,
                        marginBottom: 5,
                      }}
                    >
                      ◆ Faculty Portal
                    </div>
                    <h2
                      style={{
                        fontFamily: "'Playfair Display', Georgia, serif",
                        color: "#0F172A",
                        fontSize: 28,
                        fontWeight: 600,
                        margin: 0,
                        lineHeight: 1.2,
                      }}
                    >
                      Sign in to{" "}
                      <span
                        style={{
                          fontWeight: 600,
                          background: "linear-gradient(90deg, #155392 0%, #1e9943 100%)",
                          WebkitBackgroundClip: "text",
                          WebkitTextFillColor: "transparent",
                          backgroundClip: "text",
                        }}
                      >
                        EdGuard
                      </span>
                    </h2>
                  </div>
                </div>

                <p
                  style={{
                    fontFamily: "'Playfair Display', Georgia, serif",
                    fontStyle: "normal",
                    color: "#8A96A4",
                    fontSize: 14,
                    fontWeight: 400,
                    margin: "-10px 0 15px",
                    lineHeight: 1.65,
                    letterSpacing: "0.01em",
                  }}
                >
                  Use your KOI lecturer credentials to access the risk dashboard.
                </p>

                

                <form onSubmit={handleLogin} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                  <div>
                    <label
                      htmlFor="email"
                      style={{
                        display: "block",
                        color: "#374151",
                        fontSize: 11,
                        fontWeight: 700,
                        marginBottom: 6,
                        letterSpacing: "0.04em",
                        textTransform: "uppercase",
                      }}
                    >
                      KOI Email Address
                    </label>
                    <div style={{ position: "relative" }}>
                      <Mail
                        size={14}
                        color="#9CA3AF"
                        style={{
                          position: "absolute",
                          left: 13,
                          top: "50%",
                          transform: "translateY(-50%)",
                          pointerEvents: "none",
                        }}
                      />
                      <input
                        id="email"
                        className="login-input"
                        type="email"
                        value={email}
                        onChange={(event) => setEmail(event.target.value)}
                        placeholder="lecturer@koi.edu.au"
                        style={{
                          width: "100%",
                          padding: "11px 13px 11px 38px",
                          border: "1.5px solid #E5E7EB",
                          borderRadius: 10,
                          fontSize: 13.5,
                          color: "#1A1A2E",
                          outline: "none",
                          boxSizing: "border-box",
                          background: "#FAFBFD",
                          transition: "border-color 0.15s, box-shadow 0.15s",
                          fontFamily: "inherit",
                        }}
                      />
                    </div>
                  </div>

                  <div>
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        marginBottom: 6,
                      }}
                    >
                      <label
                        htmlFor="password"
                        style={{
                          color: "#374151",
                          fontSize: 11,
                          fontWeight: 700,
                          letterSpacing: "0.04em",
                          textTransform: "uppercase",
                        }}
                      >
                        Password
                      </label>
                      <button
                        type="button"
                        onClick={() => setShowForgot(true)}
                        style={{
                          background: "none",
                          border: "none",
                          cursor: "pointer",
                          padding: 0,
                          color: "#185FA5",
                          fontSize: 11.5,
                          fontWeight: 600,
                          letterSpacing: "0.01em",
                        }}
                        onMouseEnter={(event) => {
                          event.currentTarget.style.textDecoration = "underline";
                        }}
                        onMouseLeave={(event) => {
                          event.currentTarget.style.textDecoration = "none";
                        }}
                      >
                        Forgot password?
                      </button>
                    </div>
                    <div style={{ position: "relative" }}>
                      <Lock
                        size={14}
                        color="#9CA3AF"
                        style={{
                          position: "absolute",
                          left: 13,
                          top: "50%",
                          transform: "translateY(-50%)",
                          pointerEvents: "none",
                        }}
                      />
                      <input
                        id="password"
                        className="login-input"
                        type={showPass ? "text" : "password"}
                        value={password}
                        onChange={(event) => setPassword(event.target.value)}
                        placeholder="Enter your password"
                        style={{
                          width: "100%",
                          padding: "11px 40px 11px 38px",
                          border: "1.5px solid #E5E7EB",
                          borderRadius: 10,
                          fontSize: 13.5,
                          color: "#1A1A2E",
                          outline: "none",
                          boxSizing: "border-box",
                          background: "#FAFBFD",
                          transition: "border-color 0.15s, box-shadow 0.15s",
                          fontFamily: "inherit",
                        }}
                      />
                      <button
                        type="button"
                        onClick={() => setShowPass((current) => !current)}
                        style={{
                          position: "absolute",
                          right: 12,
                          top: "50%",
                          transform: "translateY(-50%)",
                          background: "none",
                          border: "none",
                          cursor: "pointer",
                          padding: 3,
                          borderRadius: 5,
                        }}
                      >
                        {showPass ? (
                          <EyeOff size={14} color="#9CA3AF" />
                        ) : (
                          <Eye size={14} color="#9CA3AF" />
                        )}
                      </button>
                    </div>
                  </div>

                  {error && (
                    <div
                      style={{
                        display: "flex",
                        alignItems: "flex-start",
                        gap: 9,
                        padding: "10px 13px",
                        background: "#FEF2F2",
                        border: "1px solid #FCA5A5",
                        borderRadius: 9,
                        color: "#DC2626",
                        fontSize: 12.5,
                      }}
                    >
                      <AlertTriangle
                        size={13}
                        color="#DC2626"
                        style={{ flexShrink: 0, marginTop: 1 }}
                      />
                      {error}
                    </div>
                  )}

                  <button
                    type="submit"
                    disabled={isLoading}
                    style={{
                      marginTop: 6,
                      padding: "13px",
                      background: isLoading
                        ? "#9CA3AF"
                        : "linear-gradient(135deg,#0B3D73 0%,#185FA5 50%,#1A7ABF 100%)",
                      border: "none",
                      borderRadius: 11,
                      color: "#FFFFFF",
                      fontSize: 14,
                      fontWeight: 700,
                      cursor: isLoading ? "default" : "pointer",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      gap: 8,
                      boxShadow: isLoading
                        ? "none"
                        : "0 6px 20px rgba(24,95,165,0.4), 0 2px 6px rgba(0,0,0,0.15)",
                      transition: "all 0.2s",
                      letterSpacing: "0.01em",
                    }}
                    onMouseEnter={(event) => {
                      if (!isLoading) {
                        const target = event.currentTarget;
                        target.style.transform = "translateY(-1px)";
                        target.style.boxShadow =
                          "0 10px 28px rgba(24,95,165,0.5), 0 3px 8px rgba(0,0,0,0.15)";
                      }
                    }}
                    onMouseLeave={(event) => {
                      const target = event.currentTarget;
                      target.style.transform = "translateY(0)";
                      target.style.boxShadow =
                        "0 6px 20px rgba(24,95,165,0.4), 0 2px 6px rgba(0,0,0,0.15)";
                    }}
                  >
                    {isLoading && (
                      <RefreshCw size={15} style={{ animation: "spin 0.8s linear infinite" }} />
                    )}
                    {isLoading ? "Signing in…" : "Sign in to EdGuard"}
                    {!isLoading && <ChevronRight size={15} />}
                  </button>
                </form>
              </div>
            )}

            <div
              style={{
                padding: "14px 36px 18px",
                borderTop: "1px solid #F3F4F6",
                background: "#F8F9FB",
              }}
            >
              <p style={{ textAlign: "center", color: "#6B7280", fontSize: 12.5, margin: "0 0 10px 0" }}>
                {"Don't have access? "}
                <button
                  type="button"
                  onClick={() => setShowRequest(true)}
                  style={{
                    background: "none",
                    border: "none",
                    cursor: "pointer",
                    padding: 0,
                    color: "#185FA5",
                    fontSize: 12.5,
                    fontWeight: 700,
                  }}
                  onMouseEnter={(event) => {
                    event.currentTarget.style.textDecoration = "underline";
                  }}
                  onMouseLeave={(event) => {
                    event.currentTarget.style.textDecoration = "none";
                  }}
                >
                  Request an account
                </button>
              </p>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 6 }}>
                <Shield size={11} color="#C0CAD6" />
                <span style={{ color: "#B0BBC8", fontSize: 10.5, lineHeight: 1.4 }}>
                  Authorised KOI academic staff only.
                </span>
              </div>
            </div>
          </div>

          <div
            style={{
              textAlign: "center",
              marginTop: 22,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 7,
            }}
          >
            <GraduationCap size={18} color="rgba(236, 229, 229, 0.91)" />

            <div
              style={{
                fontFamily: "'JetBrains Mono',monospace",
                fontSize: 12,
                color: "rgba(255, 255, 255, 0.93)",
                letterSpacing: "0.18em",
                textTransform: "uppercase",
              }}
            >
              King's Own Institute · Sydney, Australia
            </div>
          </div>
        </div>
      </div>





      {showForgot && (
        <>
          <div
            onClick={resetForgotModal}
            style={{
              position: "fixed",
              inset: 0,
              background: "rgba(4,16,40,0.6)",
              zIndex: 200,
              backdropFilter: "blur(4px)",
            }}
          />
          <div
            style={{
              position: "fixed",
              top: "50%",
              left: "50%",
              transform: "translate(-50%,-50%)",
              width: 390,
              maxWidth: "calc(100vw - 32px)",
              background: "#FFFFFF",
              borderRadius: 18,
              boxShadow: "0 32px 80px rgba(0,0,0,0.25)",
              zIndex: 201,
              overflow: "hidden",
              animation: "fadeInUp 0.5s ease",
            }}
          >
            <div
              style={{
                height: 3,
                background: "linear-gradient(90deg, #071B3B, #185FA5, #1A9BDC)",
              }}
            />
            <div style={{ padding: "28px 28px 24px" }}>
              {forgotSent ? (
                <div style={{ textAlign: "center", padding: "8px 0" }}>
                  <div
                    style={{
                      width: 52,
                      height: 52,
                      borderRadius: "50%",
                      background: "#ECFDF5",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      margin: "0 auto 16px",
                    }}
                  >
                    <CheckCircle size={26} color="#16A34A" />
                  </div>
                  <h3 style={{ color: "#1A1A2E", fontSize: 17, fontWeight: 700, margin: "0 0 8px" }}>
                    Check your inbox
                  </h3>
                  <p style={{ color: "#6B7280", fontSize: 13, lineHeight: 1.6, margin: "0 0 20px" }}>
                    If <strong>{forgotEmail}</strong> is registered, a reset link has been sent by the KOI IT team within 1 business day.
                  </p>
                  <button
                    onClick={resetForgotModal}
                    style={{
                      width: "100%",
                      padding: "12px",
                      background: "linear-gradient(135deg,#0B3D73,#185FA5)",
                      border: "none",
                      borderRadius: 10,
                      color: "#FFFFFF",
                      fontSize: 14,
                      fontWeight: 700,
                      cursor: "pointer",
                    }}
                  >
                    Back to sign in
                  </button>
                </div>
              ) : (
                <>
                  <h3 style={{ color: "#1A1A2E", fontSize: 17, fontWeight: 700, margin: "0 0 6px" }}>
                    Reset your password
                  </h3>
                  <p style={{ color: "#6B7280", fontSize: 13, lineHeight: 1.5, margin: "0 0 20px" }}>
                    Enter your KOI email and we'll send reset instructions.
                  </p>
                  <label
                    style={{
                      display: "block",
                      color: "#374151",
                      fontSize: 11,
                      fontWeight: 700,
                      letterSpacing: "0.04em",
                      textTransform: "uppercase",
                      marginBottom: 6,
                    }}
                  >
                    KOI Email Address
                  </label>
                  <div style={{ position: "relative", marginBottom: 16 }}>
                    <Mail
                      size={14}
                      color="#9CA3AF"
                      style={{
                        position: "absolute",
                        left: 12,
                        top: "50%",
                        transform: "translateY(-50%)",
                        pointerEvents: "none",
                      }}
                    />
                    <input
                      className="login-input"
                      type="email"
                      value={forgotEmail}
                      onChange={(event) => setForgotEmail(event.target.value)}
                      placeholder="lecturer@koi.edu.au"
                      style={{
                        width: "100%",
                        padding: "11px 12px 11px 36px",
                        border: "1.5px solid #E5E7EB",
                        borderRadius: 10,
                        fontSize: 14,
                        color: "#1A1A2E",
                        outline: "none",
                        boxSizing: "border-box",
                        fontFamily: "inherit",
                      }}
                    />
                  </div>
                  <div style={{ display: "flex", gap: 10 }}>
                    <button
                      onClick={resetForgotModal}
                      style={{
                        flex: 1,
                        padding: "11px",
                        background: "transparent",
                        border: "1.5px solid #E5E7EB",
                        borderRadius: 10,
                        color: "#6B7280",
                        fontSize: 13,
                        fontWeight: 600,
                        cursor: "pointer",
                      }}
                    >
                      Cancel
                    </button>
                    <button
                      onClick={() => {
                        if (forgotEmail) setForgotSent(true);
                      }}
                      disabled={!forgotEmail}
                      style={{
                        flex: 2,
                        padding: "11px",
                        background: forgotEmail
                          ? "linear-gradient(135deg,#0B3D73,#185FA5)"
                          : "#E5E7EB",
                        border: "none",
                        borderRadius: 10,
                        color: forgotEmail ? "#FFFFFF" : "#9CA3AF",
                        fontSize: 13,
                        fontWeight: 700,
                        cursor: forgotEmail ? "pointer" : "not-allowed",
                      }}
                    >
                      Send reset link
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </>
      )}





      {showRequest && (
        <>
          <div
            onClick={resetRequestModal}
            style={{
              position: "fixed",
              inset: 0,
              background: "rgba(4,16,40,0.6)",
              zIndex: 200,
              backdropFilter: "blur(4px)",
            }}
          />
          <div
            style={{
              position: "fixed",
              top: "50%",
              left: "50%",
              transform: "translate(-50%,-50%)",
              width: 430,
              maxWidth: "calc(100vw - 32px)",
              background: "#FFFFFF",
              borderRadius: 18,
              boxShadow: "0 32px 80px rgba(0,0,0,0.25)",
              zIndex: 201,
              overflow: "hidden",
              animation: "fadeInUp 0.2s ease",
            }}
          >
            <div
              style={{
                height: 3,
                background: "linear-gradient(90deg, #071B3B, #185FA5, #1A9BDC)",
              }}
            />
            <div style={{ padding: "28px 28px 24px" }}>
              {requestSent ? (
                <div style={{ textAlign: "center", padding: "8px 0" }}>
                  <div
                    style={{
                      width: 52,
                      height: 52,
                      borderRadius: "50%",
                      background: "#EBF4FF",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      margin: "0 auto 16px",
                    }}
                  >
                    <CheckCircle size={26} color="#185FA5" />
                  </div>
                  <h3 style={{ color: "#1A1A2E", fontSize: 17, fontWeight: 700, margin: "0 0 8px" }}>
                    Request submitted
                  </h3>
                  <p style={{ color: "#6B7280", fontSize: 13, lineHeight: 1.6, margin: "0 0 20px" }}>
                    Your request has been sent to the KOI IT Help Desk. You'll receive credentials via email within 1–2 business days.
                  </p>
                  <button
                    onClick={resetRequestModal}
                    style={{
                      width: "100%",
                      padding: "12px",
                      background: "linear-gradient(135deg,#0B3D73,#185FA5)",
                      border: "none",
                      borderRadius: 10,
                      color: "#FFFFFF",
                      fontSize: 14,
                      fontWeight: 700,
                      cursor: "pointer",
                    }}
                  >
                    Back to sign in
                  </button>
                </div>
              ) : (
                <>
                  <h3 style={{ color: "#1A1A2E", fontSize: 17, fontWeight: 700, margin: "0 0 6px" }}>
                    Request EdGuard access
                  </h3>
                  <p style={{ color: "#6B7280", fontSize: 13, lineHeight: 1.5, margin: "0 0 20px" }}>
                    Fill in your details and the KOI IT team will provision your account.
                  </p>
                  <div style={{ display: "flex", flexDirection: "column", gap: 14, marginBottom: 20 }}>
                    <div>
                      <label
                        style={{
                          display: "block",
                          color: "#374151",
                          fontSize: 11,
                          fontWeight: 700,
                          letterSpacing: "0.04em",
                          textTransform: "uppercase",
                          marginBottom: 6,
                        }}
                      >
                        Full Name
                      </label>
                      <input
                        className="login-input"
                        type="text"
                        value={requestName}
                        onChange={(event) => setRequestName(event.target.value)}
                        placeholder="Dr. Jane Davies"
                        style={{
                          width: "100%",
                          padding: "11px 12px",
                          border: "1.5px solid #E5E7EB",
                          borderRadius: 10,
                          fontSize: 14,
                          color: "#1A1A2E",
                          outline: "none",
                          boxSizing: "border-box",
                          fontFamily: "inherit",
                        }}
                      />
                    </div>
                    <div>
                      <label
                        style={{
                          display: "block",
                          color: "#374151",
                          fontSize: 11,
                          fontWeight: 700,
                          letterSpacing: "0.04em",
                          textTransform: "uppercase",
                          marginBottom: 6,
                        }}
                      >
                        KOI Email Address
                      </label>
                      <div style={{ position: "relative" }}>
                        <Mail
                          size={14}
                          color="#9CA3AF"
                          style={{
                            position: "absolute",
                            left: 12,
                            top: "50%",
                            transform: "translateY(-50%)",
                            pointerEvents: "none",
                          }}
                        />
                        <input
                          className="login-input"
                          type="email"
                          value={requestEmail}
                          onChange={(event) => setRequestEmail(event.target.value)}
                          placeholder="lecturer@koi.edu.au"
                          style={{
                            width: "100%",
                            padding: "11px 12px 11px 36px",
                            border: "1.5px solid #E5E7EB",
                            borderRadius: 10,
                            fontSize: 14,
                            color: "#1A1A2E",
                            outline: "none",
                            boxSizing: "border-box",
                            fontFamily: "inherit",
                          }}
                        />
                      </div>
                    </div>
                    <div>
                      <label
                        style={{
                          display: "block",
                          color: "#374151",
                          fontSize: 11,
                          fontWeight: 700,
                          letterSpacing: "0.04em",
                          textTransform: "uppercase",
                          marginBottom: 6,
                        }}
                      >
                        Role / Position
                      </label>
                      <select
                        className="login-input"
                        value={requestRole}
                        onChange={(event) => setRequestRole(event.target.value)}
                        style={{
                          width: "100%",
                          padding: "11px 12px",
                          border: "1.5px solid #E5E7EB",
                          borderRadius: 10,
                          fontSize: 14,
                          color: requestRole ? "#1A1A2E" : "#9CA3AF",
                          outline: "none",
                          boxSizing: "border-box",
                          background: "#FFFFFF",
                          cursor: "pointer",
                          appearance: "none",
                          WebkitAppearance: "none",
                          backgroundImage:
                            "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%239CA3AF' stroke-width='2'%3E%3Cpolyline points='6 9 12 15 18 9'%3E%3C/polyline%3E%3C/svg%3E\")",
                          backgroundRepeat: "no-repeat",
                          backgroundPosition: "right 12px center",
                          fontFamily: "inherit",
                        }}
                      >
                        <option value="" disabled>
                          Select your role…
                        </option>
                        <option value="Lecturer">Lecturer</option>
                        <option value="Course Coordinator">Course Coordinator</option>
                        <option value="Academic Support">Academic Support</option>
                        <option value="Department Head">Department Head</option>
                        <option value="Other">Other</option>
                      </select>
                    </div>
                  </div>
                  <div style={{ display: "flex", gap: 10 }}>
                    <button
                      onClick={resetRequestModal}
                      style={{
                        flex: 1,
                        padding: "11px",
                        background: "transparent",
                        border: "1.5px solid #E5E7EB",
                        borderRadius: 10,
                        color: "#6B7280",
                        fontSize: 13,
                        fontWeight: 600,
                        cursor: "pointer",
                      }}
                    >
                      Cancel
                    </button>
                    <button
                      onClick={() => {
                        if (requestName && requestEmail && requestRole) setRequestSent(true);
                      }}
                      disabled={!requestName || !requestEmail || !requestRole}
                      style={{
                        flex: 2,
                        padding: "11px",
                        background:
                          requestName && requestEmail && requestRole
                            ? "linear-gradient(135deg,#0B3D73,#185FA5)"
                            : "#E5E7EB",
                        border: "none",
                        borderRadius: 10,
                        color:
                          requestName && requestEmail && requestRole ? "#FFFFFF" : "#9CA3AF",
                        fontSize: 13,
                        fontWeight: 700,
                        cursor:
                          requestName && requestEmail && requestRole ? "pointer" : "not-allowed",
                      }}
                    >
                      Submit request
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
