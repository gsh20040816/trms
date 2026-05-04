import Button from "@mui/material/Button";

import type { ReimbursementTask, SubmissionGuideConfig } from "../lib/api/types";

function getTaskSubmissionKey(task: ReimbursementTask) {
  return task.submission_key ?? task.email_submission_key;
}

export function TaskSubmissionGuide({
  task,
  guideConfig,
  webUploadHref,
}: {
  task: ReimbursementTask;
  guideConfig: SubmissionGuideConfig | null;
  webUploadHref?: string;
}) {
  const submissionKey = getTaskSubmissionKey(task);
  const emailAddress = guideConfig?.email_submission_address ?? null;
  const telegramBotUrl = guideConfig?.telegram_bot_url ?? null;
  const emailSubject = submissionKey ? `<${submissionKey}>` : null;

  return (
    <section className="task-submission-guide" aria-label="材料提交说明">
      <div className="task-submission-guide-header">
        <div>
          <p className="task-card-id">提交说明</p>
          <h3>成员可用这几种方式提交材料</h3>
        </div>
        {submissionKey ? <code>{submissionKey}</code> : null}
      </div>

      <ul className="task-submission-guide-list">
        <li>
          <strong>网页</strong>
          <span>在当前任务页直接上传发票、截图或压缩包。</span>
          {webUploadHref ? (
            <Button size="small" variant="text" href={webUploadHref}>
              去上传
            </Button>
          ) : null}
        </li>
        <li>
          <strong>邮件</strong>
          {submissionKey && emailAddress ? (
            <span>
              先在个人信息页绑定发件邮箱；主题以 <code>{emailSubject}</code> 开头，发送到 <a href={`mailto:${emailAddress}?subject=${encodeURIComponent(emailSubject ?? "")}`}>{emailAddress}</a>。
              多封邮件可作为 <code>.eml</code> 邮件包附件合并转发，系统会导入邮件包里的真实附件。
            </span>
          ) : (
            <span>{submissionKey ? "邮件提交入口未配置；如后续启用邮件提交，发送前仍需先在个人信息页绑定发件邮箱。" : "任务提交标识未配置，邮件提交暂不可用。"}</span>
          )}
          <Button size="small" variant="text" href="/profile">
            绑定邮箱
          </Button>
        </li>
        <li>
          <strong>Telegram</strong>
          {submissionKey && telegramBotUrl ? (
            <span>
              打开 <a href={telegramBotUrl} target="_blank" rel="noreferrer">Telegram Bot</a>，先发送 <code>/bind</code> 完成绑定，再发送 <code>/task {submissionKey}</code> 切换任务；之后可直接发送文件识别。
            </span>
          ) : (
            <span>{submissionKey ? "Telegram Bot 入口未配置，先使用网页上传。" : "任务提交标识未配置，Telegram 切换任务暂不可用。"}</span>
          )}
        </li>
      </ul>
    </section>
  );
}
