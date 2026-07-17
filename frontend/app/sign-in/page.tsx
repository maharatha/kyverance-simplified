import { auth } from "@/auth";
import { SignInPanel } from "@/components/auth/SignInPanel";
import { isEntraConfigured, isLocalDevIdentityEnabled } from "@/auth.config";
import { PRODUCT_NAME } from "@/lib/product";
import Link from "next/link";
import { redirect } from "next/navigation";
import { isSessionAuthenticated } from "@/lib/auth-session";

export default async function SignInPage({
  searchParams,
}: {
  searchParams: Promise<{ callbackUrl?: string }>;
}) {
  const session = await auth();
  if (isSessionAuthenticated(session)) {
    redirect("/");
  }

  const params = await searchParams;
  const callbackUrl = params.callbackUrl || "/";
  const entraReady = isEntraConfigured();
  const localDev = isLocalDevIdentityEnabled();

  return (
    <main className="sign-in-page">
      <div className="sign-in-panel">
        <p className="sign-in-brand">
          <Link href="/">{PRODUCT_NAME}</Link>
        </p>
        <h1>Sign in</h1>
        <p className="sign-in-support">
          Use your Kyverance account to continue to simulated portfolios and
          community features.
        </p>
        <SignInPanel
          callbackUrl={callbackUrl}
          entraReady={entraReady}
          localDev={localDev}
        />
      </div>
    </main>
  );
}
