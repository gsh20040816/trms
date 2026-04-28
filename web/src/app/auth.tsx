import { useState, type FormEvent } from "react";
import { Link, Navigate, Outlet, useLocation, useNavigate, useSearchParams } from "react-router-dom";

import { ApiErrorNotice } from "../components/ApiErrorNotice";
import { RoleShell } from "../components/RoleShell";
import {
  buildLoginPath,
  clearMockSession,
  loginWithPassword,
  logoutCurrentSession,
  registerWithPassword,
  setMockSession,
  useAuthSession,
} from "./auth-store";
import { resolveAuthUiConfig, type AuthUiConfig } from "./auth-ui-config";
import {
  findRoleRouteByRole,
  roleRoutes,
  type RoleRouteConfig,
  type UserRole,
} from "./role-routes";

function getRoleRouteOrThrow(role: UserRole) {
  const roleRoute = findRoleRouteByRole(role);
  if (!roleRoute) {
    throw new Error(`Unknown role route: ${role}`);
  }
  return roleRoute;
}

function normalizeNextPath(rawPath: string | null) {
  if (!rawPath || !rawPath.startsWith("/")) {
    return null;
  }
  return rawPath;
}

export function MockLoginPage({ uiConfig = resolveAuthUiConfig() }: { uiConfig?: AuthUiConfig }) {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const session = useAuthSession();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<UserRole>("member");
  const [displayName, setDisplayName] = useState("");
  const [actorId, setActorId] = useState("");
  const [memberCode, setMemberCode] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const nextPath = normalizeNextPath(searchParams.get("next"));
  const activeRoleRoute = session ? getRoleRouteOrThrow(session.role) : null;
  const registrationRoleRoutes = uiConfig.allowPrivilegedSelfRegistration
    ? roleRoutes
    : roleRoutes.filter((roleRoute) => roleRoute.role === "member");

  function handleCredentialSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    void (async () => {
      try {
        const nextSession = mode === "login"
          ? await loginWithPassword({ username, password })
          : await registerWithPassword({
            username,
            password,
            role,
            displayName,
            actorId,
            memberCode,
          });
        const targetRoleRoute = getRoleRouteOrThrow(nextSession.role);
        void navigate(nextPath ?? targetRoleRoute.path, {
          replace: true,
        });
      } catch (submitError) {
        setError(submitError);
      } finally {
        setIsSubmitting(false);
      }
    })();
  }

  function handleLogin(role: UserRole) {
    const targetRoleRoute = getRoleRouteOrThrow(role);
    setMockSession(role);
    void navigate(nextPath ?? targetRoleRoute.path, {
      replace: true,
    });
  }

  return (
    <div className="page-stack">
      <section className="status-card auth-panel">
        <p className="eyebrow">Account Auth</p>
        <h2>账号登录与注册</h2>
        <p>
          当前已接入后端用户名密码账号体系。注册或登录成功后，前端保存后端返回的 bearer token 和用户身份，并继续复用既有成员、管理员、系统管理员入口。
        </p>
        {nextPath ? (
          <p className="status-note">检测到未登录访问，原请求入口：{nextPath}</p>
        ) : (
          <p className="status-note">第一阶段仍保留页面级角色路由门禁；业务 API 的强制 token 权限收口会在后续权限任务继续推进。</p>
        )}
      </section>
      <section className="status-card auth-panel" aria-label="账号登录注册表单">
        <div className="inline-actions">
          <button
            className={mode === "login" ? "route-link" : "route-link route-link-secondary"}
            type="button"
            onClick={() => {
              setMode("login");
              setError(null);
            }}
          >
            登录
          </button>
          <button
            className={mode === "register" ? "route-link" : "route-link route-link-secondary"}
            type="button"
            onClick={() => {
              setMode("register");
              setError(null);
            }}
          >
            注册
          </button>
        </div>
        <form className="form-grid" onSubmit={handleCredentialSubmit}>
          <label className="field-stack">
            <span>用户名</span>
            <input
              autoComplete="username"
              minLength={3}
              name="username"
              required
              value={username}
              onChange={(event) => {
                setUsername(event.target.value);
              }}
            />
          </label>
          <label className="field-stack">
            <span>密码</span>
            <input
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              minLength={8}
              name="password"
              required
              type="password"
              value={password}
              onChange={(event) => {
                setPassword(event.target.value);
              }}
            />
          </label>
          {mode === "register" ? (
            <>
              {uiConfig.allowPrivilegedSelfRegistration ? (
                <label className="field-stack">
                  <span>角色</span>
                  <select
                    name="role"
                    value={role}
                    onChange={(event) => {
                      setRole(event.target.value as UserRole);
                    }}
                  >
                    {registrationRoleRoutes.map((roleRoute) => (
                      <option key={roleRoute.role} value={roleRoute.role}>
                        {roleRoute.loginLabel}
                      </option>
                    ))}
                  </select>
                </label>
              ) : (
                <p className="status-note">
                  当前环境仅开放成员自注册；管理员与系统管理员账号必须通过受控初始化或后续邀请/审批流程创建。
                </p>
              )}
              <label className="field-stack">
                <span>显示名称</span>
                <input
                  name="display_name"
                  value={displayName}
                  onChange={(event) => {
                    setDisplayName(event.target.value);
                  }}
                />
              </label>
              <label className="field-stack">
                <span>业务身份 ID</span>
                <input
                  name="actor_id"
                  placeholder={role === "member" ? "成员学号，例如 2250001" : "管理员 ID，例如 admin-1"}
                  value={actorId}
                  onChange={(event) => {
                    setActorId(event.target.value);
                  }}
                />
              </label>
              <label className="field-stack">
                <span>成员编号</span>
                <input
                  disabled={role !== "member"}
                  name="member_code"
                  placeholder="仅成员账号需要"
                  value={memberCode}
                  onChange={(event) => {
                    setMemberCode(event.target.value);
                  }}
                />
              </label>
            </>
          ) : null}
          <div className="form-actions">
            <button className="route-link" disabled={isSubmitting} type="submit">
              {isSubmitting ? "提交中..." : mode === "login" ? "登录" : "注册并登录"}
            </button>
          </div>
        </form>
      </section>
      {error ? <ApiErrorNotice error={error} /> : null}
      {uiConfig.enableDevRoleEntries ? (
        <section className="card-grid" aria-label="开发调试角色入口">
          {roleRoutes.map((roleRoute) => (
            <article key={roleRoute.role} className="route-card">
              <p className="card-kicker">{roleRoute.emphasis}</p>
              <h2>{roleRoute.loginLabel}</h2>
              <p>{roleRoute.summary}</p>
              <p className="role-card-meta">
                开发调试身份：{roleRoute.mockDisplayName}
                {roleRoute.mockMemberCode ? `（${roleRoute.mockMemberCode}）` : ""}
              </p>
              <button
                className="route-link route-link-secondary"
                type="button"
                onClick={() => {
                  handleLogin(roleRoute.role);
                }}
              >
                以{roleRoute.loginLabel}进入
              </button>
            </article>
          ))}
        </section>
      ) : null}
      {activeRoleRoute && session ? (
        <section className="status-card">
          <p className="eyebrow">Current Session</p>
          <h2>当前已登录</h2>
          <p>
            已使用 {activeRoleRoute.loginLabel} 进入，当前身份为 {session.displayName}
            {session.memberCode ? `（${session.memberCode}）` : ""}。
          </p>
          <p className="status-note">
            {session.isMock
              ? "当前是开发调试会话，没有后端 token。"
              : `当前账号：${session.username ?? session.actorId}，已保存后端 bearer token。`}
          </p>
          <div className="inline-actions">
            <Link className="route-link" to={activeRoleRoute.path}>
              进入当前入口
            </Link>
            <button
              className="route-link route-link-secondary"
              type="button"
              onClick={() => {
                void (session.isMock ? Promise.resolve(clearMockSession()) : logoutCurrentSession()).catch((logoutError: unknown) => {
                  setError(logoutError);
                });
              }}
            >
              退出当前会话
            </button>
          </div>
        </section>
      ) : null}
    </div>
  );
}

