import { ApiError } from "../lib/api/client";
import { summarizeUnknownError, type ApiErrorSummary } from "../lib/api/errors";

type ApiErrorNoticeProps = {
  error: unknown;
};

function resolveSummary(error: unknown): ApiErrorSummary {
  if (error instanceof ApiError) {
    return error.summary;
  }
  return summarizeUnknownError(error);
}

export function ApiErrorNotice({ error }: ApiErrorNoticeProps) {
  const summary = resolveSummary(error);

  return (
    <section className="status-card api-error-card" role="alert" aria-live="polite">
      <div className="api-error-header">
        <p className="eyebrow">API Error</p>
        <span className="status-chip">
          {summary.status > 0 ? `HTTP ${summary.status}` : "前端/网络"}
        </span>
      </div>
      <h2>{summary.title}</h2>
      <p>{summary.message}</p>
      {summary.fieldIssues.length > 0 ? (
        <ul className="api-error-list">
          {summary.fieldIssues.map((issue) => (
            <li key={`${issue.path}:${issue.message}`}>
              <strong>{issue.path}</strong>
              <span>{issue.message}</span>
            </li>
          ))}
        </ul>
      ) : null}
      {summary.detailLines.length > 0 ? (
        <div className="status-note">
          {summary.detailLines.map((detailLine) => (
            <p key={detailLine}>{detailLine}</p>
          ))}
        </div>
      ) : null}
    </section>
  );
}
