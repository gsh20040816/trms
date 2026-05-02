import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

type UserSearchCandidateOption = {
  key: string;
  label: string;
  onSelect: () => void;
};

type UserSearchCandidatePickerProps = {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
  helperText: string;
  error?: boolean;
  showOptions: boolean;
  options: UserSearchCandidateOption[];
  listAriaLabel: string;
  searchErrorText: string | null;
  emptyText: string;
};

export function UserSearchCandidatePicker({
  label,
  value,
  onChange,
  placeholder,
  helperText,
  error = false,
  showOptions,
  options,
  listAriaLabel,
  searchErrorText,
  emptyText,
}: UserSearchCandidatePickerProps) {
  return (
    <Stack spacing={0.75}>
      <TextField
        label={label}
        value={value}
        onChange={(event) => {
          onChange(event.target.value);
        }}
        placeholder={placeholder}
        helperText={helperText}
        error={error}
        fullWidth
      />

      {showOptions ? (
        <Stack
          spacing={0.5}
          aria-label={listAriaLabel}
          sx={{
            borderRadius: 3,
            border: "1px solid",
            borderColor: "divider",
            bgcolor: "background.paper",
            py: 0.5,
            overflow: "hidden",
          }}
        >
          {searchErrorText ? (
            <Typography variant="body2" color="error" sx={{ px: 1.5, py: 1 }}>
              {searchErrorText}
            </Typography>
          ) : null}
          {!searchErrorText && options.length === 0 ? (
            <Typography variant="body2" color="text.secondary" sx={{ px: 1.5, py: 1 }}>
              {emptyText}
            </Typography>
          ) : null}
          {options.map((option) => (
            <Button
              key={option.key}
              variant="text"
              color="inherit"
              sx={{
                justifyContent: "flex-start",
                borderRadius: 0,
                px: 1.5,
                py: 1,
              }}
              onClick={option.onSelect}
            >
              {option.label}
            </Button>
          ))}
        </Stack>
      ) : null}
    </Stack>
  );
}
