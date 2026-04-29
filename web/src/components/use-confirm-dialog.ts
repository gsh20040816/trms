import { useContext } from "react";

import { ConfirmDialogContext, type ConfirmDialogContextValue } from "./confirm-dialog-context";

const noopConfirmContext: ConfirmDialogContextValue = {
  confirm: () => Promise.resolve(true),
};

export function useConfirmDialog() {
  const context = useContext(ConfirmDialogContext);
  if (context) {
    return context;
  }
  // 在 Provider 之外（例如部分单元测试）调用时退化为直接通过的实现，避免业务路径
  // 在隔离测试中被强行包裹 Provider；生产构建始终包裹。
  return noopConfirmContext;
}
