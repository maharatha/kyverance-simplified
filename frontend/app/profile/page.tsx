import { auth } from "@/auth";
import { isSessionAuthenticated } from "@/lib/auth-session";
import { RoutePlaceholder } from "@/components/RoutePlaceholder";
import { redirect } from "next/navigation";

export default async function ProfilePage() {
  const session = await auth();
  if (!isSessionAuthenticated(session)) {
    redirect("/sign-in?callbackUrl=/profile");
  }

  const name = session?.user?.name || "Member";
  const mode = session?.isDev ? "local development identity" : "Entra session";

  return (
    <RoutePlaceholder
      title="Profile"
      description={`${name} is signed in via ${mode}. Profile editing and account management arrive in later identity tasks.`}
    />
  );
}
