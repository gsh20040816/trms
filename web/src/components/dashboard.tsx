import type { ReactNode } from "react";

import Alert from "@mui/material/Alert";
import AlertTitle from "@mui/material/AlertTitle";
import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip, { type ChipProps } from "@mui/material/Chip";
import Stack from "@mui/material/Stack";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import Typography from "@mui/material/Typography";

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

const TONE_CHIP_COLOR: Record<BadgeTone, ChipProps["color"]> = {
  neutral: "default",
  info: "info",
  warning: "warning",
  danger: "error",
  success: "success",
};

export function StatusBadge({
  tone = "neutral",
  children,
}: {
  tone?: BadgeTone;
  children: ReactNode;
}) {
  const color = TONE_CHIP_COLOR[tone];
  const variant: ChipProps["variant"] = tone === "neutral" ? "outlined" : "filled";
  return (
    <Chip
      size="small"
      color={color}
      variant={variant}
      label={children}
      sx={{ fontWeight: 700 }}
    />
  );
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
    <Card component="section" variant="outlined">
      <CardContent>
        <Stack
          direction={{ xs: "column", sm: "row" }}
          alignItems={{ xs: "flex-start", sm: "flex-start" }}
          justifyContent="space-between"
          spacing={1.5}
          sx={{ mb: children ? 2 : 0 }}
        >
          <Box sx={{ minWidth: 0 }}>
            <Typography component="h2" variant="h6" sx={{ lineHeight: 1.25 }}>
              {title}
            </Typography>
            {description ? (
              <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                {description}
              </Typography>
            ) : null}
          </Box>
          {action ? <Box>{action}</Box> : null}
        </Stack>
        {children ? <Box>{children}</Box> : null}
      </CardContent>
    </Card>
  );
}

export function PageHeader({ eyebrow, title, description, meta, actions }: PageHeaderProps) {
  return (
    <Box component="section" sx={{ mb: 1 }}>
      <Stack
        direction={{ xs: "column", md: "row" }}
        alignItems={{ xs: "flex-start", md: "flex-end" }}
        justifyContent="space-between"
        spacing={2}
      >
        <Box sx={{ minWidth: 0 }}>
          {eyebrow ? (
            <Typography variant="overline" color="text.secondary">
              {eyebrow}
            </Typography>
          ) : null}
          <Typography component="h1" variant="h3" sx={{ mt: eyebrow ? 0.5 : 0, mb: 1 }}>
            {title}
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ maxWidth: 720 }}>
            {description}
          </Typography>
          {meta ? (
            <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 1 }}>
              {meta}
            </Typography>
          ) : null}
        </Box>
        {actions ? <Box>{actions}</Box> : null}
      </Stack>
    </Box>
  );
}

export function StatCard({ label, value, description }: StatCardProps) {
  return (
    <Card component="article" variant="outlined" sx={{ height: "100%" }}>
      <CardContent>
        <Typography variant="overline" color="text.secondary" component="p">
          {label}
        </Typography>
        <Typography component="strong" variant="h4" sx={{ display: "block", my: 0.5, fontWeight: 600, lineHeight: 1.1 }}>
          {value}
        </Typography>
        <Typography variant="body2" color="text.secondary" component="p">
          {description}
        </Typography>
      </CardContent>
    </Card>
  );
}

export function EmptyState({ title, description, action }: EmptyStateProps) {
  return (
    <Card
      component="section"
      variant="outlined"
      sx={{
        borderStyle: "dashed",
      }}
    >
      <CardContent>
        <Stack
          direction={{ xs: "column", sm: "row" }}
          alignItems={{ xs: "flex-start", sm: "center" }}
          justifyContent="space-between"
          spacing={2}
        >
          <Box>
            <Typography component="h2" variant="h6">
              {title}
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
              {description}
            </Typography>
          </Box>
          {action ? <Box>{action}</Box> : null}
        </Stack>
      </CardContent>
    </Card>
  );
}

export function ErrorMessage({ title, message, details = [] }: ErrorMessageProps) {
  return (
    <Alert
      severity="error"
      variant="outlined"
      role="alert"
      sx={{ alignItems: "flex-start" }}
    >
      <AlertTitle component="h2" sx={{ fontWeight: 700, fontSize: "1.05rem" }}>
        {title}
      </AlertTitle>
      <Typography variant="body2" sx={{ mb: details.length > 0 ? 1.5 : 0 }}>
        {message}
      </Typography>
      {details.length > 0 ? (
        <Box component="ul" sx={{ m: 0, pl: 2.5, display: "grid", gap: 0.5 }}>
          {details.map((detail) => (
            <Box component="li" key={`${detail.label}:${detail.message}`} sx={{ display: "block" }}>
              <Typography component="strong" variant="body2" sx={{ fontWeight: 700, mr: 1 }}>
                {detail.label}
              </Typography>
              <Typography component="span" variant="body2">
                {detail.message}
              </Typography>
            </Box>
          ))}
        </Box>
      ) : null}
    </Alert>
  );
}

export function RoleWorkspace({ header, summary, children }: RoleWorkspaceProps) {
  return (
    <Stack className="workspace-page" spacing={2.5}>
      {header}
      {summary}
      {children}
    </Stack>
  );
}

export function TaskTable({ caption, header, children }: TaskTableProps) {
  return (
    <TableContainer
      component={Box}
      sx={{
        borderRadius: 2,
        border: 1,
        borderColor: "divider",
      }}
    >
      <Table aria-label={caption} size="small">
        <Box component="caption" sx={{ position: "absolute", width: 1, height: 1, p: 0, m: -1, overflow: "hidden", clip: "rect(0,0,0,0)", border: 0 }}>
          {caption}
        </Box>
        <TableHead>{header}</TableHead>
        <TableBody>{children}</TableBody>
      </Table>
    </TableContainer>
  );
}
