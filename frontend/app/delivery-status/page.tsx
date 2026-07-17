import { DeliveryStatusBoard } from "@/components/delivery-status/DeliveryStatusBoard";
import { collectDeliveryStatus } from "@/lib/delivery-status/collect";
import { isLocalDeliveryStatusEnabled } from "@/lib/delivery-status/guard";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export default async function DeliveryStatusPage() {
  const status = await collectDeliveryStatus();
  const autoRefresh = isLocalDeliveryStatusEnabled() && status.available;

  return <DeliveryStatusBoard initialStatus={status} autoRefresh={autoRefresh} />;
}
