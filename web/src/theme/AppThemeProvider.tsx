import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";

import CssBaseline from "@mui/material/CssBaseline";
import { ThemeProvider } from "@mui/material/styles";
import useMediaQuery from "@mui/material/useMediaQuery";

import { AppThemeContext, type ColorSchemePreference } from "./app-theme-context";
import { darkTheme, lightTheme, type AppColorScheme } from "./m3-theme";

const STORAGE_KEY = "trms.color-scheme";

function readPreference(): ColorSchemePreference {
  if (typeof window === "undefined") {
    return "system";
  }
  try {
    const stored = window.localStorage?.getItem(STORAGE_KEY);
    if (stored === "light" || stored === "dark" || stored === "system") {
      return stored;
    }
  } catch {
    // ignore storage failures
  }
  return "system";
}

function persistPreference(next: ColorSchemePreference) {
  if (typeof window === "undefined") {
    return;
  }
  try {
    if (next === "system") {
      window.localStorage?.removeItem(STORAGE_KEY);
    } else {
      window.localStorage?.setItem(STORAGE_KEY, next);
    }
  } catch {
    // ignore storage failures
  }
}

export function AppThemeProvider({ children }: { children: ReactNode }) {
  const [preference, setPreferenceState] = useState<ColorSchemePreference>(() => readPreference());
  const prefersDark = useMediaQuery("(prefers-color-scheme: dark)");

  const colorScheme: AppColorScheme = useMemo(() => {
    if (preference === "light" || preference === "dark") {
      return preference;
    }
    return prefersDark ? "dark" : "light";
  }, [preference, prefersDark]);

  const setPreference = useCallback((next: ColorSchemePreference) => {
    setPreferenceState(next);
    persistPreference(next);
  }, []);

  useEffect(() => {
    if (typeof document !== "undefined") {
      document.documentElement.dataset.colorScheme = colorScheme;
    }
  }, [colorScheme]);

  const contextValue = useMemo(
    () => ({ colorScheme, preference, setPreference }),
    [colorScheme, preference, setPreference],
  );

  const activeTheme = colorScheme === "dark" ? darkTheme : lightTheme;

  return (
    <AppThemeContext.Provider value={contextValue}>
      <ThemeProvider theme={activeTheme}>
        <CssBaseline enableColorScheme />
        {children}
      </ThemeProvider>
    </AppThemeContext.Provider>
  );
}
