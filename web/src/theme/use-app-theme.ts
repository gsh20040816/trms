import { useContext } from "react";

import { AppThemeContext } from "./app-theme-context";

export function useAppTheme() {
  const value = useContext(AppThemeContext);
  if (!value) {
    throw new Error("useAppTheme must be used within AppThemeProvider");
  }
  return value;
}
