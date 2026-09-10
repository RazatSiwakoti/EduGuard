import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { confirmPasswordReset } from "../services/authService";

export default function ResetPasswordPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [message, setMessage] = useState("");
  const [saving, setSaving] = useState(false);

  async function submit() {
    if (password.length < 8 || password !== confirmation) {
      setMessage("Use at least 8 characters and ensure both passwords match.");
      return;
    }
    setSaving(true);
    try {
      await confirmPasswordReset(params.get("token") || "", password);
      setMessage("Your password has been reset. You can now sign in.");
      setTimeout(() => navigate("/login"), 1200);
    } catch {
      setMessage("This reset link is invalid or has expired.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <main style={{ maxWidth: 420, margin: "12vh auto", padding: 24 }}>
      <h1>Reset your password</h1>
      <input type="password" placeholder="New password" value={password} onChange={(e) => setPassword(e.target.value)} />
      <input type="password" placeholder="Confirm password" value={confirmation} onChange={(e) => setConfirmation(e.target.value)} />
      <button onClick={submit} disabled={saving}>{saving ? "Saving…" : "Set password"}</button>
      {message && <p>{message}</p>}
    </main>
  );
}
