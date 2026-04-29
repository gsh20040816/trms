import { createContext } from "react";

import type { AppColorScheme } from "./m3-theme";

export type ColorSchemePreference = AppColorScheme | "system";

export type AppThemeContextValue = {
  colorScheme: AppColorScheme;
  preference: ColorSchemePreference;
  setPreference: (next: ColorSchemePreference) => void;
};

export const AppThemeContext = createContext<AppThemeContextValue | null>(null);
