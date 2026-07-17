import { auth } from "@/auth";
import { ConnectedAccountsClient } from "@/components/settings/ConnectedAccountsClient";
import { isSessionAuthenticated } from "@/lib/auth-session";
import { redirect } from "next/navigation";

export default async function ConnectedAccountsPage() {
  const session = await auth();
  if (!isSessionAuthenticated(session)) {
    redirect("/sign-in?callbackUrl=/settings/connected");
  }

  return <ConnectedAccountsClient />;
}
