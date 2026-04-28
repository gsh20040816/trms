import { Link, Outlet, useLocation } from "react-router-dom";

import { clearMockSession, logoutCurrentSession, useAuthSession } from "./auth-store";
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

function getVisibleRoleRoutes(roleNames: UserRole[]) {
  const roleNameSet = new Set(roleNames);
  return roleRoutes.filter((roleRoute) => roleNameSet.has(roleRoute.role));
}

export function RootLayout() {
  const location = useLocation();
  const session = useAuthSession();
  const visibleRoleRoutes = session ? getVisibleRoleRoutes(session.availableRoles) : [];

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
            {visibleRoleRoutes.map((roleRoute) => (
              <Link
                key={roleRoute.path}
                className={`topbar-link${isRouteActive(location.pathname, roleRoute.path) ? " topbar-link-active" : ""}`}
                to={roleRoute.path}
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
  const visibleRoleRoutes = session ? getVisibleRoleRoutes(session.availableRoles) : [];

  if (!session) {
    return (
      <RoleWorkspace
        header={(
          <PageHeader
            eyebrow="账号入口"
            title="登录后进入对应工作台"
            description="未登录状态下不展示成员、管理员或系统管理功能板块。请先登录，再进入与你当前职责匹配的页面。"
            meta="当前未登录"
            actions={(
              <div className="page-actions">
                <Link className="button button-primary" to="/login">
                  前往登录 / 注册
                </Link>
              </div>
            )}
          />
        )}
        summary={(
          <section className="stat-grid" aria-label="登录说明">
            <StatCard label="成员账号" value="材料与确认" description="提交发票、查看识别状态、确认个人费用。" />
            <StatCard label="管理员账号" value="任务复核" description="只在登录后进入任务管理、复核与导出页面。" />
            <StatCard label="系统管理员" value="系统配置" description="系统配置和诊断入口不对未登录用户展示。" />
          </section>
        )}
      >
        <SectionCard
          title="账号与页面边界"
          description="登录页和业务页已分离。未登录用户不会看到具体功能板块，避免在入口阶段混入无关操作。"
        />
      </RoleWorkspace>
    );
  }

  return (
    <RoleWorkspace
      header={(
        <PageHeader
          eyebrow="报销任务总览"
          title="Tongji ACM 报销管理系统"
          description="登录后只展示当前账号可进入的工作台，不再把其他角色的业务板块混在首页。"
          meta={`当前身份：${formatWorkspace(session.role)}`}
          actions={(
            <div className="page-actions">
              <Link className="button button-primary" to={roleRoutes.find((item) => item.role === session.role)?.path ?? "/login"}>
                进入我的工作台
              </Link>
            </div>
          )}
        />
      )}
      summary={(
        <section className="stat-grid" aria-label="当前账号概览">
          <StatCard label="当前工作台" value={currentOverview?.title ?? formatWorkspace(session.role)} description={currentOverview?.summary ?? "当前账号已绑定可访问的工作台。"} />
          <StatCard label="可见板块" value={visibleRoleRoutes.length} description="只统计当前账号确实可以进入的工作台入口。" />
          <StatCard label="页面边界" value="已收口" description="无关角色入口、系统配置与诊断信息不会出现在当前首页。" />
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

      <section className="feature-grid" aria-label="当前账号可见入口">
        {visibleRoleRoutes.map((roleRoute) => {
          const overview = getActiveOverview(roleRoute.role);
          return (
            <SectionCard
              key={roleRoute.path}
              title={overview?.title ?? roleRoute.title}
              description={overview?.summary ?? roleRoute.summary}
              action={(
                <Link className="button button-secondary" to={roleRoute.path}>
                  进入工作台
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
