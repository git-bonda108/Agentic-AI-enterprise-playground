import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { auth } from "@/auth";
import { SIGNED_OUT_AT_COOKIE, sessionIsCurrent } from "@/lib/session-epoch";
import { AppShell } from "@/components/shell/app-shell";

export default async function AppLayout({ children }: { children: React.ReactNode }) {
  const session = await auth();
  if (!session?.user || !sessionIsCurrent(session.signedInAt, (await cookies()).get(SIGNED_OUT_AT_COOKIE)?.value)) redirect("/login");
  const user = {
    name: session.user.name ?? "Playground user",
    email: session.user.email ?? "",
    role: session.user.role,
    department: session.user.department,
    image: session.user.image,
  };
  return <AppShell user={user}>{children}</AppShell>;
}
