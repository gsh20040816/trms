import { ApiError } from "../lib/api/client";
import { summarizeUnknownError, type ApiErrorSummary } from "../lib/api/errors";
import { ErrorMessage } from "./dashboard";

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
    <ErrorMessage
      title={summary.title}
      message={summary.message}
      details={[
        ...summary.fieldIssues,
        ...summary.detailLines.map((detailLine) => ({
          label: "说明",
          message: detailLine,
        })),
      ]}
    />
  );
}
