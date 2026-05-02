import { useState } from "react";
import { Navigate } from "react-router-dom";

import Button from "@mui/material/Button";
import TextField from "@mui/material/TextField";

import { ApiErrorNotice } from "../components/ApiErrorNotice";
import { PageHeader, RoleWorkspace, SectionCard } from "../components/dashboard";
import { useSnackbar } from "../components/use-snackbar";
import { ApiError } from "../lib/api/client";
import { trmsApi } from "../lib/api/trms";
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
  const [loadError, setLoadError] = useState<unknown>(null);

  if (!session) {
    return <Navigate replace to={buildLoginPath("/profile")} />;
  }

  const canEditMemberCode = session.availableRoles.includes("member");

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
    </RoleWorkspace>
  );
}
