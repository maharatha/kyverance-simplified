import { NextResponse } from "next/server";
import { collectDeliveryStatus } from "@/lib/delivery-status/collect";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET() {
  const status = await collectDeliveryStatus();
  const headers = {
    "Cache-Control": "no-store",
  };

  if (!status.available) {
    return NextResponse.json(status, { status: 404, headers });
  }

  return NextResponse.json(status, { status: 200, headers });
}
