import { useCallback, useRef, useState, type DragEvent } from "react";

import CloudUploadIcon from "@mui/icons-material/CloudUpload";
import DescriptionIcon from "@mui/icons-material/Description";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import ImageIcon from "@mui/icons-material/Image";
import PictureAsPdfIcon from "@mui/icons-material/PictureAsPdf";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import IconButton from "@mui/material/IconButton";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemAvatar from "@mui/material/ListItemAvatar";
import ListItemText from "@mui/material/ListItemText";
import Avatar from "@mui/material/Avatar";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

type FileDropZoneProps = {
  files: File[];
  onChange: (next: File[]) => void;
  accept?: string;
  multiple?: boolean;
  disabled?: boolean;
  hint?: string;
  ariaLabel?: string;
  fileListAriaLabel?: string;
  inputName?: string;
  inputId?: string;
};

function pickFileIcon(file: File) {
  const lowerName = file.name.toLowerCase();
  if (file.type.startsWith("image/") || /\.(png|jpe?g|webp|gif)$/.test(lowerName)) {
    return <ImageIcon />;
  }
  if (file.type === "application/pdf" || lowerName.endsWith(".pdf")) {
    return <PictureAsPdfIcon />;
  }
  return <DescriptionIcon />;
}

function formatBytes(value: number) {
  if (!Number.isFinite(value) || value <= 0) {
    return "0 B";
  }
  const units = ["B", "KB", "MB", "GB"];
  let unitIndex = 0;
  let displayValue = value;
  while (displayValue >= 1024 && unitIndex < units.length - 1) {
    displayValue /= 1024;
    unitIndex += 1;
  }
  return `${displayValue.toFixed(displayValue < 10 ? 1 : 0)} ${units[unitIndex]}`;
}

export function FileDropZone({
  files,
  onChange,
  accept,
  multiple = true,
  disabled = false,
  hint,
  ariaLabel = "选择上传文件",
  fileListAriaLabel = "已选择文件",
  inputName,
  inputId,
}: FileDropZoneProps) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  const acceptInputFiles = useCallback(
    (input: FileList | null) => {
      if (!input) {
        return;
      }
      const next = Array.from(input);
      onChange(multiple ? [...files, ...next] : next.slice(0, 1));
    },
    [files, multiple, onChange],
  );

  const handleDragOver = useCallback((event: DragEvent<HTMLDivElement>) => {
    if (disabled) {
      return;
    }
    event.preventDefault();
    setIsDragging(true);
  }, [disabled]);

  const handleDragLeave = useCallback(() => {
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(
    (event: DragEvent<HTMLDivElement>) => {
      if (disabled) {
        return;
      }
      event.preventDefault();
      setIsDragging(false);
      acceptInputFiles(event.dataTransfer?.files ?? null);
    },
    [acceptInputFiles, disabled],
  );

  const handleRemove = useCallback(
    (target: File) => {
      onChange(files.filter((file) => file !== target));
    },
    [files, onChange],
  );

  return (
    <Stack spacing={1.5}>
      <Box
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        sx={{
          position: "relative",
          borderRadius: 3,
          border: "2px dashed",
          borderColor: isDragging ? "primary.main" : "divider",
          bgcolor: isDragging ? "action.hover" : "background.paper",
          p: { xs: 3, sm: 4 },
          transition: "all 120ms",
          textAlign: "center",
          cursor: disabled ? "not-allowed" : "pointer",
          opacity: disabled ? 0.6 : 1,
        }}
        onClick={() => {
          if (!disabled) {
            inputRef.current?.click();
          }
        }}
      >
        <Stack alignItems="center" spacing={1.5}>
          <Avatar
            variant="rounded"
            sx={{
              bgcolor: isDragging ? "primary.main" : "action.hover",
              color: isDragging ? "primary.contrastText" : "primary.main",
              width: 48,
              height: 48,
            }}
          >
            <CloudUploadIcon />
          </Avatar>
          <Typography variant="subtitle1" component="span">
            {isDragging ? "松开即可加入待上传列表" : "拖拽文件到此处，或点击选择文件"}
          </Typography>
          {hint ? (
            <Typography variant="body2" color="text.secondary">
              {hint}
            </Typography>
          ) : null}
          <Button
            variant="outlined"
            size="small"
            disabled={disabled}
            onClick={(event) => {
              event.stopPropagation();
              inputRef.current?.click();
            }}
            startIcon={<CloudUploadIcon fontSize="small" />}
          >
            选择文件
          </Button>
        </Stack>
        <input
          ref={inputRef}
          aria-label={ariaLabel}
          id={inputId}
          name={inputName}
          type="file"
          accept={accept}
          multiple={multiple}
          disabled={disabled}
          style={{
            position: "absolute",
            inset: 0,
            opacity: 0,
            pointerEvents: "none",
          }}
          onChange={(event) => {
            acceptInputFiles(event.target.files);
            event.target.value = "";
          }}
        />
      </Box>

      {files.length > 0 ? (
        <List dense aria-label={fileListAriaLabel} sx={{ p: 0 }}>
          {files.map((file) => (
            <ListItem
              key={`${file.name}:${file.size}:${file.lastModified}`}
              disablePadding
              sx={{
                bgcolor: "action.hover",
                borderRadius: 2,
                mb: 1,
                px: 1.5,
                py: 1,
                "&:last-of-type": { mb: 0 },
              }}
              secondaryAction={(
                <IconButton
                  edge="end"
                  size="small"
                  aria-label={`移除 ${file.name}`}
                  onClick={() => handleRemove(file)}
                  disabled={disabled}
                >
                  <DeleteOutlineIcon fontSize="small" />
                </IconButton>
              )}
            >
              <ListItemAvatar>
                <Avatar variant="rounded" sx={{ bgcolor: "background.paper", color: "text.secondary" }}>
                  {pickFileIcon(file)}
                </Avatar>
              </ListItemAvatar>
              <ListItemText
                primary={file.name}
                secondary={`${file.type || "未知类型"} · ${formatBytes(file.size)}`}
                primaryTypographyProps={{ variant: "body2", fontWeight: 600, noWrap: true }}
                secondaryTypographyProps={{ variant: "caption", color: "text.secondary" }}
              />
            </ListItem>
          ))}
        </List>
      ) : null}
    </Stack>
  );
}
