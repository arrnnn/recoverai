/**
 * RecoverAI - Currency Formatting
 * =================================
 * Mirrors agent/currency.py: all amounts are stored in USD; INR is shown
 * alongside for display. Rate is not live — set via NEXT_PUBLIC_USD_TO_INR_RATE
 * to match whatever your backend's USD_TO_INR_RATE is currently configured to.
 */

const USD_TO_INR_RATE = Number(process.env.NEXT_PUBLIC_USD_TO_INR_RATE || 88.0);

export function formatUsd(amountUsd: number): string {
  return `$${amountUsd.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function formatInr(amountUsd: number): string {
  const inr = amountUsd * USD_TO_INR_RATE;
  return `₹${inr.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function formatDual(amountUsd: number): string {
  return `${formatUsd(amountUsd)} (${formatInr(amountUsd)})`;
}