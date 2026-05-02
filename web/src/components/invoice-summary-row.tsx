import type { ReactNode } from "react";

import Checkbox from "@mui/material/Checkbox";

import { StatusBadge } from "./dashboard";

type InvoiceSummaryRowTone = "success" | "warning" | "neutral";

type InvoiceSummaryRowProps = {
  filename: string;
  invoiceNumber: string | null;
  primaryLabel?: string | null;
  amountLabel: string;
  validationLabel: string;
  validationTone: InvoiceSummaryRowTone;
  supportingMaterialCount: number;
  statusHint?: string | null;
  emphasisLabel?: string | null;
  highlight?: boolean;
  selected?: boolean;
  selection?: {
    checked: boolean;
    disabled: boolean;
    ariaLabel: string;
    onChange: (checked: boolean) => void;
  } | null;
  action?: {
    ariaLabel: string;
    onClick: () => void;
  } | null;
  trailingContent?: ReactNode;
};

export function InvoiceSummaryRow({
  filename,
  invoiceNumber,
  primaryLabel = null,
  amountLabel,
  validationLabel,
  validationTone,
  supportingMaterialCount,
  statusHint = null,
  emphasisLabel = null,
  highlight = false,
  selected = false,
  selection = null,
  action = null,
  trailingContent = null,
}: InvoiceSummaryRowProps) {
  const summaryRowClassName = [
    "invoice-summary-row-shell",
    highlight ? "invoice-summary-row-shell-warning" : "",
    selected ? "invoice-summary-row-shell-selected" : "",
  ].filter(Boolean).join(" ");
  const summaryButtonClassName = highlight
    ? "invoice-summary-row-button invoice-summary-row-button-warning"
    : "invoice-summary-row-button";
  const headlineLabel = primaryLabel ?? `票号 ${invoiceNumber ?? "待补录"}`;

  return (
    <div className={summaryRowClassName}>
      {selection ? (
        <div className="invoice-summary-selection">
          <Checkbox
            checked={selection.checked}
            disabled={selection.disabled}
            onChange={(event) => {
              selection.onChange(event.target.checked);
            }}
            inputProps={{ "aria-label": selection.ariaLabel }}
          />
        </div>
      ) : null}
      {action ? (
        <button
          type="button"
          className={summaryButtonClassName}
          aria-label={action.ariaLabel}
          onClick={action.onClick}
        >
          <span className="invoice-summary-lines">
            <span className="invoice-summary-line invoice-summary-number" title={headlineLabel}>
              {headlineLabel}
            </span>
            <span className="invoice-summary-line invoice-summary-file" title={filename}>
              {filename}
            </span>
            <span className="invoice-summary-line invoice-summary-meta">
              <span title={amountLabel}>{amountLabel}</span>
              <span className={`invoice-summary-validation invoice-summary-validation-${validationTone}`}>
                {validationLabel}
              </span>
              <span>附件 {supportingMaterialCount}</span>
            </span>
          </span>
          <span className="invoice-summary-side">
            {statusHint ? (
              <span className="invoice-summary-hint" title={statusHint}>
                {statusHint}
              </span>
            ) : null}
            {trailingContent}
            {emphasisLabel ? <StatusBadge tone="warning">{emphasisLabel}</StatusBadge> : null}
          </span>
        </button>
      ) : (
        <div className={`${summaryButtonClassName} invoice-summary-row-static`}>
          <span className="invoice-summary-lines">
            <span className="invoice-summary-line invoice-summary-number" title={headlineLabel}>
              {headlineLabel}
            </span>
            <span className="invoice-summary-line invoice-summary-file" title={filename}>
              {filename}
            </span>
            <span className="invoice-summary-line invoice-summary-meta">
              <span title={amountLabel}>{amountLabel}</span>
              <span className={`invoice-summary-validation invoice-summary-validation-${validationTone}`}>
                {validationLabel}
              </span>
              <span>附件 {supportingMaterialCount}</span>
            </span>
          </span>
          <span className="invoice-summary-side">
            {statusHint ? (
              <span className="invoice-summary-hint" title={statusHint}>
                {statusHint}
              </span>
            ) : null}
            {trailingContent}
            {emphasisLabel ? <StatusBadge tone="warning">{emphasisLabel}</StatusBadge> : null}
          </span>
        </div>
      )}
    </div>
  );
}
