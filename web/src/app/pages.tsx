import { Link, Outlet, useLocation } from "react-router-dom";

import { buildLoginPath, clearMockSession, logoutCurrentSession, useAuthSession } from "./auth-store";
import { roleRoutes, type UserRole } from "./role-routes";
import { PageHeader, RoleWorkspace, SectionCard, StatCard, StatusBadge } from "../components/dashboard";
import { formatRole, formatWorkspace } from "../lib/ui-text";

type RoleOverview = {
  role: UserRole;
  title: string;
  summary: string;
  actions: string[];
};

const ROLE_OVERVIEWS: RoleOverview[] = [
  {
    role: "member",
    title: "报销成员",
    summary: "查看我参与的任务、补充材料、确认个人费用，不再先读技术说明。",
    actions: ["查看我的任务", "提交或补充材料", "确认个人费用"],
  },
  {
    role: "admin",
    title: "管理员",
    summary: "以任务推进为中心，优先处理缺失材料、待确认费用和导出准备。",
    actions: ["创建任务", "处理缺失材料", "复核与导出"],
  },
  {
    role: "system_admin",
    title: "系统管理员",
    summary: "集中处理用户角色、全局配置、系统状态与审计记录。",
    actions: ["管理用户角色", "维护全局配置", "查看系统状态"],
  },
];

function isRouteActive(pathname: string, targetPath: string) {
  if (targetPath === "/") {
    return pathname === "/";
  }
  return pathname === targetPath || pathname.startsWith(`${targetPath}/`);
}

function getActiveOverview(role: UserRole) {
  return ROLE_OVERVIEWS.find((item) => item.role === role) ?? null;
}

export function RootLayout() {
  const location = useLocation();
  const session = useAuthSession();

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="topbar-inner">
          <Link className="brand-mark" to="/">
            TRMS
          </Link>
          <nav className="topbar-nav" aria-label="主导航">
            <Link className={`topbar-link${location.pathname === "/" ? " topbar-link-active" : ""}`} to="/">
              总览
            </Link>
            {roleRoutes.map((roleRoute) => (
              <Link
                key={roleRoute.path}
                className={`topbar-link${isRouteActive(location.pathname, roleRoute.path) ? " topbar-link-active" : ""}`}
                to={session ? roleRoute.path : buildLoginPath(roleRoute.path)}
              >
                {roleRoute.title}
              </Link>
            ))}
          </nav>
          <div className="topbar-session">
            {session ? (
              <>
                <StatusBadge tone="info">{formatRole(session.role)}</StatusBadge>
                <span className="session-text">
                  {session.displayName}
                  {session.memberCode ? `（${session.memberCode}）` : ""}
                </span>
                <button
                  className="button button-secondary"
                  type="button"
                  onClick={() => {
                    if (session.isMock) {
                      clearMockSession();
                      return;
                    }
                    void logoutCurrentSession();
                  }}
                >
                  退出登录
                </button>
              </>
            ) : (
              <Link className="button button-primary" to="/login">
                登录
              </Link>
            )}
          </div>
        </div>
      </header>

      <main className="page-content">
        <Outlet />
      </main>
    </div>
  );
}
export function HomePage() {
  const session = useAuthSession();
  const currentOverview = session ? getActiveOverview(session.role) : null;

  return (
    <RoleWorkspace
      header={(
        <PageHeader
          eyebrow="报销任务总览"
          title="Tongji ACM 报销管理系统"
          description="选择你的工作台后，页面会直接展示待处理事项、任务状态和下一步操作。普通业务界面不再显示技术实现信息。"
          meta={session ? `当前身份：${formatWorkspace(session.role)}` : "当前未登录"}
          actions={(
            <div className="page-actions">
              <Link className="button button-primary" to={session ? roleRoutes.find((item) => item.role === session.role)?.path ?? "/login" : "/login"}>
                {session ? "进入我的工作台" : "登录并进入工作台"}
              </Link>
            </div>
          )}
        />
      )}
      summary={(
        <section className="stat-grid" aria-label="系统概览">
          <StatCard label="成员入口" value="材料与确认" description="面向成员的任务、材料、费用确认入口。" />
          <StatCard label="管理员入口" value="任务优先" description="以任务处理、复核、导出为核心的后台工作区。" />
          <StatCard label="系统管理" value="配置与巡检" description="技术诊断信息只保留在系统管理场景。" />
        </section>
      )}
    >
      {currentOverview ? (
        <SectionCard
          title={currentOverview.title}
          description={currentOverview.summary}
          action={<StatusBadge tone="success">当前身份</StatusBadge>}
        >
          <ul className="action-list" aria-label="当前身份推荐操作">
            {currentOverview.actions.map((action) => (
              <li key={action}>{action}</li>
            ))}
          </ul>
        </SectionCard>
      ) : null}

      <section className="feature-grid" aria-label="角色入口">
        {roleRoutes.map((roleRoute) => {
          const overview = getActiveOverview(roleRoute.role);
          return (
            <SectionCard
              key={roleRoute.path}
              title={overview?.title ?? roleRoute.title}
              description={overview?.summary ?? roleRoute.summary}
              action={(
                <Link className="button button-secondary" to={session ? roleRoute.path : buildLoginPath(roleRoute.path)}>
                  {session && session.role === roleRoute.role ? "进入工作台" : "查看入口"}
                </Link>
              )}
            >
              <ul className="action-list" aria-label={`${roleRoute.title} 操作入口`}>
                {(overview?.actions ?? []).map((action) => (
                  <li key={`${roleRoute.role}:${action}`}>{action}</li>
                ))}
              </ul>
            </SectionCard>
          );
        })}
      </section>
    </RoleWorkspace>
  );
}

export function NotFoundPage() {
  return (
    <SectionCard
      title="未找到页面"
      description="请返回总览页重新选择工作台或操作入口。"
      action={(
        <Link className="button button-primary" to="/">
          返回总览
        </Link>
      )}
    />
  );
}
