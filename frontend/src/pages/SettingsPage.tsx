import ThemeTiles from "../components/settings/ThemeTiles";
import FontSizeControl from "../components/settings/FontSizeControl";
import ToggleRow from "../components/settings/ToggleRow";
import { useAppearance } from "../context/AppearanceContext";

export default function SettingsPage() {
  const { preferences, set } = useAppearance();
  return (
    <div className="px-6 py-8">
      <div className="mx-auto max-w-2xl">
        <h1 className="text-xl font-semibold text-stone-900">Settings</h1>
        <p className="mt-1 text-sm text-stone-500">Personalise your EduGuard experience.</p>
        <section className="mt-6 rounded-lg border border-stone-200 bg-white p-5">
          <h2 className="text-sm font-semibold text-stone-900">Appearance</h2>
          <div className="mt-4 space-y-5">
            <div><p className="mb-2 text-xs font-medium uppercase tracking-wide text-stone-500">Theme</p><ThemeTiles value={preferences.theme} onChange={(theme) => set({ theme })} /></div>
            <div><p className="mb-2 text-xs font-medium uppercase tracking-wide text-stone-500">Font size</p><FontSizeControl value={preferences.font_size} onChange={(font_size) => set({ font_size })} /></div>
          </div>
        </section>
        <section className="mt-4 rounded-lg border border-stone-200 bg-white p-5">
          <h2 className="text-sm font-semibold text-stone-900">Accessibility</h2>
          <div className="mt-2 divide-y divide-stone-100">
            <ToggleRow label="Reduce motion" description="Turns off chart animations and page transitions." checked={preferences.reduce_motion} onChange={(reduce_motion) => set({ reduce_motion })} />
            <ToggleRow label="High contrast" description="Stronger borders and darker text. Removes the background texture." checked={preferences.high_contrast} onChange={(high_contrast) => set({ high_contrast })} />
            <ToggleRow label="Colour-blind safe colours" description="Uses a blue/orange risk palette instead of red/amber/green." checked={preferences.colourblind_safe} onChange={(colourblind_safe) => set({ colourblind_safe })} />
          </div>
          <p className="mt-3 text-xs text-stone-500">EduGuard also follows your device&apos;s own reduced-motion setting.</p>
        </section>
      </div>
    </div>
  );
}
