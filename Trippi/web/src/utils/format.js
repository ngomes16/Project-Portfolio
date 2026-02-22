/**
 * File: web/src/utils/format.js
 * Purpose: Formatting helpers for currency and percentage used across demos.
 */
export function formatCurrency(amount, currency = 'USD') {
  try {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency }).format(amount);
  } catch {
    return `$${Number(amount || 0).toFixed(2)}`;
  }
}

export function formatPercent(fraction) {
  const pct = Math.max(0, Math.min(1, Number(fraction || 0)));
  return `${Math.round(pct * 100)}%`;
}


