import { redirect } from "next/navigation";

/** Legacy path — canonical route is `/settings/connected-accounts`. */
export default function ConnectedAccountsLegacyRedirect() {
  redirect("/settings/connected-accounts");
}
