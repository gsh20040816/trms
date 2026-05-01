import { useMemo, useState } from "react";

import Box from "@mui/material/Box";
import MenuItem from "@mui/material/MenuItem";
import TextField from "@mui/material/TextField";

import type { TaskMemberSummary } from "../lib/api/types";
import { buildTaskMemberSummaryMap, formatTaskMemberLabel } from "../lib/ui-text";

type TaskMemberAutocompleteProps = {
  label: string;
  value: string;
  options: string[];
  memberSummaries?: TaskMemberSummary[] | null;
  onChange: (value: string) => void;
  disabled?: boolean;
  error?: boolean;
  helperText?: string;
  includeEmptyOption?: boolean;
  emptyOptionLabel?: string;
  placeholder?: string;
  name?: string;
};

function normalizeKeyword(value: string) {
  return value.trim().toLowerCase();
}

function matchesMember(memberId: string, keyword: string) {
  if (!keyword) {
    return true;
  }
  return memberId.toLowerCase().includes(keyword);
}

export function TaskMemberAutocomplete({
  label,
  value,
  options,
  memberSummaries,
  onChange,
  disabled = false,
  error = false,
  helperText,
  includeEmptyOption = false,
  emptyOptionLabel = "请选择成员",
  placeholder,
  name,
}: TaskMemberAutocompleteProps) {
  const [searchKeyword, setSearchKeyword] = useState("");
  const keyword = normalizeKeyword(searchKeyword);
  const filteredOptions = useMemo(
    () => options.filter((memberId) => matchesMember(memberId, keyword)),
    [keyword, options],
  );
  const memberSummaryMap = useMemo(
    () => buildTaskMemberSummaryMap(memberSummaries),
    [memberSummaries],
  );
  const selectValue = filteredOptions.includes(value) ? value : "";

  const computedHelperText = helperText
    ?? (
      options.length === 0
        ? "当前任务没有可选成员。"
        : keyword.length === 0
          ? `当前可选 ${options.length} 名成员，可输入关键字筛选。`
          : filteredOptions.length > 0
            ? `当前匹配 ${filteredOptions.length} / ${options.length} 名成员。`
            : "没有匹配的成员。"
    );

  return (
    <Box sx={{ display: "grid", gap: 1.5 }}>
      <TextField
        label={`${label}搜索`}
        value={searchKeyword}
        onChange={(event) => {
          setSearchKeyword(event.target.value);
        }}
        placeholder={placeholder}
        disabled={disabled || options.length === 0}
        fullWidth
      />
      <TextField
        select
        label={label}
        name={name}
        value={selectValue}
        onChange={(event) => {
          onChange(event.target.value);
        }}
        error={error}
        helperText={computedHelperText}
        disabled={disabled}
        fullWidth
      >
        {includeEmptyOption || selectValue.length === 0 ? (
          <MenuItem value="">{emptyOptionLabel}</MenuItem>
        ) : null}
        {filteredOptions.map((memberId) => (
          <MenuItem key={memberId} value={memberId}>
            {formatTaskMemberLabel(memberId, memberSummaryMap)}
          </MenuItem>
        ))}
        {filteredOptions.length === 0 ? (
          <MenuItem disabled value="__no_match__">
            没有匹配的成员
          </MenuItem>
        ) : null}
      </TextField>
    </Box>
  );
}
