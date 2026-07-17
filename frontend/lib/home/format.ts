import type { DecimalString } from "./types";

/** Formats a supplied decimal string for display. Does not compute P&L or totals. */
export function formatMoney(value: DecimalString, currency = "USD"): string {
  const normalized = value.trim();
  const negative = normalized.startsWith("-");
  const unsigned = negative ? normalized.slice(1) : normalized;
  const [wholeRaw, fractionRaw = ""] = unsigned.split(".");
  const whole = wholeRaw.replace(/^0+(?=\d)/, "") || "0";
  const withSeparators = whole.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  const fraction = fractionRaw.padEnd(2, "0").slice(0, 2);
  const amount = `${withSeparators}.${fraction}`;
  const prefix = currency === "USD" ? "$" : `${currency} `;
  return `${negative ? "-" : ""}${prefix}${amount}`;
}

/** Formats a supplied percent string with an explicit sign for accessibility. */
export function formatSignedPercent(value: DecimalString): string {
  const normalized = value.trim();
  if (normalized.startsWith("-") || normalized.startsWith("+")) {
    return `${normalized}%`;
  }
  if (normalized === "0" || normalized === "0.0" || normalized === "0.00") {
    return "0.00%";
  }
  return `+${normalized}%`;
}

export function formatSignedMoney(value: DecimalString, currency = "USD"): string {
  const normalized = value.trim();
  if (normalized.startsWith("-")) {
    return formatMoney(normalized, currency);
  }
  if (normalized === "0" || normalized === "0.0" || normalized === "0.00") {
    return formatMoney("0.00", currency);
  }
  return `+${formatMoney(normalized, currency)}`;
}

export function formatTimestamp(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return iso;
  }
  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  }).format(date);
}

export function provenanceLabel(
  provenance: "simulated" | "manual_unverified" | "connected_read_only",
): string {
  switch (provenance) {
    case "simulated":
      return "Simulated";
    case "manual_unverified":
      return "Manual (unverified)";
    case "connected_read_only":
      return "Connected (read-only)";
  }
}
