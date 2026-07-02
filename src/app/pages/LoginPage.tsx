import { useState } from "react";
import { useNavigate } from "react-router";
import { Eye, EyeOff, Brain, Shield, GraduationCap, Mail, Lock, ChevronRight, CheckCircle, Cpu, RefreshCw } from "lucide-react";

const DEMO_CREDENTIALS = [
  { name: "Dr. Jane Davies", role: "Lecturer — BSYS301 / INFO101", email: "j.davies@koi.edu.au", initials: "JD", color: "#185FA5" },
  { name: "Prof. Marcus Webb", role: "Course Coordinator — All Units", email: "m.webb@koi.edu.au", initials: "MW", color: "#7C3AED" },
  { name: "Dr. Anika Singh", role: "Lecturer — BSYS201 / BSYS401", email: "a.singh@koi.edu.au", initials: "AS", color: "#0891B2" },
];

const SYSTEM_FEATURES = [
  { icon: <Brain size={15} color="#60A5FA" />, label: "Learning Model + Rule-Based ML Engine", desc: "Hybrid detection · F1-score 0.74" },
  { icon: <Shield size={15} color="#34D399" />, label: "SHAP Explainability (XAI)", desc: "Transparent risk reasoning per student" },
  { icon: <Cpu size={15} color="#FBBF24" />, label: "Automated SMTP Alerts", desc: "Real-time email notifications via Python" },
];

