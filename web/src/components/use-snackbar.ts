import { useContext } from "react";

import { SnackbarContext, type SnackbarContextValue } from "./snackbar-context";

const noopSnackbar: SnackbarContextValue = {
  showSnackbar: () => undefined,
  showSuccess: () => undefined,
  showError: () => undefined,
  showInfo: () => undefined,
  showWarning: () => undefined,
};

export function useSnackbar() {
  const value = useContext(SnackbarContext);
  if (value) {
    return value;
  }
  // 在测试或在 Provider 之外渲染时退化为静默实现，避免单元测试为单个组件
  // 单独包裹 SnackbarProvider；生产构建始终包裹，路径不会落到这里。
  return noopSnackbar;
}
