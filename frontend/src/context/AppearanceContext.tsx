import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { toast } from "sonner";
import { updatePreferences } from "../services/authService";
import type { Preferences } from "../types/auth";
import { useAuth } from "./AuthContext";

const STORAGE_KEY = "eduguard:prefs";

const DEFAULT_PREFERENCES: Preferences = {
  theme: "system",
  font_size: "default",
  reduce_motion: false,
  high_contrast: false,
  colourblind_safe: false,
};

interface AppearanceContextType {
  preferences: Preferences;
  set: (partial: Partial<Preferences>) => void;
}

const AppearanceContext = createContext<AppearanceContextType | undefined>(
  undefined
);

function applyPreferences(preferences: Preferences) {
  const root = document.documentElement;
  const dark =
    preferences.theme === "dark" ||
    (preferences.theme !== "light" &&
      window.matchMedia("(prefers-color-scheme: dark)").matches);

  root.classList.toggle("dark", dark);
  root.classList.toggle("hc", preferences.high_contrast);
  root.classList.toggle("reduce-motion", preferences.reduce_motion);
  root.classList.toggle("cvd", preferences.colourblind_safe);
  root.dataset.fontSize = preferences.font_size;
}

function readCachedPreferences(): Preferences {
  try {
    const cached = JSON.parse(
      localStorage.getItem(STORAGE_KEY) || "{}"
    ) as Partial<Preferences>;
    return { ...DEFAULT_PREFERENCES, ...cached };
  } catch {
    return DEFAULT_PREFERENCES;
  }
}

export function AppearanceProvider({ children }: { children: ReactNode }) {
  const { user, applyUser } = useAuth();
  const [preferences, setPreferences] = useState(readCachedPreferences);

  useEffect(() => {
    applyPreferences(preferences);
  }, [preferences]);

  useEffect(() => {
    if (!user?.preferences) return;
    const serverPreferences = {
      ...DEFAULT_PREFERENCES,
      ...user.preferences,
    };
    queueMicrotask(() => {
      setPreferences(serverPreferences);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(serverPreferences));
      applyPreferences(serverPreferences);
    });
  }, [user?.preferences]);

  useEffect(() => {
    if (preferences.theme !== "system") return;

    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
    const handleChange = () => applyPreferences(preferences);
    mediaQuery.addEventListener("change", handleChange);
    return () => mediaQuery.removeEventListener("change", handleChange);
  }, [preferences]);

  const set = useCallback(
    (partial: Partial<Preferences>) => {
      const previous = preferences;
      const next = { ...previous, ...partial };
      setPreferences(next);
      applyPreferences(next);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next));

      void updatePreferences(partial)
        .then((updatedUser) => {
          applyUser(updatedUser);
        })
        .catch(() => {
          setPreferences(previous);
          applyPreferences(previous);
          localStorage.setItem(STORAGE_KEY, JSON.stringify(previous));
          toast.error("Could not save appearance settings.");
        });
    },
    [applyUser, preferences]
  );

  return (
    <AppearanceContext.Provider value={{ preferences, set }}>
      {children}
    </AppearanceContext.Provider>
  );
}

export function useAppearance() {
  const context = useContext(AppearanceContext);
  if (!context) {
    throw new Error("useAppearance must be used within an AppearanceProvider");
  }
  return context;
}
