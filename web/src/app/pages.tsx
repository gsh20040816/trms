import { Link, Outlet, useLocation } from "react-router-dom";

import { buildLoginPath, clearMockSession, logoutCurrentSession, useAuthSession } from "./auth-store";
import { roleRoutes, type UserRole } from "./role-routes";
import { apiClient } from "../lib/api/client";

type WorkflowStage = {
  label: string;
  summary: string;
};

type RolePlaybook = {
  role: UserRole;
  stage: string;
  outcome: string;
  actions: string[];
};

const WORKFLOW_STAGES: WorkflowStage[] = [
  {
    label: "创建任务",
    summary: "管理员先把比赛、成员、截止时间和费用类别配置完整。",
  },
  {
    label: "收集材料",
    summary: "成员只处理当前比赛任务，不在无关页面里来回找入口。",
  },
  {
    label: "识别校验",
    summary: "系统暴露识别失败、待确认字段和缺失材料，不把异常藏起来。",
  },
  {
    label: "分摊确认",
    summary: "成员确认自己的费用明细，管理员只处理冲突和逾期项。",
  },
  {
    label: "复核导出",
    summary: "管理员在一个工作台里完成复核、提醒和导出准备。",
  },
];

const ROLE_PLAYBOOKS: RolePlaybook[] = [
  {
    role: "member",
    stage: "材料提交主链路",
    outcome: "先看自己要补什么，再决定上传、确认还是等待复核。",
    actions: ["查看可见任务", "上传材料或补附件", "确认费用明细"],
  },
  {
    role: "admin",
    stage: "任务管理与复核",
    outcome: "优先推进有异常、快截止、可进入下一阶段的任务。",
    actions: ["创建或发布任务", "处理异常与异议", "进入复核与导出"],
  },
  {
    role: "system_admin",
    stage: "全局配置边界",
    outcome: "保留系统级入口，但不让它干扰成员和管理员的主流程。",
    actions: ["检查账号策略", "预留渠道配置", "维护全局治理边界"],
  },
];

function isRouteActive(pathname: string, targetPath: string) {
  if (targetPath === "/") {
    return pathname === "/";
  }
  return pathname === targetPath || pathname.startsWith(`${targetPath}/`);
}

function getRolePlaybook(role: UserRole) {
  return ROLE_PLAYBOOKS.find((item) => item.role === role);
}

export function RootLayout() {
  const location = useLocation();
  const session = useAuthSession();
  const currentRoleRoute = session
    ? roleRoutes.find((roleRoute) => roleRoute.role === session.role) ?? null
    : null;
  const activeRoleRoute = roleRoutes.find((roleRoute) => isRouteActive(location.pathname, roleRoute.path)) ?? null;

  return (
    <div className="workspace-shell">
      <header className="workspace-header">
        <div className="workspace-nav-row">
          <Link className="brand-mark" to="/">
            TRMS
          </Link>
          <nav className="workspace-nav" aria-label="主导航">
            <Link
              className={`workspace-nav-link${location.pathname === "/" ? " workspace-nav-link-active" : ""}`}
              to="/"
            >
              总览
            </Link>
            {roleRoutes.map((roleRoute) => (
              <Link
                key={roleRoute.path}
                className={`workspace-nav-link${isRouteActive(location.pathname, roleRoute.path) ? " workspace-nav-link-active" : ""}`}
                to={session ? roleRoute.path : buildLoginPath(roleRoute.path)}
              >
                {roleRoute.title}
              </Link>
            ))}
          </nav>
          <div className="workspace-session-cluster">
            <span className="session-pill">
              {session && currentRoleRoute ? currentRoleRoute.loginLabel : "未登录"}
            </span>
            {session ? (
              <>
                <span className="session-text">
                  {session.displayName}
                  {session.memberCode ? `（${session.memberCode}）` : ""}
                </span>
                <button
                  className="route-link route-link-secondary"
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
              <Link className="route-link" to="/login">
                登录或注册
              </Link>
            )}
          </div>
        </div>

        <section className="workspace-hero">
          <div className="workspace-hero-main">
            <p className="eyebrow">Tongji ACM Reimbursement Mission Control</p>
            <h1>把报销流程变成一条可推进的工作流</h1>
            <p className="hero-copy">
              首页不再先展示一堆边界说明。成员优先看到自己的下一步动作，管理员优先看到异常、截止时间和推进状态。
            </p>
            <div className="inline-actions">
              <Link className="route-link" to={session && currentRoleRoute ? currentRoleRoute.path : "/login"}>
                {session && currentRoleRoute ? "进入当前工作台" : "进入登录页"}
              </Link>
              <Link className="route-link route-link-secondary" to="/">
                查看流程总览
              </Link>
            </div>
          </div>

          <aside className="workspace-hero-panel" aria-label="当前会话摘要">
            <p className="card-kicker">当前工作台</p>
            <h2>{activeRoleRoute ? activeRoleRoute.title : "统一入口总览"}</h2>
            <p>
              {activeRoleRoute
                ? activeRoleRoute.summary
                : "从总览页选择角色入口，再进入对应的成员或管理员工作流。"}
            </p>
            <dl className="workspace-meta-grid">
              <div>
                <dt>当前角色</dt>
                <dd>{currentRoleRoute ? currentRoleRoute.loginLabel : "未登录"}</dd>
              </div>
              <div>
                <dt>API 边界</dt>
                <dd>{apiClient.baseUrl}</dd>
              </div>
              <div>
                <dt>当前路径</dt>
                <dd>{location.pathname}</dd>
              </div>
              <div>
                <dt>工作方式</dt>
                <dd>{session ? "按身份进入工作台" : "先登录，再进入工作台"}</dd>
              </div>
            </dl>
          </aside>
        </section>

        <ol className="workflow-strip" aria-label="报销主流程">
          {WORKFLOW_STAGES.map((stage, index) => (
            <li key={stage.label} className="workflow-step">
              <span className="workflow-step-index">{index + 1}</span>
              <div>
                <strong>{stage.label}</strong>
                <span>{stage.summary}</span>
              </div>
            </li>
          ))}
        </ol>
      </header>

      <main className="page-content">
        <Outlet />
      </main>
    </div>
  );
}

