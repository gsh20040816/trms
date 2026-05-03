import type { ReactNode } from "react";

import Box from "@mui/material/Box";
import ButtonBase from "@mui/material/ButtonBase";
import Checkbox from "@mui/material/Checkbox";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import { StatusBadge, SurfaceCard } from "./dashboard";

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
    <SurfaceCard className={summaryRowClassName}>
      {selection ? (
        <Box className="invoice-summary-selection">
          <Checkbox
            checked={selection.checked}
            disabled={selection.disabled}
            onChange={(event) => {
              selection.onChange(event.target.checked);
            }}
            inputProps={{ "aria-label": selection.ariaLabel }}
          />
        </Box>
      ) : null}
      {action ? (
        <ButtonBase
          component="button"
          className={summaryButtonClassName}
          aria-label={action.ariaLabel}
          onClick={action.onClick}
          disabled={false}
          focusRipple
        >
          <Stack className="invoice-summary-lines">
            <Typography className="invoice-summary-line invoice-summary-number" title={headlineLabel} component="span">
              {headlineLabel}
            </Typography>
            <Typography className="invoice-summary-line invoice-summary-file" title={filename} component="span">
              {filename}
            </Typography>
            <Box className="invoice-summary-line invoice-summary-meta">
              <Typography component="span" title={amountLabel}>{amountLabel}</Typography>
              <Typography component="span" className={`invoice-summary-validation invoice-summary-validation-${validationTone}`}>
                {validationLabel}
              </Typography>
              <Typography component="span">附件 {supportingMaterialCount}</Typography>
            </Box>
          </Stack>
          <Box className="invoice-summary-side">
            {statusHint ? (
              <Typography component="span" className="invoice-summary-hint" title={statusHint}>
                {statusHint}
              </Typography>
            ) : null}
            {trailingContent}
            {emphasisLabel ? <StatusBadge tone="warning">{emphasisLabel}</StatusBadge> : null}
          </Box>
        </ButtonBase>
      ) : (
        <Box className={`${summaryButtonClassName} invoice-summary-row-static`}>
          <Stack className="invoice-summary-lines">
            <Typography className="invoice-summary-line invoice-summary-number" title={headlineLabel} component="span">
              {headlineLabel}
            </Typography>
            <Typography className="invoice-summary-line invoice-summary-file" title={filename} component="span">
              {filename}
            </Typography>
            <Box className="invoice-summary-line invoice-summary-meta">
              <Typography component="span" title={amountLabel}>{amountLabel}</Typography>
              <Typography component="span" className={`invoice-summary-validation invoice-summary-validation-${validationTone}`}>
                {validationLabel}
              </Typography>
              <Typography component="span">附件 {supportingMaterialCount}</Typography>
            </Box>
          </Stack>
          <Box className="invoice-summary-side">
            {statusHint ? (
              <Typography component="span" className="invoice-summary-hint" title={statusHint}>
                {statusHint}
              </Typography>
            ) : null}
            {trailingContent}
            {emphasisLabel ? <StatusBadge tone="warning">{emphasisLabel}</StatusBadge> : null}
          </Box>
        </Box>
      )}
    </SurfaceCard>
  );
}
