import { Link, Navigate, useLocation, useNavigate, useSearchParams } from "react-router-dom";

import { AdminTaskListPage } from "./admin-task-list";
import { RoleShell } from "../components/RoleShell";
import {
  buildLoginPath,
  clearMockSession,
  setMockSession,
  useAuthSession,
} from "./auth-store";
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

export function MockLoginPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const session = useAuthSession();
  const nextPath = normalizeNextPath(searchParams.get("next"));
  const activeRoleRoute = session ? getRoleRouteOrThrow(session.role) : null;

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
        <p className="eyebrow">Mock Auth</p>
        <h2>登录占位</h2>
        <p>
          当前前端未接入真实 OAuth 或账号体系，只提供本地 mock 角色会话，用于后续页面开发和权限可见性联调。
        </p>
        {nextPath ? (
          <p className="status-note">检测到未登录访问，原请求入口：{nextPath}</p>
        ) : (
          <p className="status-note">此页面只固化登录、切换角色和未登录拦截边界，不连接真实后端身份系统。</p>
        )}
      </section>
      <section className="card-grid" aria-label="mock 角色登录入口">
        {roleRoutes.map((roleRoute) => (
          <article key={roleRoute.role} className="route-card">
            <p className="card-kicker">{roleRoute.emphasis}</p>
            <h2>{roleRoute.loginLabel}</h2>
            <p>{roleRoute.summary}</p>
            <p className="role-card-meta">
              Mock 身份：{roleRoute.mockDisplayName}
              {roleRoute.mockMemberCode ? `（${roleRoute.mockMemberCode}）` : ""}
            </p>
            <button
              className="route-link"
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
      {activeRoleRoute && session ? (
        <section className="status-card">
          <p className="eyebrow">Current Session</p>
          <h2>当前已登录</h2>
          <p>
            已使用 {activeRoleRoute.loginLabel} 进入，当前身份为 {session.displayName}
            {session.memberCode ? `（${session.memberCode}）` : ""}。
          </p>
          <div className="inline-actions">
            <Link className="route-link" to={activeRoleRoute.path}>
              进入当前入口
            </Link>
            <button
              className="route-link route-link-secondary"
              type="button"
              onClick={() => {
                clearMockSession();
              }}
            >
              退出 mock 会话
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
          当前 mock 身份为 {currentRoleRoute.loginLabel} / {session.displayName}
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

  if (roleRoute.role === "admin") {
    return <AdminTaskListPage session={session} />;
  }

  return (
    <RoleShell
      emphasis={roleRoute.emphasis}
      title={roleRoute.title}
      summary={roleRoute.summary}
    >
      <p className="status-note">
        当前以 mock 身份 {session.displayName}
        {session.memberCode ? `（${session.memberCode}）` : ""} 进入。此页只固化登录态与角色入口边界，真实业务内容将在后续任务补齐。
      </p>
      <div className="inline-actions">
        <Link className="route-link" to="/">
          返回首页
        </Link>
        <Link className="route-link route-link-secondary" to="/login">
          切换 mock 身份
        </Link>
      </div>
    </RoleShell>
  );
}
