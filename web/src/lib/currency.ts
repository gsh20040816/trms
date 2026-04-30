export function formatCurrencyFromCents(cents: number) {
  return `￥${(cents / 100).toFixed(2)}`;
}

export function formatInvoiceAmountFromCents(
  cents: number | null | undefined,
  placeholder = "未识别金额/待补录",
) {
  if (typeof cents !== "number" || !Number.isFinite(cents)) {
    return placeholder;
  }
  return formatCurrencyFromCents(cents);
}
