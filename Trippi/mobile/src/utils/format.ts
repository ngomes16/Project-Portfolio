/**
 * File: src/utils/format.ts
 * Purpose: Utility formatting helpers (currency, percent).
 */
export function formatCurrency(amount: number, currency: string = 'USD'): string {
  try {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency }).format(amount);
  } catch {
    return `$${amount.toFixed(2)}`;
  }
}

export function formatPercent(fraction: number): string {
  const pct = Math.max(0, Math.min(1, fraction));
  return `${Math.round(pct * 100)}%`;
}


