import { useEffect, useState } from "react";
import type { Preferences } from "../../types/auth";

export default function ThemeTiles({ value, onChange }: { value: Preferences["theme"]; onChange: (value: Preferences["theme"]) => void }) {
  const [systemDark, setSystemDark] = useState(() => window.matchMedia("(prefers-color-scheme: dark)").matches);

  useEffect(() => {
    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
    const handleChange = (event: MediaQueryListEvent) => setSystemDark(event.matches);
    mediaQuery.addEventListener("change", handleChange);
    return () => mediaQuery.removeEventListener("change", handleChange);
  }, []);

  return (
    <div className="grid grid-cols-3 gap-2">
      {(["light", "dark", "system"] as const).map((theme) => (
        <button key={theme} type="button" onClick={() => onChange(theme)} className={`rounded-md border p-3 text-left text-sm ${value === theme ? "border-stone-900 ring-1 ring-stone-900" : "border-stone-200"}`}>
          <span className={`mb-2 block h-8 rounded ${theme === "dark" ? "bg-stone-800" : theme === "light" ? "bg-stone-100" : "bg-gradient-to-r from-stone-100 to-stone-800"}`} />
          <span className="font-medium capitalize">{theme}</span>
          {theme === "system" && <span className="mt-0.5 block text-xs text-stone-500">Currently {systemDark ? "dark" : "light"}</span>}
        </button>
      ))}
    </div>
  );
}
