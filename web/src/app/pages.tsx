import { Link, Outlet } from "react-router-dom";

import { roleRoutes } from "./role-routes";
import { apiClient } from "../lib/api/client";

export function RootLayout() {
  return (
    <div className="app-shell">
      <header className="hero-panel">
        <p className="eyebrow">TRMS Web Skeleton</p>
        <h1>报销收集前端骨架已建立</h1>
        <p className="hero-copy">
          当前只固化入口、路由和 API 客户端边界，不在本轮实现业务页面。
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
      </header>
      <main className="page-content">
        <Outlet />
      </main>
    </div>
  );
}

export function HomePage() {
  return (
    <div className="page-stack">
      <section className="card-grid" aria-label="角色入口">
        {roleRoutes.map((roleRoute) => (
          <article key={roleRoute.path} className="route-card">
            <p className="card-kicker">{roleRoute.emphasis}</p>
            <h2>{roleRoute.title}</h2>
            <p>{roleRoute.summary}</p>
            <Link className="route-link" to={roleRoute.path}>
              进入占位页
            </Link>
          </article>
        ))}
      </section>
      <section className="status-card contract-card" aria-label="API 合同边界">
        <p className="eyebrow">API Contracts</p>
        <h2>前端 API 类型与错误边界已建立</h2>
        <p>
          当前前端已固化任务、材料、发票、分摊、确认、校验和导出合同类型，并为
          FastAPI 常见 `detail` 错误、字段校验错误和网络失败提供统一展示入口。
        </p>
        <p className="status-note">
          下一轮页面任务可直接复用统一 `trmsApi` 请求封装和 `ApiErrorNotice`
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
