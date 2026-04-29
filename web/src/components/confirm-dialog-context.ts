import { createContext } from "react";

import type { AlertColor } from "@mui/material/Alert";

export type ConfirmDialogTone = AlertColor;

export type ConfirmDialogOptions = {
  title: string;
  description?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  tone?: ConfirmDialogTone;
  destructive?: boolean;
  requireTyping?: string;
};

export type ConfirmDialogContextValue = {
  confirm: (options: ConfirmDialogOptions) => Promise<boolean>;
};

export const ConfirmDialogContext = createContext<ConfirmDialogContextValue | null>(null);