export function HomePage() {
  const session = useAuthSession();

  return (
    <div className="page-stack">
      <section className="status-card dashboard-panel">
        <p className="eyebrow">Workflow Overview</p>
        <h2>按阶段推进，不按页面迷路</h2>
        <p>
          成员和管理员看到的是不同的工作台，但都沿着同一条主流程推进。真正需要优先处理的是异常和下一步动作，而不是重复解释系统边界。
        </p>
        <div className="workflow-board">
          {WORKFLOW_STAGES.map((stage, index) => (
            <article key={stage.label} className="workflow-board-card">
              <span className="workflow-board-index">0{index + 1}</span>
              <h3>{stage.label}</h3>
              <p>{stage.summary}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="dashboard-grid" aria-label="角色入口">
        {roleRoutes.map((roleRoute) => {
          const playbook = getRolePlaybook(roleRoute.role);

          return (
            <article key={roleRoute.path} className="route-card route-card-accent">
              <div className="task-card-top">
                <div>
                  <p className="card-kicker">{playbook?.stage ?? roleRoute.emphasis}</p>
                  <h2>{roleRoute.title}</h2>
                </div>
                <span className="status-chip">
                  {session && session.role === roleRoute.role ? "当前角色" : "角色入口"}
                </span>
              </div>
              <p>{playbook?.outcome ?? roleRoute.summary}</p>
              {playbook ? (
                <ul className="task-workflow-list" aria-label={`${roleRoute.title} 推荐动作`}>
                  {playbook.actions.map((action) => (
                    <li key={`${roleRoute.role}:${action}`} className="task-workflow-item">
                      {action}
                    </li>
                  ))}
                </ul>
              ) : null}
              <p className="role-card-meta">
                {session
                  ? session.role === roleRoute.role
                    ? "当前身份可直接进入该工作台。"
                    : "当前已登录为其他角色，进入后会看到角色错配提示。"
                  : "未登录时将先跳转到账号登录页。"}
              </p>
              <div className="inline-actions">
                <Link
                  className="route-link"
                  to={session ? roleRoute.path : buildLoginPath(roleRoute.path)}
                >
                  {session && session.role === roleRoute.role ? "进入当前工作台" : "查看该入口"}
                </Link>
              </div>
            </article>
          );
        })}
      </section>

      <section className="status-card dashboard-panel">
        <p className="eyebrow">Operating Rules</p>
        <h2>当前前端先解决三件事</h2>
        <div className="dashboard-kpi-grid">
          <div className="kpi-card">
            <strong className="kpi-label">先看下一步</strong>
            <p>成员先看上传、补材料、确认费用的入口，不再先读说明文本。</p>
          </div>
          <div className="kpi-card">
            <strong className="kpi-label">先看异常</strong>
            <p>管理员先看 Must 级失败、识别异常、异议和逾期确认，再决定推进顺序。</p>
          </div>
          <div className="kpi-card">
            <strong className="kpi-label">先看阶段</strong>
            <p>所有入口都围绕同一条任务阶段线组织，减少页面间跳转迷路。</p>
          </div>
        </div>
      </section>
    </div>
  );
}

export function NotFoundPage() {
  return (
    <section className="status-card">
      <p className="eyebrow">404</p>
      <h2>未找到对应页面</h2>
      <p>返回首页后可重新选择成员、管理员或系统管理员入口。</p>
      <div className="inline-actions">
        <Link className="route-link" to="/">
          返回首页
        </Link>
      </div>
    </section>
  );
}
