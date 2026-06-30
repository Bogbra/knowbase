import { redirect } from "next/navigation";
import { auth } from "@/lib/auth";
import { ErrorBoundary } from "@/components/error-boundary";

export default async function AppLayout({ children }: { children: React.ReactNode }) {
  const session = await auth();
  if (!session || session.error === "RefreshTokenError") redirect("/login");
  return <ErrorBoundary>{children}</ErrorBoundary>;
}
