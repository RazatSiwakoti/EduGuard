import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

export type ThemeMode = "light" | "dark" | "system";

interface ThemeContextValue {
  theme: ThemeMode;
  isDark: boolean;
  setTheme: (t: ThemeMode) => void;
}

const ThemeContext = createContext<ThemeContextValue>({
  theme: "light",
  isDark: false,
  setTheme: () => {},
});

function resolveIsDark(theme: ThemeMode): boolean {
  if (theme === "dark") return true;
  if (theme === "light") return false;
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<ThemeMode>(() => {
    try {
      const saved = localStorage.getItem("edguard_theme") as ThemeMode | null;
      return saved ?? "light";
    } catch {
      return "light";
    }
  });

  const [isDark, setIsDark] = useState(() => resolveIsDark(
    (() => {
      try {
        return (localStorage.getItem("edguard_theme") as ThemeMode) ?? "light";
      } catch {
        return "light";
      }
    })()
  ));

  // Apply / remove .dark class on <html> and update isDark
  useEffect(() => {
    const apply = (t: ThemeMode) => {
      const dark = resolveIsDark(t);
      setIsDark(dark);
      document.documentElement.classList.toggle("dark", dark);
    };

    apply(theme);

    // Re-evaluate when system preference changes (only matters for "system" mode)
    if (theme === "system") {
      const mq = window.matchMedia("(prefers-color-scheme: dark)");
      const handler = () => apply(theme);
      mq.addEventListener("change", handler);
      return () => mq.removeEventListener("change", handler);
    }
  }, [theme]);

  const setTheme = (t: ThemeMode) => {
    setThemeState(t);
    try {
      localStorage.setItem("edguard_theme", t);
    } catch {}
  };

  return (
    <ThemeContext.Provider value={{ theme, isDark, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  return useContext(ThemeContext);
}
