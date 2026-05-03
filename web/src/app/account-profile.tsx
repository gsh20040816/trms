import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemText from "@mui/material/ListItemText";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";

import { ApiErrorNotice } from "../components/ApiErrorNotice";
import { PageHeader, RoleWorkspace, SectionCard } from "../components/dashboard";
import { useSnackbar } from "../components/use-snackbar";
import { ApiError } from "../lib/api/client";
import { trmsApi } from "../lib/api/trms";
import type { EmailBindingRecord } from "../lib/api/types";
import { formatUserIdentityLabel } from "../lib/ui-text";
import {
  buildLoginPath,
  updateCurrentSessionUser,
  useAuthSession,
} from "./auth-store";

export function AccountProfilePage() {
  const session = useAuthSession();
  const { showError, showSuccess } = useSnackbar();
  const [displayName, setDisplayName] = useState(session?.displayName ?? "");
  const [memberCode, setMemberCode] = useState(session?.memberCode ?? "");
  const [saving, setSaving] = useState(false);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [savingPassword, setSavingPassword] = useState(false);
  const [loadError, setLoadError] = useState<unknown>(null);
  const [emailBindings, setEmailBindings] = useState<EmailBindingRecord[]>([]);
  const [bindingEmail, setBindingEmail] = useState("");
  const [bindingCode, setBindingCode] = useState("");
  const [requestedBindingEmail, setRequestedBindingEmail] = useState("");
  const [sendingBindingCode, setSendingBindingCode] = useState(false);
  const [verifyingBindingCode, setVerifyingBindingCode] = useState(false);

  const canManageEmailBindings = session?.availableRoles.includes("member") ?? false;

  useEffect(() => {
    if (!canManageEmailBindings) {
      return;
    }

    let cancelled = false;
    trmsApi.listEmailBindings()
      .then((response) => {
        if (!cancelled) {
          setEmailBindings(response.items);
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setLoadError(error);
          showError(error instanceof ApiError ? error.summary.message : "邮箱绑定列表读取失败。");
        }
      });

    return () => {
      cancelled = true;
    };
  }, [canManageEmailBindings, showError]);

  if (!session) {
    return <Navigate replace to={buildLoginPath("/profile")} />;
  }

  const canEditMemberCode = canManageEmailBindings;

  async function handleSave() {
    setLoadError(null);
    setSaving(true);
    try {
      const updatedUser = await trmsApi.updateCurrentUser({
        display_name: displayName,
        ...(canEditMemberCode ? { member_code: memberCode } : {}),
      });
      updateCurrentSessionUser(updatedUser);
      setDisplayName(updatedUser.display_name);
      setMemberCode(updatedUser.member_code ?? "");
      showSuccess("个人信息已保存。");
    } catch (error) {
      setLoadError(error);
      showError(error instanceof ApiError ? error.summary.message : "个人信息保存失败。");
    } finally {
      setSaving(false);
    }
  }

  async function handlePasswordSave() {
    if (newPassword !== confirmPassword) {
      showError("两次输入的新密码不一致。");
      return;
    }

    setLoadError(null);
    setSavingPassword(true);
    try {
      await trmsApi.updateCurrentUserPassword({
        current_password: currentPassword,
        new_password: newPassword,
      });
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      showSuccess("密码已更新。");
    } catch (error) {
      setLoadError(error);
      showError(error instanceof ApiError ? error.summary.message : "密码修改失败。");
    } finally {
      setSavingPassword(false);
    }
  }

  async function handleSendBindingCode() {
    const normalizedEmail = bindingEmail.trim().toLowerCase();
    if (!normalizedEmail) {
      showError("请先填写要绑定的邮箱地址。");
      return;
    }

    setLoadError(null);
    setSendingBindingCode(true);
    try {
      const response = await trmsApi.requestEmailBindingVerificationCode({ email: normalizedEmail });
      setBindingEmail(response.item.email);
      setRequestedBindingEmail(response.item.email);
      setBindingCode("");
      showSuccess("验证码已发送，请查看邮箱。");
    } catch (error) {
      setLoadError(error);
      showError(error instanceof ApiError ? error.summary.message : "验证码发送失败。");
    } finally {
      setSendingBindingCode(false);
    }
  }

  async function handleVerifyBindingCode() {
    const normalizedEmail = (requestedBindingEmail || bindingEmail).trim().toLowerCase();
    const normalizedCode = bindingCode.trim();
    if (!normalizedEmail) {
      showError("请先发送邮箱验证码。");
      return;
    }
    if (!normalizedCode) {
      showError("请填写邮箱验证码。");
      return;
    }

    setLoadError(null);
    setVerifyingBindingCode(true);
    try {
      const response = await trmsApi.verifyEmailBinding({
        email: normalizedEmail,
        code: normalizedCode,
      });
      setEmailBindings((current) => {
        const rest = current.filter((item) => item.id !== response.item.id && item.email !== response.item.email);
        return [...rest, response.item].sort((left, right) => left.email.localeCompare(right.email));
      });
      setBindingEmail("");
      setBindingCode("");
      setRequestedBindingEmail("");
      showSuccess("邮箱已绑定。");
    } catch (error) {
      setLoadError(error);
      showError(error instanceof ApiError ? error.summary.message : "邮箱绑定失败。");
    } finally {
      setVerifyingBindingCode(false);
    }
  }

  return (
    <RoleWorkspace
      header={(
        <PageHeader
          eyebrow="账号设置"
          title="个人信息"
          description="在这里维护当前账号的基础资料；成员账号可同步维护学号。"
        />
      )}
    >
      {loadError ? <ApiErrorNotice error={loadError} /> : null}

      <SectionCard title="当前账号" description="这些字段来自当前 bearer 会话。">
        <dl className="task-meta-grid member-status-meta-grid">
          <div><dt>当前身份</dt><dd>{formatUserIdentityLabel(session)}</dd></div>
          <div><dt>用户名</dt><dd>{session.username ?? "未提供"}</dd></div>
          <div><dt>可切换角色</dt><dd>{session.availableRoles.join(" / ")}</dd></div>
          <div><dt>业务标识</dt><dd>{session.actorId}</dd></div>
        </dl>
      </SectionCard>

      <SectionCard title="资料维护" description="保存后会同步刷新当前前端会话中的显示名称与学号。">
        <div className="admin-form-grid">
          <TextField
            label="显示名称"
            value={displayName}
            onChange={(event) => setDisplayName(event.target.value)}
            disabled={saving}
            required
          />
          {canEditMemberCode ? (
            <TextField
              label="学号"
              value={memberCode}
              onChange={(event) => setMemberCode(event.target.value)}
              disabled={saving}
              required
            />
          ) : null}
        </div>
        <div className="inline-actions">
          <Button type="button" variant="contained" disabled={saving} onClick={() => { void handleSave(); }}>
            {saving ? "保存中..." : "保存个人信息"}
          </Button>
        </div>
      </SectionCard>

      {canManageEmailBindings ? (
        <SectionCard
          title="绑定邮箱"
          description="可绑定多个邮箱；绑定后，这些邮箱都可按任务提交标识提交报销材料。"
        >
          {emailBindings.length > 0 ? (
            <List dense aria-label="已绑定邮箱列表" sx={{ py: 0, mb: 2 }}>
              {emailBindings.map((binding) => (
                <ListItem key={binding.id} disableGutters>
                  <ListItemText primary={binding.email} secondary="可作为邮件材料提交的发件地址" />
                </ListItem>
              ))}
            </List>
          ) : (
            <Alert severity="info" sx={{ mb: 2 }}>
              当前还没有绑定邮箱。
            </Alert>
          )}
          <Stack spacing={2}>
            <div className="admin-form-grid">
              <TextField
                label="邮箱地址"
                type="email"
                value={bindingEmail}
                onChange={(event) => setBindingEmail(event.target.value)}
                disabled={sendingBindingCode || verifyingBindingCode}
                required
                slotProps={{ htmlInput: { "aria-label": "邮箱地址" } }}
              />
              <TextField
                label="验证码"
                value={bindingCode}
                onChange={(event) => setBindingCode(event.target.value)}
                disabled={verifyingBindingCode || !requestedBindingEmail}
                helperText={requestedBindingEmail ? `验证码已发送至 ${requestedBindingEmail}` : "先发送验证码，再填写邮件中的 6 位数字。"}
                required
                slotProps={{ htmlInput: { "aria-label": "验证码" } }}
              />
            </div>
            <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} alignItems={{ xs: "stretch", sm: "center" }}>
              <Button
                type="button"
                variant="outlined"
                disabled={sendingBindingCode || verifyingBindingCode}
                onClick={() => { void handleSendBindingCode(); }}
              >
                {sendingBindingCode ? "发送中..." : "发送验证码"}
              </Button>
              <Button
                type="button"
                variant="contained"
                disabled={verifyingBindingCode || !requestedBindingEmail}
                onClick={() => { void handleVerifyBindingCode(); }}
              >
                {verifyingBindingCode ? "绑定中..." : "完成绑定"}
              </Button>
            </Stack>
          </Stack>
        </SectionCard>
      ) : null}

      <SectionCard title="密码修改" description="修改密码时必须先输入当前密码；用户名仍保持只读。">
        <div className="admin-form-grid">
          <TextField
            label="当前密码"
            type="password"
            value={currentPassword}
            onChange={(event) => setCurrentPassword(event.target.value)}
            disabled={savingPassword}
            required
            slotProps={{ htmlInput: { "aria-label": "当前密码" } }}
          />
          <TextField
            label="新密码"
            type="password"
            value={newPassword}
            onChange={(event) => setNewPassword(event.target.value)}
            disabled={savingPassword}
            helperText="至少 8 位。"
            required
            slotProps={{ htmlInput: { "aria-label": "新密码" } }}
          />
          <TextField
            label="确认新密码"
            type="password"
            value={confirmPassword}
            onChange={(event) => setConfirmPassword(event.target.value)}
            disabled={savingPassword}
            required
            slotProps={{ htmlInput: { "aria-label": "确认新密码" } }}
          />
        </div>
        <div className="inline-actions">
          <Button
            type="button"
            variant="contained"
            disabled={savingPassword}
            onClick={() => { void handlePasswordSave(); }}
          >
            {savingPassword ? "修改中..." : "修改密码"}
          </Button>
        </div>
      </SectionCard>
    </RoleWorkspace>
  );
}
