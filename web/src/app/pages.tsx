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
