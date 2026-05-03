import { useEffect, useState } from "react";
import { Navigate, useSearchParams } from "react-router-dom";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import CircularProgress from "@mui/material/CircularProgress";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import { useSnackbar } from "../components/use-snackbar";
import { ApiError } from "../lib/api/client";
import { summarizeUnknownError } from "../lib/api/errors";
import { trmsApi } from "../lib/api/trms";
import type { TelegramBindingAuthorizationView } from "../lib/api/types";
import { buildLoginPath, useAuthSession } from "./auth-store";

function describeError(error: unknown) {
  if (error instanceof ApiError) {
    return error.summary.message;
  }
  return summarizeUnknownError(error).message;
}

export function TelegramBindingPage() {
  const [searchParams] = useSearchParams();
  const session = useAuthSession();
  const { showError, showSuccess } = useSnackbar();
  const token = searchParams.get("token")?.trim() ?? "";
  const missingToken = token.length === 0;
  const [authorization, setAuthorization] = useState<TelegramBindingAuthorizationView | null>(null);
  const [loadError, setLoadError] = useState<string | null>(missingToken ? "绑定链接缺少 token。" : null);
  const [confirmError, setConfirmError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(!missingToken);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isBound, setIsBound] = useState(false);

  useEffect(() => {
    if (missingToken) {
      return;
    }
    let isCancelled = false;
    void trmsApi.getTelegramBindingAuthorization(token)
      .then((response) => {
        if (isCancelled) {
          return;
        }
        setAuthorization(response.item);
        setLoadError(null);
      })
      .catch((error) => {
        if (isCancelled) {
          return;
        }
        const message = describeError(error);
        setLoadError(message);
      })
      .finally(() => {
        if (!isCancelled) {
          setIsLoading(false);
        }
      });
    return () => {
      isCancelled = true;
    };
  }, [missingToken, token]);

  if (!session) {
    const search = new URLSearchParams({ token });
    return <Navigate to={buildLoginPath(`/telegram/bind?${search.toString()}`)} replace />;
  }

  async function handleConfirmBinding() {
    if (!token) {
      return;
    }
    setConfirmError(null);
    setIsSubmitting(true);
    try {
      await trmsApi.confirmTelegramBindingAuthorization(token);
      setIsBound(true);
      showSuccess("Telegram 账号绑定成功。");
    } catch (error) {
      const message = describeError(error);
      setConfirmError(message);
      showError(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Stack spacing={3} sx={{ maxWidth: 720, mx: "auto" }}>
      <Box>
        <Typography variant="overline" color="text.secondary">
          Telegram 绑定
        </Typography>
        <Typography variant="h4" component="h1" sx={{ mt: 0.5 }}>
          绑定 Telegram 账号
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mt: 1 }}>
          当前登录账号确认后，这个 Telegram 账号就可以直接查看任务、切换当前任务并发送发票文件。
        </Typography>
      </Box>

      <Card>
        <CardContent>
          {isLoading ? (
            <Stack direction="row" spacing={1.5} alignItems="center">
              <CircularProgress size={20} />
              <Typography>正在读取绑定请求...</Typography>
            </Stack>
          ) : null}
          {!isLoading && loadError ? (
            <Alert severity="error">{loadError}</Alert>
          ) : null}
          {!isLoading && !loadError && authorization ? (
            <Stack spacing={2}>
              <Alert severity="info">
                待绑定 Telegram 账号：
                {authorization.telegram_username
                  ? `@${authorization.telegram_username}`
                  : `用户 ${authorization.telegram_user_id}`}
              </Alert>
              <Typography variant="body2" color="text.secondary">
                绑定后，该 Telegram 账号会映射到当前登录身份
                {session.displayName ? `“${session.displayName}”` : ""}
                ，并共享成员可见任务范围。
              </Typography>
              {authorization.status === "expired" ? (
                <Alert severity="warning">这个绑定链接已过期，请回到 Telegram 重新发送 /bind。</Alert>
              ) : null}
              {authorization.status === "consumed" || isBound ? (
                <Alert severity="success">这个 Telegram 账号已经绑定完成，可以回到 Telegram 继续操作。</Alert>
              ) : null}
              {confirmError ? <Alert severity="error">{confirmError}</Alert> : null}
              <Box sx={{ display: "flex", justifyContent: "flex-end" }}>
                <Button
                  variant="contained"
                  onClick={() => void handleConfirmBinding()}
                  disabled={
                    isSubmitting
                    || authorization.status !== "pending"
                    || isBound
                  }
                >
                  {isSubmitting ? "绑定中..." : "确认绑定当前账号"}
                </Button>
              </Box>
            </Stack>
          ) : null}
        </CardContent>
      </Card>
    </Stack>
  );
}
