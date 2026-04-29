import { useContext } from "react";

import { SnackbarContext } from "./snackbar-context";

export function useSnackbar() {
  const value = useContext(SnackbarContext);
  if (!value) {
    throw new Error("useSnackbar must be used within SnackbarProvider");
  }
  return value;
}
