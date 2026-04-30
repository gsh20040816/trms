export function buildInvoiceDetailPath(taskId: string, invoiceId: string) {
  return `/member/invoices/${encodeURIComponent(invoiceId)}?taskId=${encodeURIComponent(taskId)}`;
}

export function buildMaterialInvoiceDetailPath(taskId: string, materialId: string) {
  return `/member/materials/${encodeURIComponent(materialId)}/invoice?taskId=${encodeURIComponent(taskId)}`;
}
