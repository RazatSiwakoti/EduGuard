import { useState } from "react";
import Avatar from "../components/Avatar";
import AvatarUploadDialog from "../components/account/AvatarUploadDialog";
import { useAuth } from "../context/AuthContext";
import { useChangePassword, useDeleteAvatar, useUpdateProfile } from "../hooks/useAccount";
import { formatRole } from "../utils/userDisplay";

export default function AccountPage() {
  const { user } = useAuth();
  const updateProfile = useUpdateProfile();
  const changePassword = useChangePassword();
  const deleteAvatar = useDeleteAvatar();
  const [name, setName] = useState(user?.full_name ?? "");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [uploadOpen, setUploadOpen] = useState(false);

  if (!user) return null;
  const nameDirty = name.trim() !== user.full_name;
  const passwordError = confirmPassword && newPassword !== confirmPassword
    ? "Passwords do not match."
    : newPassword && newPassword === currentPassword
      ? "New password must differ from your current password."
      : newPassword && newPassword.length < 8
        ? "New password must be at least 8 characters."
        : "";
  const strength = newPassword.length >= 12 ? "Strong" : newPassword.length >= 8 ? "Good" : "Too short";

  function saveName(event: React.FormEvent) {
    event.preventDefault();
    updateProfile.mutate(name.trim());
  }

  function savePassword(event: React.FormEvent) {
    event.preventDefault();
    if (passwordError || !currentPassword || !newPassword) return;
    changePassword.mutate({ currentPassword, newPassword }, {
      onSuccess: () => {
        setCurrentPassword("");
        setNewPassword("");
        setConfirmPassword("");
      },
    });
  }

  return (
    <div className="px-6 py-8">
      <div className="mx-auto max-w-2xl">
        <h1 className="text-xl font-semibold text-stone-900">Account</h1>
        <p className="mt-1 text-sm text-stone-500">Manage your profile and sign-in details.</p>

        <section className="mt-6 rounded-lg border border-stone-200 bg-white p-5">
          <h2 className="text-sm font-semibold text-stone-900">Profile</h2>
          <div className="mt-4 flex flex-col gap-5 sm:flex-row">
            <div className="flex shrink-0 flex-col items-center gap-2">
              <Avatar src={user.avatar} name={user.full_name} size="xl" />
              <button type="button" onClick={() => setUploadOpen(true)} className="text-xs font-medium text-stone-700 underline underline-offset-2">Change photo</button>
              {user.avatar && <button type="button" onClick={() => deleteAvatar.mutate()} className="text-xs text-red-600 hover:underline">Remove</button>}
            </div>
            <form onSubmit={saveName} className="min-w-0 flex-1 space-y-3">
              <label className="block text-sm font-medium text-stone-700">Full name<input value={name} onChange={(event) => setName(event.target.value)} className="mt-1.5 w-full rounded border border-stone-300 px-3 py-2 font-normal outline-none focus:border-stone-500" /></label>
              <label className="block text-sm font-medium text-stone-700">Email<input value={user.email} readOnly className="mt-1.5 w-full cursor-not-allowed rounded border border-stone-200 bg-stone-50 px-3 py-2 text-sm font-normal text-stone-500" /><span className="mt-1 block text-xs font-normal text-stone-500">Your email is your sign-in and cannot be changed here. Contact an administrator.</span></label>
              <div className="grid grid-cols-2 gap-3 text-sm"><p><span className="block text-xs text-stone-500">Role</span>{formatRole(user.role)}</p><p><span className="block text-xs text-stone-500">Member since</span>{new Date(user.created_at).toLocaleDateString()}</p></div>
              <button type="submit" disabled={!nameDirty || updateProfile.isPending} className="rounded bg-stone-900 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-40">{updateProfile.isPending ? "Saving…" : "Save changes"}</button>
            </form>
          </div>
        </section>

        <section className="mt-4 rounded-lg border border-stone-200 bg-white p-5">
          <h2 className="text-sm font-semibold text-stone-900">Password</h2>
          <form onSubmit={savePassword} className="mt-4 max-w-md space-y-3">
            <PasswordField label="Current password" value={currentPassword} onChange={setCurrentPassword} />
            <PasswordField label="New password" value={newPassword} onChange={setNewPassword} />
            {newPassword && <p className="text-xs text-stone-500">Strength: <span className="font-medium">{strength}</span></p>}
            <PasswordField label="Confirm new password" value={confirmPassword} onChange={setConfirmPassword} />
            {passwordError && <p className="text-xs text-red-600">{passwordError}</p>}
            <button type="submit" disabled={Boolean(passwordError) || !currentPassword || !newPassword || !confirmPassword || changePassword.isPending} className="rounded bg-stone-900 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-40">{changePassword.isPending ? "Changing…" : "Change password"}</button>
          </form>
        </section>

        <section className="mt-4 rounded-lg border border-stone-200 bg-white p-5">
          <h2 className="text-sm font-semibold text-stone-900">Sessions</h2>
          <p className="mt-3 text-sm text-stone-600">Last signed in: {new Date(user.last_login).toLocaleString()}</p>
        </section>
      </div>
      {uploadOpen && <AvatarUploadDialog name={user.full_name} onOpenChange={setUploadOpen} />}
    </div>
  );
}

function PasswordField({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return <label className="block text-sm font-medium text-stone-700">{label}<input type="password" value={value} onChange={(event) => onChange(event.target.value)} className="mt-1.5 w-full rounded border border-stone-300 px-3 py-2 font-normal outline-none focus:border-stone-500" /></label>;
}
