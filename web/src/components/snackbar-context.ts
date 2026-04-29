import { createContext } from "react";

import type { AlertColor } from "@mui/material/Alert";

export type SnackbarSeverity = AlertColor;

export type SnackbarOptions = {
  message: string;
  severity?: SnackbarSeverity;
  durationMs?: number;
};

export type SnackbarContextValue = {
  showSnackbar: (options: SnackbarOptions) => void;
  showSuccess: (message: string) => void;
  showError: (message: string) => void;
  showInfo: (message: string) => void;
  showWarning: (message: string) => void;
};

export const SnackbarContext = createContext<SnackbarContextValue | null>(null);
