import {
  useCallback,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

import Alert from "@mui/material/Alert";
import Snackbar from "@mui/material/Snackbar";

import {
  SnackbarContext,
  type SnackbarContextValue,
  type SnackbarOptions,
} from "./snackbar-context";

type ActiveSnackbar = SnackbarOptions & {
  key: number;
  open: boolean;
};

export function SnackbarProvider({ children }: { children: ReactNode }) {
  const [activeSnackbar, setActiveSnackbar] = useState<ActiveSnackbar | null>(null);
  const queueRef = useRef<SnackbarOptions[]>([]);

  const processNext = useCallback(() => {
    const next = queueRef.current.shift();
    if (next) {
      setActiveSnackbar({ ...next, key: Date.now(), open: true });
    } else {
      setActiveSnackbar(null);
    }
  }, []);

  const showSnackbar = useCallback(
    (options: SnackbarOptions) => {
      if (activeSnackbar) {
        queueRef.current.push(options);
        return;
      }
      setActiveSnackbar({ ...options, key: Date.now(), open: true });
    },
    [activeSnackbar],
  );

  const handleClose = useCallback((_event: unknown, reason?: string) => {
    if (reason === "clickaway") {
      return;
    }
    setActiveSnackbar((current) => (current ? { ...current, open: false } : current));
  }, []);

  const handleExited = useCallback(() => {
    processNext();
  }, [processNext]);

  const contextValue = useMemo<SnackbarContextValue>(() => ({
    showSnackbar,
    showSuccess: (message) => showSnackbar({ message, severity: "success" }),
    showError: (message) => showSnackbar({ message, severity: "error", durationMs: 6000 }),
    showInfo: (message) => showSnackbar({ message, severity: "info" }),
    showWarning: (message) => showSnackbar({ message, severity: "warning" }),
  }), [showSnackbar]);

  return (
    <SnackbarContext.Provider value={contextValue}>
      {children}
      <Snackbar
        key={activeSnackbar?.key}
        open={Boolean(activeSnackbar?.open)}
        autoHideDuration={activeSnackbar?.durationMs ?? 4000}
        onClose={handleClose}
        TransitionProps={{ onExited: handleExited }}
        anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
      >
        {activeSnackbar ? (
          <Alert
            elevation={6}
            variant="filled"
            severity={activeSnackbar.severity ?? "info"}
            onClose={() => handleClose(null)}
            sx={{ minWidth: 280 }}
          >
            {activeSnackbar.message}
          </Alert>
        ) : undefined}
      </Snackbar>
    </SnackbarContext.Provider>
  );
}
