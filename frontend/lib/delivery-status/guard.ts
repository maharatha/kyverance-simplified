/**
 * Local delivery board is development-only.
 * Production and test builds must never collect or expose workspace telemetry.
 */
export function isLocalDeliveryStatusEnabled(
  nodeEnv: string | undefined = process.env.NODE_ENV,
): boolean {
  return nodeEnv === "development";
}

export const DELIVERY_STATUS_UNAVAILABLE_REASON =
  "Delivery status is available only during local Next.js development (`next dev`).";
