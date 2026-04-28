import { Link, Outlet } from "react-router-dom";

import { buildLoginPath, clearMockSession, logoutCurrentSession, useAuthSession } from "./auth-store";
import { roleRoutes } from "./role-routes";
import { apiClient } from "../lib/api/client";

export function RootLayout() {
  const session = useAuthSession();
  const currentRoleRoute = session
    ? roleRoutes.find((roleRoute) => roleRoute.role === session.role) ?? null
    : null;

  return (
    <div className="app-shell">
      <header className="hero-panel">
        <p className="eyebrow">TRMS Web</p>
        <h1>报销收集前端入口与账号登录已建立</h1>
        <p className="hero-copy">
          当前已固化入口、用户名密码登录注册、角色路由门禁和 API 客户端边界，并补齐管理员与成员两条前端主链路的首批真实业务页面。
        </p>
        <dl className="boundary-grid" aria-label="当前边界">
          <div>
            <dt>前端入口</dt>
            <dd>React + TypeScript + Vite</dd>
          </div>
          <div>
            <dt>路由边界</dt>
            <dd>成员、管理员、系统管理员三类入口已分离</dd>
          </div>
          <div>
            <dt>API 边界</dt>
            <dd>{apiClient.baseUrl}</dd>
          </div>
          <div>
            <dt>合同层</dt>
            <dd>任务、材料、发票、分摊、确认、校验、导出类型已固化</dd>
          </div>
          <div>
            <dt>错误展示</dt>
            <dd>统一解析 detail/message/字段校验错误，不在前端静默吞掉</dd>
          </div>
        </dl>
        <section className="session-banner" aria-label="当前会话">
          <div>
            <p className="eyebrow">Session Boundary</p>
            <h2>{session ? "当前已登录" : "当前未登录"}</h2>
            <p>
              当前支持用户名密码账号登录；OAuth 和统一身份认证仍属于后续增强范围。
            </p>
          </div>
          <div className="session-grid">
            <div>
              <dt>当前角色</dt>
              <dd>{currentRoleRoute ? currentRoleRoute.loginLabel : "未登录"}</dd>
            </div>
            <div>
              <dt>当前身份</dt>
              <dd>
                {session
                  ? `${session.displayName}${session.memberCode ? `（${session.memberCode}）` : ""}`
                  : "请先登录或注册账号"}
              </dd>
            </div>
          </div>
          <div className="inline-actions">
            <Link className="route-link" to={session && currentRoleRoute ? currentRoleRoute.path : "/login"}>
              {session ? "进入当前入口" : "登录或注册"}
            </Link>
            {session ? (
              <button
                className="route-link route-link-secondary"
                type="button"
                onClick={() => {
                  if (session.isMock) {
                    clearMockSession();
                  } else {
                    void logoutCurrentSession();
                  }
                }}
              >
                退出登录
              </button>
            ) : null}
          </div>
        </section>
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
      <section className="card-grid" aria-label="角色入口">
        {roleRoutes.map((roleRoute) => (
          <article key={roleRoute.path} className="route-card">
            <p className="card-kicker">{roleRoute.emphasis}</p>
            <h2>{roleRoute.title}</h2>
            <p>{roleRoute.summary}</p>
            <p className="role-card-meta">
              {session
                ? session.role === roleRoute.role
                  ? "当前身份可直接进入该入口。"
                  : "当前已登录为其他角色，进入后会看到角色错配提示。"
                : "未登录时将先跳转到账号登录页。"}
            </p>
            <Link
              className="route-link"
              to={session ? roleRoute.path : buildLoginPath(roleRoute.path)}
            >
              {session ? (session.role === roleRoute.role ? "进入当前入口" : "查看入口边界") : "登录后进入"}
            </Link>
          </article>
        ))}
      </section>
      <section className="status-card auth-panel" aria-label="登录占位边界">
        <p className="eyebrow">Account Auth</p>
        <h2>账号登录与角色入口边界已固定</h2>
        <p>
          未登录用户访问业务路由时会被重定向到 `/login`；当前账号登录会向后端注册或校验用户名密码，并保存 bearer token 与用户身份。
        </p>
        <p className="status-note">
          这一边界用于支撑下一批管理员列表、成员上传和系统配置页面开发，避免每个页面各自实现临时登录逻辑。
        </p>
      </section>
      <section className="status-card contract-card" aria-label="API 合同边界">
        <p className="eyebrow">API Contracts</p>
        <h2>前端 API 类型与错误边界已建立</h2>
        <p>
          当前前端已固化任务、材料、发票、分摊、确认、校验和导出合同类型，并为
          FastAPI 常见 `detail` 错误、字段校验错误和网络失败提供统一展示入口；管理员任务列表已开始复用这些合同和错误边界。
        </p>
        <p className="status-note">
          后续页面任务可继续复用统一 `trmsApi` 请求封装和 `ApiErrorNotice`
          错误组件，不需要在业务页面重复拼装错误文案。
        </p>
      </section>
    </div>
  );
}

export function NotFoundPage() {
  return (
    <section className="status-card">
      <p className="eyebrow">404</p>
      <h2>未找到对应页面</h2>
      <Link className="route-link" to="/">
        返回首页
      </Link>
    </section>
  );
}