export function ProtectedRoleRoute({ roleRoute }: { roleRoute: RoleRouteConfig }) {
  const session = useAuthSession();
  const location = useLocation();

  if (!session) {
    return (
      <Navigate
        replace
        to={buildLoginPath(`${location.pathname}${location.search}`)}
      />
    );
  }

  if (session.role !== roleRoute.role) {
    const currentRoleRoute = getRoleRouteOrThrow(session.role);
    return (
      <RoleShell
        emphasis="角色错配"
        title={`${roleRoute.title} 暂不可访问`}
        summary={`当前登录身份不匹配；此入口仅允许${roleRoute.loginLabel}访问。`}
      >
        <p className="status-note">
          当前身份为 {currentRoleRoute.loginLabel} / {session.displayName}
          {session.memberCode ? `（${session.memberCode}）` : ""}。
        </p>
        <div className="inline-actions">
          <Link className="route-link" to={currentRoleRoute.path}>
            进入我的入口
          </Link>
          <Link className="route-link route-link-secondary" to="/">
            返回首页
          </Link>
        </div>
      </RoleShell>
    );
  }

  if (roleRoute.role === "admin" || roleRoute.role === "member") {
    return <Outlet />;
  }

  return (
    <RoleShell
      emphasis={roleRoute.emphasis}
      title={roleRoute.title}
      summary={roleRoute.summary}
    >
      <p className="status-note">
        当前以身份 {session.displayName}
        {session.memberCode ? `（${session.memberCode}）` : ""} 进入。此页只固化登录态与角色入口边界，真实业务内容将在后续任务补齐。
      </p>
      <div className="inline-actions">
        <Link className="route-link" to="/">
          返回首页
        </Link>
        <Link className="route-link route-link-secondary" to="/login">
          切换登录身份
        </Link>
      </div>
    </RoleShell>
  );
}
