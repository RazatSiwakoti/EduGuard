import React, { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router";
import {
  User, Bell, SlidersHorizontal, BookOpen, MessageSquare,
  LayoutDashboard, Shield, ChevronRight, Check, AlertCircle,
  Eye, EyeOff, ChevronDown, Mail, Clock, Activity, Lock,
  ToggleLeft, Info, Pencil, Save, LogOut, Monitor, Moon, Sun,
  PanelLeftClose, PanelLeftOpen, ArrowLeft
} from "lucide-react";
import { useTheme } from "../context/ThemeContext";

// ─── Types ───────────────────────────────────────────────────────────────────

type Section =
  | "account"
  | "notifications"
  | "risk-settings"
  | "subjects"
  | "alerts-comm"
  | "preferences"
  | "security";

interface NavItem {
  id: Section;
  label: string;
  icon: React.ReactNode;
  badge?: string;
}

// ─── Shared UI Primitives ─────────────────────────────────────────────────────

function Toggle({ checked, onChange, disabled }: { checked: boolean; onChange: () => void; disabled?: boolean }) {
  return (
    <button
      onClick={disabled ? undefined : onChange}
      aria-pressed={checked}
      className={`relative inline-flex items-center h-6 w-11 rounded-full transition-all duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#185FA5]/50 ${
        disabled ? "opacity-40 cursor-not-allowed" : "cursor-pointer"
      } ${checked ? "bg-[#185FA5]" : "bg-[#D1D5DB]"}`}
    >
      <span className={`inline-block h-5 w-5 rounded-full bg-white shadow-sm transform transition-transform duration-200 ${checked ? "translate-x-[22px]" : "translate-x-[2px]"}`} />
    </button>
  );
}

function FieldLabel({ children, hint }: { children: React.ReactNode; hint?: string }) {
  const [show, setShow] = useState(false);
  return (
    <div className="flex items-center gap-1.5 mb-1.5">
      <label className="text-[13px] font-semibold text-[#1A1A2E] dark:text-[#E2E8F0]">{children}</label>
      {hint && (
        <div className="relative">
          <button
            className="text-[#9CA3AF] hover:text-[#185FA5] transition-colors"
            onMouseEnter={() => setShow(true)}
            onMouseLeave={() => setShow(false)}
          >
            <Info size={12} />
          </button>
          {show && (
            <div className="absolute z-50 bottom-full left-1/2 -translate-x-1/2 mb-2 w-52 text-[11px] bg-[#1A1A2E] text-white rounded-lg px-3 py-2 leading-relaxed shadow-xl">
              {hint}
              <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-[#1A1A2E]" />
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function Input({
  value, onChange, type = "text", placeholder = "", disabled = false,
  prefix, suffix
}: {
  value: string; onChange?: (v: string) => void; type?: string;
  placeholder?: string; disabled?: boolean;
  prefix?: React.ReactNode; suffix?: React.ReactNode;
}) {
  return (
    <div className="relative flex items-center">
      {prefix && <div className="absolute left-3 text-[#9CA3AF] dark:text-[#64748B]">{prefix}</div>}
      <input
        type={type}
        value={value}
        onChange={e => onChange?.(e.target.value)}
        placeholder={placeholder}
        disabled={disabled}
        className={`w-full h-10 rounded-xl border border-[#E5E7EB] dark:border-[#1E3550] bg-white/80 dark:bg-[#162232]/80 text-[13px] text-[#1A1A2E] dark:text-[#E2E8F0] placeholder-[#9CA3AF] dark:placeholder-[#4B6480] focus:outline-none focus:border-[#185FA5] focus:ring-2 focus:ring-[#185FA5]/10 transition-all duration-150 ${prefix ? "pl-9" : "pl-3"} ${suffix ? "pr-9" : "pr-3"} ${disabled ? "opacity-50 cursor-not-allowed bg-[#F9FAFB] dark:bg-[#0F1824]" : ""}`}
      />
      {suffix && <div className="absolute right-3">{suffix}</div>}
    </div>
  );
}

function Select({ value, onChange, options }: {
  value: string; onChange: (v: string) => void;
  options: { value: string; label: string }[];
}) {
  return (
    <div className="relative">
      <select
        value={value}
        onChange={e => onChange(e.target.value)}
        className="w-full h-10 pl-3 pr-8 rounded-xl border border-[#E5E7EB] dark:border-[#1E3550] bg-white/80 dark:bg-[#162232]/80 text-[13px] text-[#1A1A2E] dark:text-[#E2E8F0] focus:outline-none focus:border-[#185FA5] focus:ring-2 focus:ring-[#185FA5]/10 transition-all duration-150 appearance-none cursor-pointer"
      >
        {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
      <ChevronDown size={13} className="absolute right-3 top-1/2 -translate-y-1/2 text-[#9CA3AF] dark:text-[#4B6480] pointer-events-none" />
    </div>
  );
}

function SectionCard({ title, subtitle, children }: {
  title: string; subtitle?: string; children: React.ReactNode;
}) {
  return (
    <div className="bg-white/70 dark:bg-[#162232]/80 backdrop-blur-sm rounded-2xl border border-[#E5E7EB]/80 dark:border-[#1E3550] shadow-[0_1px_8px_rgba(0,0,0,0.05)] dark:shadow-[0_1px_8px_rgba(0,0,0,0.25)] overflow-hidden mb-5">
      <div className="px-6 py-4 border-b border-[#F3F4F6] dark:border-[#1E3550]">
        <h3 className="text-[14px] font-bold text-[#1A1A2E] dark:text-[#E2E8F0] tracking-tight">{title}</h3>
        {subtitle && <p className="text-[11px] text-[#9CA3AF] dark:text-[#64748B] mt-0.5 font-normal">{subtitle}</p>}
      </div>
      <div className="px-6 py-5">{children}</div>
    </div>
  );
}

function ToggleRow({
  label, desc, checked, onChange, disabled
}: { label: string; desc?: string; checked: boolean; onChange: () => void; disabled?: boolean }) {
  return (
    <div className="flex items-center justify-between py-3 border-b border-[#F9FAFB] dark:border-[#1A2D45] last:border-0">
      <div className="flex-1 pr-4">
        <div className="text-[13px] font-semibold text-[#1A1A2E] dark:text-[#E2E8F0]">{label}</div>
        {desc && <div className="text-[11px] text-[#9CA3AF] dark:text-[#64748B] mt-0.5 leading-relaxed">{desc}</div>}
      </div>
      <Toggle checked={checked} onChange={onChange} disabled={disabled} />
    </div>
  );
}

function StatusMessage({ type, message }: { type: "success" | "error"; message: string }) {
  return (
    <div className={`flex items-center gap-2 text-[12px] px-3 py-2 rounded-lg mt-3 ${
      type === "success" ? "bg-[#ECFDF5] text-[#15803D]" : "bg-[#FEF2F2] text-[#DC2626]"
    }`}>
      {type === "success" ? <Check size={13} /> : <AlertCircle size={13} />}
      {message}
    </div>
  );
}

function SaveButton({
  onClick, disabled, loading, label = "Save Changes"
}: { onClick: () => void; disabled?: boolean; loading?: boolean; label?: string }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled || loading}
      className={`inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-[13px] font-semibold transition-all duration-200 ${
        disabled
          ? "bg-[#F3F4F6] dark:bg-[#1A2D45] text-[#9CA3AF] dark:text-[#4B6480] cursor-not-allowed"
          : "bg-[#185FA5] text-white hover:bg-[#1351919] shadow-[0_2px_8px_rgba(24,95,165,0.25)] hover:shadow-[0_4px_14px_rgba(24,95,165,0.35)] hover:translate-y-[-1px] active:translate-y-0"
      }`}
    >
      {loading ? (
        <span className="inline-block w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
      ) : (
        <Save size={13} />
      )}
      {loading ? "Saving…" : label}
    </button>
  );
}

function SliderInput({
  value, onChange, min = 0, max = 1, step = 0.01,
  color = "#185FA5"
}: {
  value: number; onChange: (v: number) => void;
  min?: number; max?: number; step?: number; color?: string;
}) {
  const pct = ((value - min) / (max - min)) * 100;
  return (
    <div className="flex items-center gap-4">
      <div className="relative flex-1 h-2">
        <div className="absolute inset-0 rounded-full bg-[#E5E7EB] dark:bg-[#1E3550]" />
        <div
          className="absolute left-0 top-0 h-full rounded-full transition-all duration-100"
          style={{ width: `${pct}%`, background: color }}
        />
        <input
          type="range"
          min={min} max={max} step={step}
          value={value}
          onChange={e => onChange(parseFloat(e.target.value))}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
        />
      </div>
      <div
        className="w-16 h-10 rounded-xl border border-[#E5E7EB] dark:border-[#1E3550] bg-white/80 dark:bg-[#162232]/80 text-[13px] font-semibold text-center text-[#1A1A2E] dark:text-[#E2E8F0] focus:outline-none focus:border-[#185FA5] tabular-nums"
        style={{ display: "flex", alignItems: "center", justifyContent: "center" }}
      >
        {value.toFixed(2)}
      </div>
    </div>
  );
}

// ─── Content Sections ─────────────────────────────────────────────────────────

function AccountSection() {
  const [form, setForm] = useState({
    name: "Dr. Sarah Mitchell",
    email: "s.mitchell@koi.edu.au",
    department: "School of Information Technology",
  });
  const [orig] = useState({ ...form });
  const [saved, setSaved] = useState<"idle" | "saving" | "ok" | "err">("idle");
  const [editEmail, setEditEmail] = useState(false);

  const isDirty = JSON.stringify(form) !== JSON.stringify(orig);

  const handleSave = async () => {
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) {
      setSaved("err"); setTimeout(() => setSaved("idle"), 3000); return;
    }
    setSaved("saving");
    await new Promise(r => setTimeout(r, 1000));
    setSaved("ok"); setTimeout(() => setSaved("idle"), 3000);
  };

  return (
    <>
      {/* Profile Card */}
      <SectionCard title="Profile Overview">
        <div className="flex items-center gap-5">
          <div className="relative flex-shrink-0">
            <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-[#185FA5] to-[#0E3D70] flex items-center justify-center text-white text-2xl font-bold font-serif shadow-lg">
              SM
            </div>
            <div className="absolute -bottom-1 -right-1 w-5 h-5 rounded-full bg-[#97C459] border-2 border-white" />
          </div>
          <div className="flex-1">
            <div className="font-serif text-[22px] text-[#1A1A2E] dark:text-[#E2E8F0] leading-tight">{form.name}</div>
            <div className="text-[13px] text-[#185FA5] font-semibold mt-0.5">{form.email}</div>
            <div className="flex items-center gap-2 mt-2">
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-[#EBF4FF] text-[#185FA5]">
                <ToggleLeft size={10} /> Lecturer
              </span>
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-[#F0FDF4] text-[#15803D]">
                <Activity size={10} /> Active
              </span>
            </div>
          </div>
        </div>
      </SectionCard>

      {/* Editable Form */}
      <SectionCard title="Edit Profile" subtitle="Update your display name, email and department">
        <div className="grid grid-cols-1 gap-4">
          <div>
            <FieldLabel hint="Your name as shown to students and in reports">Full Name</FieldLabel>
            <Input value={form.name} onChange={v => setForm(f => ({ ...f, name: v }))} prefix={<User size={13} />} />
          </div>
          <div>
            <FieldLabel hint="Used for notifications and login. Must be a valid KOI email address">Email Address</FieldLabel>
            <Input
              value={form.email}
              onChange={v => setForm(f => ({ ...f, email: v }))}
              type="email"
              disabled={!editEmail}
              prefix={<Mail size={13} />}
              suffix={
                <button onClick={() => setEditEmail(v => !v)} className="text-[#9CA3AF] hover:text-[#185FA5] transition-colors">
                  <Pencil size={12} />
                </button>
              }
            />
            {!editEmail && <p className="text-[10px] text-[#9CA3AF] mt-1">Click the pencil icon to edit your email</p>}
          </div>
          <div>
            <FieldLabel>Department</FieldLabel>
            <Select
              value={form.department}
              onChange={v => setForm(f => ({ ...f, department: v }))}
              options={[
                { value: "School of Information Technology", label: "School of Information Technology" },
                { value: "School of Business", label: "School of Business" },
                { value: "School of Health Sciences", label: "School of Health Sciences" },
                { value: "School of Education", label: "School of Education" },
              ]}
            />
          </div>
          <div>
            <FieldLabel>Role</FieldLabel>
            <Input value="Lecturer (Teaching Staff)" disabled />
            <p className="text-[10px] text-[#9CA3AF] mt-1">Role assignment is managed by your system administrator</p>
          </div>
        </div>
        <div className="flex items-center gap-3 mt-5">
          <SaveButton onClick={handleSave} disabled={!isDirty} loading={saved === "saving"} />
          {saved === "ok" && <StatusMessage type="success" message="Profile updated successfully" />}
          {saved === "err" && <StatusMessage type="error" message="Invalid email address format" />}
        </div>
      </SectionCard>
    </>
  );
}

function NotificationsSection() {
  const [emailEnabled, setEmailEnabled] = useState(true);
  const [pushEnabled, setPushEnabled] = useState(false);
  const [highRisk, setHighRisk] = useState(true);
  const [medRisk, setMedRisk] = useState(true);
  const [weeklyDigest, setWeeklyDigest] = useState(false);
  const [frequency, setFrequency] = useState("instant");
  const [saved, setSaved] = useState<"idle" | "ok">("idle");
  const [dirty, setDirty] = useState(false);

  const mark = () => setDirty(true);

  const handleSave = async () => {
    await new Promise(r => setTimeout(r, 800));
    setSaved("ok"); setDirty(false);
    setTimeout(() => setSaved("idle"), 3000);
  };

  return (
    <>
      <SectionCard title="Delivery Channels" subtitle="Choose how EdGuard reaches you">
        <ToggleRow
          label="Email Notifications"
          desc="Receive risk alerts and summaries via email at s.mitchell@koi.edu.au"
          checked={emailEnabled}
          onChange={() => { setEmailEnabled(v => !v); mark(); }}
        />
        <ToggleRow
          label="In-App Push Notifications"
          desc="Browser push notifications when active in EdGuard"
          checked={pushEnabled}
          onChange={() => { setPushEnabled(v => !v); mark(); }}
        />
      </SectionCard>

      <SectionCard title="Alert Preferences" subtitle="Control which events trigger notifications">
        <ToggleRow
          label="High Risk Alerts"
          desc="Notify immediately when a student crosses the high-risk threshold"
          checked={highRisk}
          onChange={() => { setHighRisk(v => !v); mark(); }}
        />
        <ToggleRow
          label="Medium Risk Escalations"
          desc="Notify when a student escalates from low to medium risk"
          checked={medRisk}
          onChange={() => { setMedRisk(v => !v); mark(); }}
        />
        <ToggleRow
          label="Weekly Digest"
          desc="Receive a cohort summary every Monday at 8:00 AM AEST"
          checked={weeklyDigest}
          onChange={() => { setWeeklyDigest(v => !v); mark(); }}
        />
      </SectionCard>

      <SectionCard title="Alert Frequency" subtitle="Set how often batched notifications are delivered">
        <div className="grid grid-cols-3 gap-3">
          {[
            { value: "instant", label: "Instant", desc: "Sent immediately", icon: <Activity size={16} /> },
            { value: "daily", label: "Daily Digest", desc: "Once per day at 8 AM", icon: <Clock size={16} /> },
            { value: "weekly", label: "Weekly Summary", desc: "Every Monday morning", icon: <Bell size={16} /> },
          ].map(opt => (
            <button
              key={opt.value}
              onClick={() => { setFrequency(opt.value); mark(); }}
              className={`p-4 rounded-xl border-2 text-left transition-all duration-200 ${
                frequency === opt.value
                  ? "border-[#185FA5] bg-[#EBF4FF]"
                  : "border-[#E5E7EB] bg-white/60 hover:border-[#185FA5]/30 hover:bg-[#EBF4FF]/40"
              }`}
            >
              <div className={`mb-2 ${frequency === opt.value ? "text-[#185FA5]" : "text-[#9CA3AF]"}`}>{opt.icon}</div>
              <div className={`text-[13px] font-semibold ${frequency === opt.value ? "text-[#185FA5]" : "text-[#1A1A2E] dark:text-[#E2E8F0]"}`}>{opt.label}</div>
              <div className="text-[11px] text-[#9CA3AF] mt-0.5">{opt.desc}</div>
            </button>
          ))}
        </div>
        <div className="flex items-center gap-3 mt-5">
          <SaveButton onClick={handleSave} disabled={!dirty} label="Save Notification Preferences" />
          {saved === "ok" && <StatusMessage type="success" message="Notification settings saved" />}
        </div>
      </SectionCard>
    </>
  );
}

function RiskSettingsSection() {
  const [high, setHigh] = useState(0.70);
  const [med, setMed] = useState(0.40);
  const [saved, setSaved] = useState<"idle" | "ok" | "err">("idle");

  const isValid = med < high && high <= 1 && med >= 0;
  const isDirty = high !== 0.70 || med !== 0.40;

  const handleSave = async () => {
    if (!isValid) { setSaved("err"); setTimeout(() => setSaved("idle"), 3000); return; }
    await new Promise(r => setTimeout(r, 900));
    setSaved("ok"); setTimeout(() => setSaved("idle"), 3000);
  };

  const bandWidth = {
    safe: med * 100,
    medium: (high - med) * 100,
    high: (1 - high) * 100,
  };

  return (
    <>
      <SectionCard title="Risk Thresholds" subtitle="Calibrate sensitivity of the hybrid ML + Rule-Based engine">
        <div className="space-y-6">
          <div>
            <div className="flex items-center justify-between mb-2">
              <FieldLabel hint="Students scoring above this threshold are flagged as High Risk. Lowering this value increases sensitivity.">
                High Risk Threshold
              </FieldLabel>
              <span className="text-[11px] font-semibold text-[#E24B4A] bg-[#FEE2E2] px-2 py-0.5 rounded-full">
                {high.toFixed(2)}
              </span>
            </div>
            <SliderInput value={high} onChange={v => setHigh(Math.max(med + 0.01, v))} color="#E24B4A" />
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <FieldLabel hint="Students scoring between this and the High Risk threshold are flagged as At Risk (Medium). Must be lower than High Risk Threshold.">
                Medium Risk Threshold
              </FieldLabel>
              <span className="text-[11px] font-semibold text-[#EF9F27] bg-[#FEF3C7] px-2 py-0.5 rounded-full">
                {med.toFixed(2)}
              </span>
            </div>
            <SliderInput value={med} onChange={v => setMed(Math.min(high - 0.01, v))} color="#EF9F27" />
          </div>

          {/* Visual band preview */}
          <div>
            <div className="text-[11px] font-semibold text-[#9CA3AF] uppercase tracking-wide mb-2">Risk Band Preview</div>
            <div className="flex h-8 rounded-xl overflow-hidden shadow-inner">
              <div
                className="h-full flex items-center justify-center text-[10px] font-bold text-white transition-all duration-300"
                style={{ width: `${bandWidth.safe}%`, background: "#97C459" }}
              >
                {bandWidth.safe > 15 ? "Safe" : ""}
              </div>
              <div
                className="h-full flex items-center justify-center text-[10px] font-bold text-white transition-all duration-300"
                style={{ width: `${bandWidth.medium}%`, background: "#EF9F27" }}
              >
                {bandWidth.medium > 12 ? "At Risk" : ""}
              </div>
              <div
                className="h-full flex items-center justify-center text-[10px] font-bold text-white transition-all duration-300"
                style={{ width: `${bandWidth.high}%`, background: "#E24B4A" }}
              >
                {bandWidth.high > 12 ? "High Risk" : ""}
              </div>
            </div>
            <div className="flex justify-between text-[10px] text-[#9CA3AF] mt-1">
              <span>0.00</span>
              <span>{med.toFixed(2)}</span>
              <span>{high.toFixed(2)}</span>
              <span>1.00</span>
            </div>
          </div>

          {!isValid && (
            <div className="flex items-center gap-2 text-[12px] text-[#DC2626] bg-[#FEF2F2] px-3 py-2 rounded-lg">
              <AlertCircle size={13} /> Medium threshold must be strictly less than High threshold
            </div>
          )}
        </div>

        <div className="flex items-center gap-3 mt-5">
          <button
            onClick={() => { setHigh(0.70); setMed(0.40); }}
            className="text-[12px] text-[#9CA3AF] hover:text-[#185FA5] transition-colors underline underline-offset-2"
          >
            Reset to defaults
          </button>
          <SaveButton onClick={handleSave} disabled={!isDirty || !isValid} label="Apply Thresholds" />
          {saved === "ok" && <StatusMessage type="success" message="Risk thresholds updated" />}
          {saved === "err" && <StatusMessage type="error" message="Threshold validation failed" />}
        </div>
      </SectionCard>

      <SectionCard title="Sensitivity Impact" subtitle="Approximate effect of current thresholds on your cohort">
        <div className="grid grid-cols-3 gap-4">
          {[
            { label: "Estimated Safe", value: `${Math.round(bandWidth.safe)}%`, color: "#97C459", bg: "#F0FDF4" },
            { label: "Estimated At Risk", value: `${Math.round(bandWidth.medium)}%`, color: "#EF9F27", bg: "#FFFBEB" },
            { label: "Estimated High Risk", value: `${Math.round(bandWidth.high)}%`, color: "#E24B4A", bg: "#FEF2F2" },
          ].map(item => (
            <div key={item.label} className="rounded-xl p-4 text-center" style={{ background: item.bg }}>
              <div className="text-[22px] font-bold font-mono tabular" style={{ color: item.color }}>{item.value}</div>
              <div className="text-[11px] text-[#6B7280] dark:text-[#64748B] mt-0.5">{item.label}</div>
            </div>
          ))}
        </div>
        <p className="text-[10px] text-[#9CA3AF] mt-3">
          * Estimates based on uniform score distribution across your enrolled cohort. Actual distribution will vary.
        </p>
      </SectionCard>
    </>
  );
}

function SubjectsSection() {
  const [subjects, setSubjects] = useState([
    { code: "BSYS301", name: "Business Systems Design", enrolled: 42, visible: true },
    { code: "ICT711", name: "Advanced Network Security", enrolled: 31, visible: true },
    { code: "ICT501", name: "Database Management Systems", enrolled: 58, visible: false },
    { code: "BSYS211", name: "Systems Analysis & Design", enrolled: 24, visible: true },
    { code: "ICT820", name: "Cloud Computing Architecture", enrolled: 18, visible: false },
  ]);
  const [saved, setSaved] = useState<"idle" | "ok">("idle");

  const handleSave = async () => {
    await new Promise(r => setTimeout(r, 800));
    setSaved("ok"); setTimeout(() => setSaved("idle"), 3000);
  };

  const activeCount = subjects.filter(s => s.visible).length;

  return (
    <>
      <SectionCard
        title="Assigned Subjects & Classes"
        subtitle={`${activeCount} of ${subjects.length} subjects visible in your dashboard`}
      >
        <div className="space-y-2">
          {subjects.map(sub => (
            <div
              key={sub.code}
              className={`flex items-center gap-4 p-4 rounded-xl border transition-all duration-200 ${
                sub.visible
                  ? "border-[#185FA5]/20 bg-[#EBF4FF]/40"
                  : "border-[#E5E7EB] bg-[#F9FAFB]/60"
              }`}
            >
              <div className={`w-10 h-10 rounded-xl flex items-center justify-center text-[10px] font-bold font-mono flex-shrink-0 ${
                sub.visible ? "bg-[#185FA5] text-white" : "bg-[#E5E7EB] text-[#9CA3AF]"
              }`}>
                {sub.code.slice(0, 3)}
              </div>
              <div className="flex-1 min-w-0">
                <div className={`text-[13px] font-semibold ${sub.visible ? "text-[#1A1A2E] dark:text-[#E2E8F0]" : "text-[#9CA3AF] dark:text-[#4B6480]"}`}>
                  {sub.code}
                </div>
                <div className="text-[11px] text-[#6B7280] dark:text-[#64748B] truncate">{sub.name}</div>
              </div>
              <div className="text-[11px] text-[#9CA3AF] font-mono tabular flex-shrink-0">
                {sub.enrolled} students
              </div>
              <Toggle
                checked={sub.visible}
                onChange={() => setSubjects(prev =>
                  prev.map(s => s.code === sub.code ? { ...s, visible: !s.visible } : s)
                )}
              />
            </div>
          ))}
        </div>
        <div className="flex items-center gap-3 mt-5">
          <SaveButton onClick={handleSave} label="Save Subject Visibility" />
          {saved === "ok" && <StatusMessage type="success" message="Dashboard filters updated" />}
        </div>
      </SectionCard>

      <SectionCard title="Visibility Summary" subtitle="Currently visible subjects will appear in dashboard filters and reports">
        <div className="flex flex-wrap gap-2">
          {subjects.filter(s => s.visible).map(s => (
            <span key={s.code} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[12px] font-semibold bg-[#185FA5] text-white">
              <BookOpen size={10} /> {s.code}
            </span>
          ))}
          {subjects.filter(s => !s.visible).map(s => (
            <span key={s.code} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[12px] font-semibold bg-[#F3F4F6] text-[#9CA3AF] line-through">
              {s.code}
            </span>
          ))}
        </div>
      </SectionCard>
    </>
  );
}

function AlertsCommSection() {
  const DEFAULT_TEMPLATE = `Dear {student_name},

I hope this message finds you well. I am reaching out as your lecturer for {subject_code} because our academic monitoring system has identified that you may be experiencing some difficulties this semester.

Your current academic standing has been flagged for review based on the following indicators:
- Assessment performance: {assessment_score}%
- Attendance rate: {attendance_rate}%
- Assignment submission status: {submission_status}

I would like to schedule a brief 15-minute meeting to discuss any challenges you may be facing and explore the support options available to you at KOI. Please reply to this email or book a time via the student portal.

You are not alone, and there are many resources available to help you succeed.

Kind regards,
{lecturer_name}
{department}
King's Own Institute`;

  const [template, setTemplate] = useState(DEFAULT_TEMPLATE);
  const [preview, setPreview] = useState(false);
  const [saved, setSaved] = useState<"idle" | "ok">("idle");

  const previewText = template
    .replace("{student_name}", "James Thornton")
    .replace("{subject_code}", "ICT711")
    .replace("{assessment_score}", "52")
    .replace("{attendance_rate}", "61")
    .replace("{submission_status}", "2 missed")
    .replace("{lecturer_name}", "Dr. Sarah Mitchell")
    .replace("{department}", "School of Information Technology");

  const handleSave = async () => {
    await new Promise(r => setTimeout(r, 900));
    setSaved("ok"); setTimeout(() => setSaved("idle"), 3000);
  };

  return (
    <>
      <SectionCard title="Email Alert Template" subtitle="Customise the message sent to at-risk students">
        <div className="flex items-center gap-2 mb-4">
          {["Template", "Preview"].map((tab, i) => (
            <button
              key={tab}
              onClick={() => setPreview(i === 1)}
              className={`px-4 py-1.5 rounded-lg text-[12px] font-semibold transition-all duration-150 ${
                preview === (i === 1)
                  ? "bg-[#185FA5] text-white"
                  : "text-[#6B7280] dark:text-[#94A3B8] hover:bg-[#F3F4F6] dark:hover:bg-[#1A2D45]"
              }`}
            >
              {tab}
            </button>
          ))}
        </div>

        {!preview ? (
          <div>
            <div className="mb-3 flex flex-wrap gap-2">
              {["{student_name}", "{subject_code}", "{assessment_score}", "{attendance_rate}", "{submission_status}", "{lecturer_name}", "{department}"].map(tag => (
                <button
                  key={tag}
                  onClick={() => {}}
                  className="text-[10px] font-mono bg-[#F0FDF4] text-[#15803D] border border-[#BBF7D0] px-2 py-0.5 rounded cursor-default"
                >
                  {tag}
                </button>
              ))}
            </div>
            <textarea
              value={template}
              onChange={e => setTemplate(e.target.value)}
              rows={14}
              className="w-full text-[12px] font-mono text-[#1A1A2E] dark:text-[#E2E8F0] bg-white/80 dark:bg-[#162232]/80 border border-[#E5E7EB] dark:border-[#1E3550] rounded-xl px-4 py-3 focus:outline-none focus:border-[#185FA5] focus:ring-2 focus:ring-[#185FA5]/10 resize-none leading-relaxed transition-all"
            />
          </div>
        ) : (
          <div className="bg-[#F9FAFB] border border-[#E5E7EB] rounded-xl p-5">
            <div className="text-[10px] font-semibold uppercase tracking-wider text-[#9CA3AF] mb-3">Preview — Rendered for James Thornton / ICT711</div>
            <div className="text-[12px] text-[#374151] dark:text-[#CBD5E1] leading-relaxed whitespace-pre-line font-sans">
              {previewText}
            </div>
          </div>
        )}

        <div className="flex items-center gap-3 mt-4">
          <SaveButton onClick={handleSave} label="Save Template" />
          <button
            onClick={() => setTemplate(DEFAULT_TEMPLATE)}
            className="text-[12px] text-[#9CA3AF] hover:text-[#185FA5] transition-colors underline underline-offset-2"
          >
            Reset to default
          </button>
          {saved === "ok" && <StatusMessage type="success" message="Template saved successfully" />}
        </div>
      </SectionCard>
    </>
  );
}

function PreferencesSection() {
  const { theme, setTheme: setGlobalTheme } = useTheme();
  const [defaultRiskFilter, setDefaultRiskFilter] = useState("all");
  const [defaultSubject, setDefaultSubject] = useState("all");
  const [compactTable, setCompactTable] = useState(false);
  const [showSHAP, setShowSHAP] = useState(true);
  const [animateCharts, setAnimateCharts] = useState(true);
  const [saved, setSaved] = useState<"idle" | "ok">("idle");
  const [dirty, setDirty] = useState(false);

  const mark = () => setDirty(true);

  const handleThemeChange = (val: "light" | "dark" | "system") => {
    setGlobalTheme(val);
    mark();
  };

  const handleSave = async () => {
    await new Promise(r => setTimeout(r, 800));
    setSaved("ok"); setDirty(false);
    setTimeout(() => setSaved("idle"), 3000);
  };

  const themeOptions: { value: "light" | "system" | "dark"; label: string; icon: React.ReactNode }[] = [
    { value: "light", label: "Light", icon: <Sun size={16} /> },
    { value: "system", label: "System", icon: <Monitor size={16} /> },
    { value: "dark", label: "Dark", icon: <Moon size={16} /> },
  ];

  return (
    <>
      <SectionCard title="Appearance" subtitle="Personalise EdGuard's visual presentation">
        <div className="mb-4">
          <FieldLabel>Theme</FieldLabel>
          <div className="grid grid-cols-3 gap-3 mt-1">
            {themeOptions.map(opt => (
              <button
                key={opt.value}
                onClick={() => handleThemeChange(opt.value)}
                className={`p-3 rounded-xl border-2 flex flex-col items-center gap-1.5 transition-all duration-200 ${
                  theme === opt.value
                    ? "border-[#185FA5] bg-[#EBF4FF] dark:bg-[#0B2D4A]"
                    : "border-[#E5E7EB] dark:border-[#1E3550] bg-white/60 dark:bg-[#162232]/60 hover:border-[#185FA5]/30"
                }`}
              >
                <span className={theme === opt.value ? "text-[#185FA5]" : "text-[#9CA3AF]"}>{opt.icon}</span>
                <span className={`text-[12px] font-semibold ${theme === opt.value ? "text-[#185FA5]" : "text-[#6B7280] dark:text-[#94A3B8]"}`}>{opt.label}</span>
              </button>
            ))}
          </div>
          <p className="text-[11px] text-[#9CA3AF] mt-2 leading-relaxed">
            Changes apply immediately across the entire EdGuard interface.
          </p>
        </div>
        <ToggleRow label="Animate Charts" desc="Enable entrance animations on charts and graphs" checked={animateCharts} onChange={() => { setAnimateCharts(v => !v); mark(); }} />
      </SectionCard>

      <SectionCard title="Dashboard Defaults" subtitle="Set default filter states when EdGuard first loads">
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <FieldLabel>Default Risk Level Filter</FieldLabel>
            <Select
              value={defaultRiskFilter}
              onChange={v => { setDefaultRiskFilter(v); mark(); }}
              options={[
                { value: "all", label: "All Students" },
                { value: "high", label: "High Risk Only" },
                { value: "medium", label: "Medium Risk Only" },
                { value: "at-risk", label: "All At-Risk" },
              ]}
            />
          </div>
          <div>
            <FieldLabel>Default Subject</FieldLabel>
            <Select
              value={defaultSubject}
              onChange={v => { setDefaultSubject(v); mark(); }}
              options={[
                { value: "all", label: "All Subjects" },
                { value: "BSYS301", label: "BSYS301" },
                { value: "ICT711", label: "ICT711" },
                { value: "BSYS211", label: "BSYS211" },
              ]}
            />
          </div>
        </div>
        <ToggleRow label="Compact Table Mode" desc="Show more students per page with reduced row height" checked={compactTable} onChange={() => { setCompactTable(v => !v); mark(); }} />
        <ToggleRow label="Show SHAP Explanations" desc="Display feature impact indicators on student risk cards" checked={showSHAP} onChange={() => { setShowSHAP(v => !v); mark(); }} />
        <div className="flex items-center gap-3 mt-5">
          <SaveButton onClick={handleSave} disabled={!dirty} label="Save Preferences" />
          {saved === "ok" && <StatusMessage type="success" message="Preferences saved" />}
        </div>
      </SectionCard>
    </>
  );
}

function SecuritySection() {
  const [currentPw, setCurrentPw] = useState("");
  const [newPw, setNewPw] = useState("");
  const [confirmPw, setConfirmPw] = useState("");
  const [showCurrent, setShowCurrent] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [sessionTimeout, setSessionTimeout] = useState("30");
  const [twoFA, setTwoFA] = useState(false);
  const [pwSaved, setPwSaved] = useState<"idle" | "saving" | "ok" | "err">("idle");

  const strength = (() => {
    if (!newPw) return 0;
    let score = 0;
    if (newPw.length >= 8) score++;
    if (/[A-Z]/.test(newPw)) score++;
    if (/[0-9]/.test(newPw)) score++;
    if (/[^A-Za-z0-9]/.test(newPw)) score++;
    return score;
  })();

  const strengthLabel = ["", "Weak", "Fair", "Good", "Strong"][strength];
  const strengthColor = ["", "#E24B4A", "#EF9F27", "#185FA5", "#97C459"][strength];

  const handlePwSave = async () => {
    if (!currentPw || !newPw || newPw !== confirmPw) {
      setPwSaved("err"); setTimeout(() => setPwSaved("idle"), 3000); return;
    }
    if (strength < 2) {
      setPwSaved("err"); setTimeout(() => setPwSaved("idle"), 3000); return;
    }
    setPwSaved("saving");
    await new Promise(r => setTimeout(r, 1200));
    setPwSaved("ok");
    setCurrentPw(""); setNewPw(""); setConfirmPw("");
    setTimeout(() => setPwSaved("idle"), 4000);
  };

  const loginActivity = [
    { date: "Today, 09:14 AM", location: "Sydney, AU", device: "Chrome 124 / macOS", current: true },
    { date: "Yesterday, 6:02 PM", location: "Sydney, AU", device: "Safari / iPhone 15", current: false },
    { date: "22 May 2025, 11:30 AM", location: "Sydney, AU", device: "Chrome 124 / macOS", current: false },
    { date: "20 May 2025, 3:45 PM", location: "Melbourne, AU", device: "Firefox 125 / Windows", current: false },
  ];

  return (
    <>
      <SectionCard title="Change Password" subtitle="Use a strong, unique password for your EdGuard account">
        <div className="space-y-4">
          <div>
            <FieldLabel>Current Password</FieldLabel>
            <Input
              value={currentPw} onChange={setCurrentPw} type={showCurrent ? "text" : "password"}
              placeholder="Enter current password" prefix={<Lock size={13} />}
              suffix={
                <button onClick={() => setShowCurrent(v => !v)} className="text-[#9CA3AF] hover:text-[#185FA5] transition-colors">
                  {showCurrent ? <EyeOff size={13} /> : <Eye size={13} />}
                </button>
              }
            />
          </div>
          <div>
            <FieldLabel>New Password</FieldLabel>
            <Input
              value={newPw} onChange={setNewPw} type={showNew ? "text" : "password"}
              placeholder="Min. 8 chars, mixed case + number" prefix={<Lock size={13} />}
              suffix={
                <button onClick={() => setShowNew(v => !v)} className="text-[#9CA3AF] hover:text-[#185FA5] transition-colors">
                  {showNew ? <EyeOff size={13} /> : <Eye size={13} />}
                </button>
              }
            />
            {newPw && (
              <div className="flex items-center gap-3 mt-2">
                <div className="flex-1 flex gap-1">
                  {[1, 2, 3, 4].map(i => (
                    <div
                      key={i}
                      className="h-1.5 flex-1 rounded-full transition-all duration-300"
                      style={{ background: i <= strength ? strengthColor : "#E5E7EB" }}
                    />
                  ))}
                </div>
                <span className="text-[11px] font-semibold" style={{ color: strengthColor }}>{strengthLabel}</span>
              </div>
            )}
          </div>
          <div>
            <FieldLabel>Confirm New Password</FieldLabel>
            <Input
              value={confirmPw} onChange={setConfirmPw} type="password"
              placeholder="Repeat new password" prefix={<Lock size={13} />}
            />
            {confirmPw && newPw !== confirmPw && (
              <p className="text-[11px] text-[#DC2626] mt-1">Passwords do not match</p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-3 mt-5">
          <SaveButton
            onClick={handlePwSave}
            disabled={!currentPw || !newPw || !confirmPw}
            loading={pwSaved === "saving"}
            label="Update Password"
          />
          {pwSaved === "ok" && <StatusMessage type="success" message="Password changed successfully" />}
          {pwSaved === "err" && <StatusMessage type="error" message="Passwords don't match or current password incorrect" />}
        </div>
      </SectionCard>

      <SectionCard title="Session & Access" subtitle="Control how long your session stays active">
        <div className="mb-4">
          <FieldLabel hint="After this period of inactivity, you will be automatically logged out">Session Timeout</FieldLabel>
          <div className="grid grid-cols-3 gap-3 mt-1">
            {["15", "30", "60"].map(min => (
              <button
                key={min}
                onClick={() => setSessionTimeout(min)}
                className={`py-2.5 rounded-xl border-2 text-[13px] font-semibold transition-all duration-150 ${
                  sessionTimeout === min
                    ? "border-[#185FA5] bg-[#EBF4FF] dark:bg-[#0B2D4A] text-[#185FA5]"
                    : "border-[#E5E7EB] dark:border-[#1E3550] bg-white/60 dark:bg-[#162232]/60 text-[#6B7280] dark:text-[#94A3B8] hover:border-[#185FA5]/30"
                }`}
              >
                {min} min
              </button>
            ))}
          </div>
        </div>
        <ToggleRow
          label="Two-Factor Authentication"
          desc="Require email OTP verification on each login. Requires IT admin confirmation."
          checked={twoFA}
          onChange={() => setTwoFA(v => !v)}
        />
      </SectionCard>

      <SectionCard title="Recent Login Activity" subtitle="Review recent sessions for suspicious access">
        <div className="space-y-2">
          {loginActivity.map((item, i) => (
            <div key={i} className={`flex items-center gap-4 p-3 rounded-xl ${item.current ? "bg-[#EBF4FF]" : "bg-[#F9FAFB]"}`}>
              <div className={`w-2 h-2 rounded-full flex-shrink-0 ${item.current ? "bg-[#97C459]" : "bg-[#D1D5DB]"}`} />
              <div className="flex-1 min-w-0">
                <div className="text-[12px] font-semibold text-[#1A1A2E] dark:text-[#E2E8F0]">{item.date}</div>
                <div className="text-[11px] text-[#9CA3AF]">{item.device} · {item.location}</div>
              </div>
              {item.current && (
                <span className="text-[10px] font-bold bg-[#185FA5] text-white px-2 py-0.5 rounded-full flex-shrink-0">
                  CURRENT
                </span>
              )}
            </div>
          ))}
        </div>
        <button className="mt-4 flex items-center gap-1.5 text-[12px] font-semibold text-[#E24B4A] hover:opacity-80 transition-opacity">
          <LogOut size={13} /> Sign out all other sessions
        </button>
      </SectionCard>
    </>
  );
}

// ─── Sidebar ──────────────────────────────────────────────────────────────────

const NAV_ITEMS: NavItem[] = [
  { id: "account", label: "Account", icon: <User size={16} /> },
  { id: "notifications", label: "Notifications", icon: <Bell size={16} /> },
  { id: "risk-settings", label: "Risk Settings", icon: <SlidersHorizontal size={16} />, badge: "!" },
  { id: "subjects", label: "Subjects & Classes", icon: <BookOpen size={16} /> },
  { id: "alerts-comm", label: "Alerts & Comms", icon: <MessageSquare size={16} /> },
  { id: "preferences", label: "Preferences", icon: <LayoutDashboard size={16} /> },
  { id: "security", label: "Security", icon: <Shield size={16} /> },
];

// ─── Main Component ───────────────────────────────────────────────────────────

export default function SettingsPage() {
  const [active, setActive] = useState<Section>("account");
  const [collapsed, setCollapsed] = useState(false);
  const contentRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  const { isDark } = useTheme();

  // Dark mode palette shortcuts for the Settings shell
  const D = {
    pageBg: isDark ? "#0D1B2A" : "#F6F5F1",
    headerBg: isDark ? "rgba(13,27,42,0.92)" : "rgba(255,255,255,0.88)",
    headerBorder: isDark ? "rgba(255,255,255,0.07)" : "rgba(17,24,39,0.08)",
    sidebarBg: isDark ? "rgba(15,30,48,0.95)" : "rgba(255,255,255,0.75)",
    sidebarBorder: isDark ? "rgba(255,255,255,0.07)" : "rgba(229,231,235,0.9)",
    btnBorder: isDark ? "rgba(255,255,255,0.1)" : "#E5E7EB",
    btnColor: isDark ? "#94A3B8" : "#6B7280",
    btnHoverBg: isDark ? "rgba(24,95,165,0.15)" : "#EBF4FF",
    textPrimary: isDark ? "#F1F5F9" : "#0F172A",
    textSecondary: isDark ? "#94A3B8" : "#9CA3AF",
    navActive: isDark ? "#185FA5" : "#185FA5",
    navActiveBg: isDark ? "#185FA5" : "#185FA5",
    navInactiveBg: "transparent",
    labelBg: isDark ? "#1A2D45" : "#F9FAFB",
    divider: isDark ? "rgba(255,255,255,0.07)" : "#F3F4F6",
    toggleBtn: isDark ? "#1A2E45" : "white",
    toggleBtnBorder: isDark ? "rgba(255,255,255,0.1)" : "#E5E7EB",
    sectionLabel: isDark ? "#4B6480" : "#9CA3AF",
  };

  useEffect(() => {
    if (contentRef.current) {
      contentRef.current.scrollTo({ top: 0, behavior: "smooth" });
    }
  }, [active]);

  const renderContent = () => {
    switch (active) {
      case "account": return <AccountSection />;
      case "notifications": return <NotificationsSection />;
      case "risk-settings": return <RiskSettingsSection />;
      case "subjects": return <SubjectsSection />;
      case "alerts-comm": return <AlertsCommSection />;
      case "preferences": return <PreferencesSection />;
      case "security": return <SecuritySection />;
    }
  };

  const activeItem = NAV_ITEMS.find(n => n.id === active);
  const sideW = collapsed ? 56 : 236;

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        display: "flex",
        flexDirection: "column",
        background: D.pageBg,
        backgroundImage: isDark
          ? `radial-gradient(1200px 600px at 85% -10%, rgba(24,95,165,0.14), transparent 60%),
             radial-gradient(900px 500px at -10% 110%, rgba(239,159,39,0.06), transparent 55%)`
          : `radial-gradient(1200px 600px at 85% -10%, rgba(24,95,165,0.08), transparent 60%),
             radial-gradient(900px 500px at -10% 110%, rgba(239,159,39,0.06), transparent 55%)`,
        fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
        color: D.textPrimary,
        zIndex: 500,
        transition: "background 0.3s ease, color 0.3s ease",
      }}
    >
      {/* ── Settings Top Bar ── */}
      <header
        style={{
          flexShrink: 0,
          height: "56px",
          background: D.headerBg,
          backdropFilter: "saturate(180%) blur(16px)",
          WebkitBackdropFilter: "saturate(180%) blur(16px)",
          borderBottom: `1px solid ${D.headerBorder}`,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "0 24px",
          zIndex: 10,
          transition: "background 0.3s ease",
        }}
      >
        {/* Left: back + branding */}
        <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
          <button
            onClick={() => navigate("/")}
            style={{
              display: "flex", alignItems: "center", gap: "6px",
              background: "none", border: `1px solid ${D.btnBorder}`, borderRadius: "9px",
              padding: "5px 12px", cursor: "pointer", color: D.btnColor,
              fontSize: "13px", fontWeight: 600, transition: "all 0.15s",
            }}
            onMouseEnter={e => {
              const el = e.currentTarget as HTMLButtonElement;
              el.style.borderColor = "#185FA5";
              el.style.color = "#185FA5";
              el.style.background = isDark ? "rgba(24,95,165,0.15)" : "#EBF4FF";
            }}
            onMouseLeave={e => {
              const el = e.currentTarget as HTMLButtonElement;
              el.style.borderColor = D.btnBorder;
              el.style.color = D.btnColor;
              el.style.background = "none";
            }}
          >
            <ArrowLeft size={13} />
            Dashboard
          </button>
          <div style={{ width: "1px", height: "22px", background: D.btnBorder }} />
          <div style={{ display: "flex", alignItems: "center", gap: "9px" }}>
            <div style={{
              width: "28px", height: "28px",
              background: "linear-gradient(140deg, #0B3D73 0%, #185FA5 55%, #2E8FD4 100%)",
              borderRadius: "7px", display: "flex", alignItems: "center", justifyContent: "center",
              boxShadow: "0 3px 8px -2px rgba(24,95,165,0.4)",
              flexShrink: 0,
            }}>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
                <path d="M12 2 L21 6 V12 C21 17 17 21 12 22 C7 21 3 17 3 12 V6 Z"
                  stroke="#FFFFFF" strokeWidth="1.6" strokeLinejoin="round" fill="rgba(255,255,255,0.08)" />
                <path d="M8.5 12.2 L11 14.7 L15.8 9.8" stroke="#FFFFFF" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <span style={{ fontSize: "15px", fontWeight: 700, color: D.textPrimary, letterSpacing: "-0.02em" }}>
              Ed<span style={{ fontFamily: "'Instrument Serif', serif", fontStyle: "italic", fontWeight: 400, color: "#185FA5" }}>Guard</span>
            </span>
            <span style={{ fontSize: "12px", color: D.textSecondary, fontWeight: 400 }}>/ Settings</span>
          </div>
        </div>

        {/* Right: user chip */}
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <div style={{ width: "32px", height: "32px", borderRadius: "50%", background: "linear-gradient(135deg,#185FA5,#2478C8)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
            <span style={{ color: "#fff", fontSize: "11px", fontWeight: 700 }}>SM</span>
          </div>
          <div>
            <div style={{ fontSize: "13px", fontWeight: 600, color: D.textPrimary, lineHeight: 1.2 }}>Dr. Sarah Mitchell</div>
            <div style={{ fontSize: "10px", color: D.textSecondary, lineHeight: 1.2 }}>Lecturer · KOI</div>
          </div>
        </div>
      </header>

      {/* ── Body row ── */}
      <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>

        {/* ── Sidebar ── */}
        <aside
          style={{
            flexShrink: 0,
            width: sideW,
            transition: "width 0.25s ease, background 0.3s ease",
            display: "flex",
            flexDirection: "column",
            background: D.sidebarBg,
            backdropFilter: "blur(14px)",
            WebkitBackdropFilter: "blur(14px)",
            borderRight: `1px solid ${D.sidebarBorder}`,
            boxShadow: isDark ? "1px 0 10px rgba(0,0,0,0.2)" : "1px 0 10px rgba(0,0,0,0.04)",
            overflow: "hidden",
            padding: "14px 8px 16px",
          }}
        >
          {/* Collapse toggle */}
          <div style={{ display: "flex", justifyContent: collapsed ? "center" : "flex-end", marginBottom: "10px", paddingRight: collapsed ? 0 : "2px" }}>
            <button
              onClick={() => setCollapsed(v => !v)}
              title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
              style={{
                width: "26px", height: "26px", borderRadius: "7px",
                border: `1px solid ${D.toggleBtnBorder}`, background: D.toggleBtn,
                display: "flex", alignItems: "center", justifyContent: "center",
                cursor: "pointer", color: D.textSecondary, transition: "all 0.15s", flexShrink: 0,
              }}
              onMouseEnter={e => { const el = e.currentTarget as HTMLButtonElement; el.style.color = "#185FA5"; el.style.borderColor = "#185FA5"; }}
              onMouseLeave={e => { const el = e.currentTarget as HTMLButtonElement; el.style.color = D.textSecondary; el.style.borderColor = D.toggleBtnBorder; }}
            >
              {collapsed ? <PanelLeftOpen size={12} /> : <PanelLeftClose size={12} />}
            </button>
          </div>

          {/* Section label */}
          {!collapsed && (
            <div style={{ paddingLeft: "10px", paddingBottom: "6px" }}>
              <span style={{ fontSize: "10px", fontWeight: 700, color: D.sectionLabel, letterSpacing: "0.08em", textTransform: "uppercase" }}>
                My Settings
              </span>
            </div>
          )}

          {/* Nav items */}
          <nav style={{ flex: 1, display: "flex", flexDirection: "column", gap: "2px" }}>
            {NAV_ITEMS.map(item => {
              const isActive = item.id === active;
              const hoverBg = isDark ? "rgba(255,255,255,0.06)" : "#F3F4F6";
              return (
                <button
                  key={item.id}
                  onClick={() => setActive(item.id)}
                  title={collapsed ? item.label : undefined}
                  style={{
                    width: "100%",
                    display: "flex",
                    alignItems: "center",
                    gap: collapsed ? 0 : "10px",
                    justifyContent: collapsed ? "center" : "flex-start",
                    padding: collapsed ? "9px 0" : "9px 10px",
                    borderRadius: "10px",
                    border: "none",
                    cursor: "pointer",
                    background: isActive ? "#185FA5" : "transparent",
                    color: isActive ? "#fff" : D.btnColor,
                    transition: "background 0.15s, color 0.15s",
                    boxShadow: isActive ? "0 2px 8px rgba(24,95,165,0.22)" : "none",
                  }}
                  onMouseEnter={e => { if (!isActive) (e.currentTarget as HTMLButtonElement).style.background = hoverBg; }}
                  onMouseLeave={e => { if (!isActive) (e.currentTarget as HTMLButtonElement).style.background = "transparent"; }}
                >
                  <span style={{ flexShrink: 0, color: isActive ? "#fff" : D.textSecondary, display: "flex" }}>{item.icon}</span>
                  {!collapsed && (
                    <>
                      <span style={{ flex: 1, fontSize: "13px", fontWeight: 600, textAlign: "left", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                        {item.label}
                      </span>
                      {item.badge && !isActive && (
                        <span style={{ width: "15px", height: "15px", borderRadius: "50%", background: "#E24B4A", color: "#fff", fontSize: "8px", fontWeight: 700, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                          {item.badge}
                        </span>
                      )}
                      {isActive && <ChevronRight size={11} style={{ flexShrink: 0, opacity: 0.7 }} />}
                    </>
                  )}
                </button>
              );
            })}
          </nav>

          {/* Footer user card */}
          {!collapsed && (
            <div style={{ borderTop: `1px solid ${D.divider}`, paddingTop: "10px", marginTop: "8px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px", padding: "7px 10px", borderRadius: "10px", background: D.labelBg }}>
                <div style={{ width: "26px", height: "26px", borderRadius: "7px", background: "linear-gradient(135deg,#185FA5,#0E3D70)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                  <span style={{ color: "#fff", fontSize: "9px", fontWeight: 700 }}>SM</span>
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: "11px", fontWeight: 600, color: D.textPrimary, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>Sarah Mitchell</div>
                  <div style={{ fontSize: "9px", color: D.textSecondary, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>s.mitchell@koi.edu.au</div>
                </div>
              </div>
            </div>
          )}
        </aside>

        {/* ── Main Content ── */}
        <div
          ref={contentRef}
          style={{
            flex: 1,
            overflowY: "auto",
            padding: "32px 40px 64px",
          }}
        >
          {/* Breadcrumb + heading */}
          <div style={{ marginBottom: "24px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
              <span style={{ color: "#185FA5", display: "flex" }}>{activeItem?.icon}</span>
              <h1 style={{ fontFamily: "'Instrument Serif', serif", fontSize: "26px", color: D.textPrimary, margin: 0, lineHeight: 1.2, letterSpacing: "-0.01em" }}>
                {activeItem?.label}
              </h1>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "4px", fontSize: "12px", color: D.textSecondary }}>
              <span>Settings</span>
              <ChevronRight size={11} />
              <span style={{ color: "#185FA5", fontWeight: 500 }}>{activeItem?.label}</span>
            </div>
          </div>

          {/* Section content */}
          <div style={{ maxWidth: "720px" }}>
            <div key={active} style={{ animation: "slideInSettings 0.2s ease" }}>
              {renderContent()}
            </div>
          </div>
        </div>
      </div>

      <style>{`
        @keyframes slideInSettings {
          from { opacity: 0; transform: translateX(10px); }
          to   { opacity: 1; transform: translateX(0); }
        }
      `}</style>
    </div>
  );
}
