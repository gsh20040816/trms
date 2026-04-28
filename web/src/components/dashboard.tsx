import type { ReactNode } from "react";

type BadgeTone = "neutral" | "info" | "warning" | "danger" | "success";

type PageHeaderProps = {
  eyebrow?: string;
  title: string;
  description: string;
  meta?: string;
  actions?: ReactNode;
};

type StatCardProps = {
  label: string;
  value: ReactNode;
  description: string;
};

type EmptyStateProps = {
  title: string;
  description: string;
  action?: ReactNode;
};

type ErrorMessageProps = {
  title: string;
  message: string;
  details?: Array<{ label: string; message: string }>;
};

type RoleWorkspaceProps = {
  header: ReactNode;
  summary?: ReactNode;
  children: ReactNode;
};

type TaskTableProps = {
  caption: string;
  header: ReactNode;
  children: ReactNode;
};

export function StatusBadge({
  tone = "neutral",
  children,
}: {
  tone?: BadgeTone;
  children: ReactNode;
}) {
  return <span className={`status-badge status-badge-${tone}`}>{children}</span>;
}

export function SectionCard({
  title,
  description,
  action,
  children,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
  children?: ReactNode;
}) {
  return (
    <section className="panel-card">
      <div className="panel-card-header">
        <div>
          <h2>{title}</h2>
          {description ? <p>{description}</p> : null}
        </div>
        {action ? <div className="panel-card-action">{action}</div> : null}
      </div>
      {children}
    </section>
  );
}

export function PageHeader({ eyebrow, title, description, meta, actions }: PageHeaderProps) {
  return (
    <section className="page-header">
      <div className="page-header-body">
        {eyebrow ? <p className="page-header-eyebrow">{eyebrow}</p> : null}
        <h1>{title}</h1>
        <p>{description}</p>
        {meta ? <p className="page-header-meta">{meta}</p> : null}
      </div>
      {actions ? <div className="page-header-actions">{actions}</div> : null}
    </section>
  );
}

export function StatCard({ label, value, description }: StatCardProps) {
  return (
    <article className="stat-card">
      <p className="stat-card-label">{label}</p>
      <strong className="stat-card-value">{value}</strong>
      <p className="stat-card-description">{description}</p>
    </article>
  );
}

export function EmptyState({ title, description, action }: EmptyStateProps) {
  return (
    <section className="empty-state">
      <div>
        <h2>{title}</h2>
        <p>{description}</p>
      </div>
      {action ? <div className="empty-state-action">{action}</div> : null}
    </section>
  );
}

export function ErrorMessage({ title, message, details = [] }: ErrorMessageProps) {
  return (
    <section className="panel-card error-card" role="alert" aria-live="polite">
      <div className="panel-card-header">
        <div>
          <h2>{title}</h2>
          <p>{message}</p>
        </div>
        <StatusBadge tone="danger">需要处理</StatusBadge>
      </div>
      {details.length > 0 ? (
        <ul className="error-detail-list">
          {details.map((detail) => (
            <li key={`${detail.label}:${detail.message}`}>
              <strong>{detail.label}</strong>
              <span>{detail.message}</span>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}

export function RoleWorkspace({ header, summary, children }: RoleWorkspaceProps) {
  return (
    <div className="workspace-page">
      {header}
      {summary}
      {children}
    </div>
  );
}

export function TaskTable({ caption, header, children }: TaskTableProps) {
  return (
    <div className="table-shell">
      <table className="dashboard-table">
        <caption className="sr-only">{caption}</caption>
        <thead>{header}</thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  );
}