export default function LoginPage() {
  const [email, setEmail] = useState("j.davies@koi.edu.au");
  const [password, setPassword] = useState("KOI-EdGuard-2026");
  const [showPass, setShowPass] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [loadingStep, setLoadingStep] = useState(0);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const LOADING_STEPS = [
    "Authenticating credentials…",
    "Loading risk model (Learning Model v2.3.1)…",
    "Syncing student data from Moodle…",
    "Preparing dashboard…",
  ];

  const handleLogin = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!email || !password) { setError("Please enter your KOI email and password."); return; }
    setError("");
    setIsLoading(true);
    for (let i = 0; i < LOADING_STEPS.length; i++) {
      setLoadingStep(i);
      await new Promise(r => setTimeout(r, 550));
    }
    localStorage.setItem("edguard_auth", "true");
    localStorage.setItem("edguard_user", email);
    navigate("/");
  };

  const handleDemoLogin = async (demoEmail: string) => {
    setEmail(demoEmail);
    setPassword("KOI-EdGuard-2026");
    setError("");
    setIsLoading(true);
    for (let i = 0; i < LOADING_STEPS.length; i++) {
      setLoadingStep(i);
      await new Promise(r => setTimeout(r, 480));
    }
    localStorage.setItem("edguard_auth", "true");
    localStorage.setItem("edguard_user", demoEmail);
    navigate("/");
  };

  return (
    <div style={{
      minHeight: "100vh", display: "flex",
      fontFamily: "'Inter', -apple-system, sans-serif",
      background: "#F6F5F1",
    }}>
      <style>{`
        @keyframes pulse { 0%,100%{opacity:1;transform:scale(1)}50%{opacity:0.5;transform:scale(1.15)} }
        @keyframes spin { to{transform:rotate(360deg)} }
        @keyframes fadeInUp { from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:translateY(0)} }
        @keyframes float { 0%,100%{transform:translateY(0)}50%{transform:translateY(-5px)} }
        @keyframes loginOrb1 { 0%,100%{transform:translate(0,0)}33%{transform:translate(30px,-20px)}66%{transform:translate(-20px,15px)} }
        @keyframes loginOrb2 { 0%,100%{transform:translate(0,0)}33%{transform:translate(-25px,20px)}66%{transform:translate(20px,-15px)} }
        @keyframes progressBar { from{width:0%}to{width:100%} }
        @keyframes stepFade { from{opacity:0;transform:translateX(-6px)}to{opacity:1;transform:translateX(0)} }
        * { box-sizing: border-box; }
        body { margin: 0; }
        ::selection { background:#185FA5;color:#fff }
        ::-webkit-scrollbar{width:6px}
        ::-webkit-scrollbar-thumb{background:#D1D5DB;border-radius:3px}
      `}</style>

      {/* ── LEFT PANEL ── */}
      <div style={{
        width: "52%", minHeight: "100vh",
        background: "linear-gradient(160deg, #071B3B 0%, #0D3567 40%, #185FA5 75%, #1C7FCA 100%)",
        position: "relative", overflow: "hidden",
        display: "flex", flexDirection: "column", justifyContent: "space-between",
        padding: "48px 52px",
      }}>
        {/* Ambient orbs */}
        <div style={{ position:"absolute",inset:0,overflow:"hidden",pointerEvents:"none" }}>
          <div style={{ position:"absolute",width:480,height:480,borderRadius:"50%",background:"radial-gradient(closest-side,rgba(46,143,212,0.18),transparent)",top:-80,left:-120,animation:"loginOrb1 14s ease-in-out infinite" }} />
          <div style={{ position:"absolute",width:360,height:360,borderRadius:"50%",background:"radial-gradient(closest-side,rgba(239,159,39,0.12),transparent)",bottom:-60,right:-80,animation:"loginOrb2 18s ease-in-out infinite" }} />
          <div style={{ position:"absolute",width:200,height:200,borderRadius:"50%",background:"radial-gradient(closest-side,rgba(255,255,255,0.04),transparent)",top:"45%",right:"12%" }} />
          {/* grid pattern */}
          <svg style={{ position:"absolute",inset:0,width:"100%",height:"100%",opacity:0.04 }} xmlns="http://www.w3.org/2000/svg">
            <defs><pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M40 0L0 0 0 40" fill="none" stroke="#fff" strokeWidth="0.5"/></pattern></defs>
            <rect width="100%" height="100%" fill="url(#grid)" />
          </svg>
        </div>

        {/* Brand header */}
        <div style={{ position:"relative", zIndex:1, animation:"fadeInUp 0.5s ease" }}>
          <div style={{ display:"flex", alignItems:"center", gap:14, marginBottom:40 }}>
            <div style={{ width:46,height:46,background:"rgba(255,255,255,0.12)",backdropFilter:"blur(8px)",borderRadius:12,border:"1px solid rgba(255,255,255,0.18)",display:"flex",alignItems:"center",justifyContent:"center",boxShadow:"0 8px 24px rgba(0,0,0,0.2)" }}>
              <svg width="26" height="26" viewBox="0 0 24 24" fill="none">
                <path d="M12 2 L21 6 V12 C21 17 17 21 12 22 C7 21 3 17 3 12 V6 Z" stroke="#FFFFFF" strokeWidth="1.6" strokeLinejoin="round" fill="rgba(255,255,255,0.1)"/>
                <path d="M8.5 12.2 L11 14.7 L15.8 9.8" stroke="#FFFFFF" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
            <div>
              <div style={{ fontSize:26, fontWeight:700, color:"#FFFFFF", letterSpacing:"-0.03em" }}>
                Ed<span style={{ fontFamily:"'Instrument Serif',serif", fontStyle:"italic", fontWeight:400 }}>Guard</span>
              </div>
              <div style={{ fontFamily:"'JetBrains Mono',monospace", fontSize:9, color:"rgba(255,255,255,0.5)", letterSpacing:"0.14em", textTransform:"uppercase", marginTop:2 }}>
                KOI · Sydney · v2.4
              </div>
            </div>
          </div>

          <div style={{ maxWidth:380 }}>
            <div style={{ fontFamily:"'JetBrains Mono',monospace", fontSize:10, color:"rgba(255,255,255,0.4)", letterSpacing:"0.18em", textTransform:"uppercase", marginBottom:14 }}>
              ◆ Student Risk Detection System
            </div>
            <h1 style={{ color:"#FFFFFF", fontSize:42, fontWeight:800, lineHeight:1.06, letterSpacing:"-0.04em", margin:"0 0 8px 0" }}>
              Early Detection.<br/>
              <span style={{ fontFamily:"'Instrument Serif',serif", fontStyle:"italic", fontWeight:400, color:"rgba(255,255,255,0.75)" }}>
                Timely Action.
              </span>
            </h1>
            <h2 style={{ color:"rgba(255,255,255,0.5)", fontSize:26, fontWeight:300, margin:"0 0 28px 0", letterSpacing:"-0.02em" }}>
              Better Outcomes.
            </h2>
            <p style={{ color:"rgba(255,255,255,0.55)", fontSize:14, lineHeight:1.7, margin:0 }}>
              A hybrid ML-powered risk detection dashboard for KOI lecturers — identify at-risk students early and take timely intervention action.
            </p>
          </div>
        </div>

        {/* Feature list */}
        <div style={{ position:"relative", zIndex:1, animation:"fadeInUp 0.6s ease 0.1s both" }}>
          <div style={{ display:"flex", flexDirection:"column", gap:14 }}>
            {SYSTEM_FEATURES.map((f, i) => (
              <div key={i} style={{ display:"flex", alignItems:"flex-start", gap:12 }}>
                <div style={{ width:32,height:32,borderRadius:8,background:"rgba(255,255,255,0.08)",border:"1px solid rgba(255,255,255,0.1)",display:"flex",alignItems:"center",justifyContent:"center",flexShrink:0 }}>
                  {f.icon}
                </div>
                <div>
                  <div style={{ color:"rgba(255,255,255,0.85)", fontSize:13, fontWeight:600 }}>{f.label}</div>
                  <div style={{ color:"rgba(255,255,255,0.4)", fontSize:11, marginTop:1 }}>{f.desc}</div>
                </div>
              </div>
            ))}
          </div>

          {/* Bottom: KOI info */}
          <div style={{ marginTop:32, paddingTop:24, borderTop:"1px solid rgba(255,255,255,0.1)" }}>
            <div style={{ display:"flex", alignItems:"center", gap:10 }}>
              <GraduationCap size={15} color="rgba(255,255,255,0.35)" />
              <span style={{ color:"rgba(255,255,255,0.35)", fontSize:12 }}>King's Own Institute · Sydney, Australia</span>
            </div>
          </div>
        </div>
      </div>

      {/* ── RIGHT PANEL ── */}
      <div style={{
        flex:1, display:"flex", alignItems:"center", justifyContent:"center",
        padding:"40px 56px", position:"relative",
      }}>
        {/* Subtle background accent */}
        <div style={{ position:"absolute",top:-100,right:-100,width:400,height:400,borderRadius:"50%",background:"radial-gradient(closest-side,rgba(24,95,165,0.05),transparent)",pointerEvents:"none" }} />

        <div style={{ width:"100%", maxWidth:400, animation:"fadeInUp 0.45s ease 0.05s both" }}>

          {/* Loading overlay */}
          {isLoading && (
            <div style={{ position:"fixed",inset:0,background:"rgba(255,255,255,0.92)",backdropFilter:"blur(6px)",zIndex:999,display:"flex",flexDirection:"column",alignItems:"center",justifyContent:"center",gap:24 }}>
              <div style={{ width:56,height:56,borderRadius:16,background:"linear-gradient(140deg,#0B3D73,#185FA5)",display:"flex",alignItems:"center",justifyContent:"center",boxShadow:"0 12px 32px rgba(24,95,165,0.35)",animation:"float 2s ease-in-out infinite" }}>
                <svg width="30" height="30" viewBox="0 0 24 24" fill="none">
                  <path d="M12 2 L21 6 V12 C21 17 17 21 12 22 C7 21 3 17 3 12 V6 Z" stroke="#fff" strokeWidth="1.6" strokeLinejoin="round" fill="rgba(255,255,255,0.1)"/>
                  <path d="M8.5 12.2 L11 14.7 L15.8 9.8" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </div>
              <div style={{ textAlign:"center" }}>
                <div style={{ color:"#0F172A", fontSize:18, fontWeight:700, marginBottom:6 }}>Signing you in…</div>
                <div style={{ color:"#6B7280", fontSize:13, animation:"stepFade 0.3s ease", key:loadingStep }}>{LOADING_STEPS[loadingStep]}</div>
              </div>
              <div style={{ width:240, height:3, background:"#E5E7EB", borderRadius:2, overflow:"hidden" }}>
                <div style={{ height:"100%", background:"linear-gradient(90deg,#185FA5,#1A7ABF)", borderRadius:2, width:`${((loadingStep+1)/LOADING_STEPS.length)*100}%`, transition:"width 0.5s ease" }} />
              </div>
              <div style={{ display:"flex", flexDirection:"column", gap:6, marginTop:4 }}>
                {LOADING_STEPS.map((step, i) => (
                  <div key={i} style={{ display:"flex", alignItems:"center", gap:8, opacity:i <= loadingStep ? 1 : 0.25, transition:"opacity 0.3s ease" }}>
                    <CheckCircle size={13} color={i < loadingStep ? "#22C55E" : i === loadingStep ? "#185FA5" : "#D1D5DB"} />
                    <span style={{ color: i <= loadingStep ? "#374151" : "#9CA3AF", fontSize:12 }}>{step}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Header */}
          <div style={{ marginBottom:32 }}>
            <div style={{ fontFamily:"'JetBrains Mono',monospace", fontSize:10, color:"#185FA5", letterSpacing:"0.16em", textTransform:"uppercase", marginBottom:10 }}>
              ◆ Faculty Portal
            </div>
            <h2 style={{ color:"#0F172A", fontSize:28, fontWeight:800, letterSpacing:"-0.03em", margin:"0 0 6px" }}>
              Sign in to Ed<span style={{ fontFamily:"'Instrument Serif',serif", fontStyle:"italic", fontWeight:400, color:"#185FA5" }}>Guard</span>
            </h2>
            <p style={{ color:"#6B7280", fontSize:14, margin:0 }}>Use your KOI lecturer credentials to access the dashboard.</p>
          </div>

          {/* Form */}
          <form onSubmit={handleLogin} style={{ display:"flex", flexDirection:"column", gap:16 }}>
            {/* Email */}
            <div>
              <label style={{ display:"block", color:"#374151", fontSize:12, fontWeight:600, marginBottom:6 }}>KOI Email Address</label>
              <div style={{ position:"relative" }}>
                <Mail size={15} color="#9CA3AF" style={{ position:"absolute", left:13, top:"50%", transform:"translateY(-50%)", pointerEvents:"none" }} />
                <input
                  type="email" value={email} onChange={e => setEmail(e.target.value)}
                  placeholder="lecturer@koi.edu.au"
                  style={{ width:"100%", padding:"11px 13px 11px 38px", border:"1.5px solid #E5E7EB", borderRadius:10, fontSize:14, color:"#1A1A2E", outline:"none", boxSizing:"border-box", background:"#FFFFFF", transition:"border-color 0.15s" }}
                  onFocus={e => (e.target.style.borderColor = "#185FA5")}
                  onBlur={e => (e.target.style.borderColor = "#E5E7EB")}
                />
              </div>
            </div>

            {/* Password */}
            <div>
              <label style={{ display:"block", color:"#374151", fontSize:12, fontWeight:600, marginBottom:6 }}>Password</label>
              <div style={{ position:"relative" }}>
                <Lock size={15} color="#9CA3AF" style={{ position:"absolute", left:13, top:"50%", transform:"translateY(-50%)", pointerEvents:"none" }} />
                <input
                  type={showPass ? "text" : "password"} value={password} onChange={e => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  style={{ width:"100%", padding:"11px 40px 11px 38px", border:"1.5px solid #E5E7EB", borderRadius:10, fontSize:14, color:"#1A1A2E", outline:"none", boxSizing:"border-box", background:"#FFFFFF", transition:"border-color 0.15s" }}
                  onFocus={e => (e.target.style.borderColor = "#185FA5")}
                  onBlur={e => (e.target.style.borderColor = "#E5E7EB")}
                />
                <button type="button" onClick={() => setShowPass(v => !v)}
                  style={{ position:"absolute", right:12, top:"50%", transform:"translateY(-50%)", background:"none", border:"none", cursor:"pointer", padding:2 }}>
                  {showPass ? <EyeOff size={15} color="#9CA3AF" /> : <Eye size={15} color="#9CA3AF" />}
                </button>
              </div>
            </div>

            {/* Error */}
            {error && (
              <div style={{ padding:"10px 14px", background:"#FEF2F2", border:"1px solid #FCA5A5", borderRadius:8, color:"#DC2626", fontSize:13 }}>
                {error}
              </div>
            )}

            {/* Login button */}
            <button type="submit" disabled={isLoading}
              style={{ marginTop:4, padding:"12px", background:"linear-gradient(135deg,#185FA5 0%,#1A7ABF 100%)", border:"none", borderRadius:10, color:"#FFFFFF", fontSize:14, fontWeight:700, cursor:"pointer", display:"flex", alignItems:"center", justifyContent:"center", gap:8, boxShadow:"0 4px 14px rgba(24,95,165,0.35)", transition:"opacity 0.15s" }}
              onMouseEnter={e => (e.currentTarget.style.opacity = "0.92")}
              onMouseLeave={e => (e.currentTarget.style.opacity = "1")}
            >
              {isLoading ? <RefreshCw size={15} style={{ animation:"spin 0.8s linear infinite" }} /> : null}
              {isLoading ? "Signing in…" : "Sign in to EdGuard"}
              {!isLoading && <ChevronRight size={15} />}
            </button>
          </form>

          {/* Divider */}
          <div style={{ display:"flex", alignItems:"center", gap:12, margin:"24px 0 20px" }}>
            <div style={{ flex:1, height:1, background:"#E5E7EB" }} />
            <span style={{ color:"#9CA3AF", fontSize:12, whiteSpace:"nowrap" }}>or sign in as demo user</span>
            <div style={{ flex:1, height:1, background:"#E5E7EB" }} />
          </div>

          {/* Demo accounts */}
          <div style={{ display:"flex", flexDirection:"column", gap:8 }}>
            {DEMO_CREDENTIALS.map((cred, i) => (
              <button key={i} onClick={() => handleDemoLogin(cred.email)}
                style={{ display:"flex", alignItems:"center", gap:12, padding:"10px 14px", background:"#FFFFFF", border:"1.5px solid #E5E7EB", borderRadius:10, cursor:"pointer", transition:"all 0.15s", textAlign:"left" }}
                onMouseEnter={e => { e.currentTarget.style.borderColor = "#185FA5"; e.currentTarget.style.background = "#EBF4FF"; }}
                onMouseLeave={e => { e.currentTarget.style.borderColor = "#E5E7EB"; e.currentTarget.style.background = "#FFFFFF"; }}
              >
                <div style={{ width:34,height:34,borderRadius:"50%",background:`linear-gradient(135deg,${cred.color},${cred.color}CC)`,display:"flex",alignItems:"center",justifyContent:"center",flexShrink:0 }}>
                  <span style={{ color:"#FFFFFF", fontSize:11, fontWeight:700 }}>{cred.initials}</span>
                </div>
                <div style={{ flex:1, minWidth:0 }}>
                  <div style={{ color:"#1A1A2E", fontSize:13, fontWeight:600 }}>{cred.name}</div>
                  <div style={{ color:"#9CA3AF", fontSize:11 }}>{cred.role}</div>
                </div>
                <ChevronRight size={14} color="#9CA3AF" />
              </button>
            ))}
          </div>

          {/* Footer note */}
          <div style={{ marginTop:28, padding:"12px 16px", background:"#F9FAFB", borderRadius:8, border:"1px solid #E5E7EB" }}>
            <div style={{ display:"flex", alignItems:"flex-start", gap:8 }}>
              <Shield size={13} color="#6B7280" style={{ flexShrink:0, marginTop:1 }} />
              <p style={{ color:"#6B7280", fontSize:11, lineHeight:1.5, margin:0 }}>
                This system is for authorised KOI academic staff only. Access is monitored and logged for compliance. Do not share credentials.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}