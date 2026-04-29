import { useCallback, useMemo, useRef, useState, type ReactNode } from "react";

import WarningAmberIcon from "@mui/icons-material/WarningAmber";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

import {
  ConfirmDialogContext,
  type ConfirmDialogContextValue,
  type ConfirmDialogOptions,
} from "./confirm-dialog-context";

type ActiveConfirmation = {
  options: ConfirmDialogOptions;
  resolve: (decision: boolean) => void;
};

export function ConfirmDialogProvider({ children }: { children: ReactNode }) {
  const [active, setActive] = useState<ActiveConfirmation | null>(null);
  const [typedValue, setTypedValue] = useState("");
  const pendingResolveRef = useRef<ActiveConfirmation["resolve"] | null>(null);

  const close = useCallback((decision: boolean) => {
    if (pendingResolveRef.current) {
      pendingResolveRef.current(decision);
      pendingResolveRef.current = null;
    }
    setActive(null);
    setTypedValue("");
  }, []);

  const confirm = useCallback(
    (options: ConfirmDialogOptions) => {
      return new Promise<boolean>((resolve) => {
        pendingResolveRef.current = resolve;
        setTypedValue("");
        setActive({ options, resolve });
      });
    },
    [],
  );

  const contextValue = useMemo<ConfirmDialogContextValue>(() => ({ confirm }), [confirm]);

  const options = active?.options;
  const tone = options?.tone ?? (options?.destructive ? "error" : "warning");
  const requireTyping = options?.requireTyping ?? null;
  const isTypeMatched = requireTyping ? typedValue.trim() === requireTyping : true;

  return (
    <ConfirmDialogContext.Provider value={contextValue}>
      {children}
      <Dialog
        open={Boolean(active)}
        onClose={() => close(false)}
        aria-labelledby="confirm-dialog-title"
        aria-describedby="confirm-dialog-description"
        slotProps={{ paper: { sx: { borderRadius: 4 } } }}
        maxWidth="xs"
        fullWidth
      >
        <DialogTitle
          id="confirm-dialog-title"
          sx={{ display: "flex", alignItems: "center", gap: 1.5, pb: 1 }}
        >
          <Box
            component="span"
            sx={{
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              width: 32,
              height: 32,
              borderRadius: 2,
              bgcolor: tone === "error" ? "error.main" : tone === "info" ? "info.main" : "warning.main",
              color: "common.white",
            }}
          >
            <WarningAmberIcon fontSize="small" />
          </Box>
          <Typography component="span" variant="h6" sx={{ fontWeight: 700 }}>
            {options?.title ?? ""}
          </Typography>
        </DialogTitle>
        <DialogContent id="confirm-dialog-description">
          <Stack spacing={1.5}>
            {options?.description ? (
              <Typography variant="body2" color="text.secondary">
                {options.description}
              </Typography>
            ) : null}
            {options?.destructive ? (
              <Alert severity="warning" variant="outlined">
                这是一个不可逆操作。请在确认前阅读上方说明。
              </Alert>
            ) : null}
            {requireTyping ? (
              <Box>
                <Typography variant="body2" sx={{ mb: 1 }}>
                  请输入 <strong>{requireTyping}</strong> 以确认：
                </Typography>
                <TextField
                  size="small"
                  fullWidth
                  autoFocus
                  value={typedValue}
                  onChange={(event) => setTypedValue(event.target.value)}
                  inputProps={{ "aria-label": "确认动作输入框" }}
                />
              </Box>
            ) : null}
          </Stack>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => close(false)} variant="text">
            {options?.cancelLabel ?? "取消"}
          </Button>
          <Button
            onClick={() => close(true)}
            variant="contained"
            color={options?.destructive ? "error" : "primary"}
            disabled={!isTypeMatched}
          >
            {options?.confirmLabel ?? "确认"}
          </Button>
        </DialogActions>
      </Dialog>
    </ConfirmDialogContext.Provider>
  );
}
