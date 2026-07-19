import { auth } from "@/lib/auth";
import { apiClient } from "@/lib/api-client";
import { CommandPalette } from "@/components/command-palette"; // Client Component — safe to import in Server Component
import { WorkspaceSidebar } from "@/components/workspace-sidebar";
import type { Workspace } from "@/types";

export default async function WorkspaceLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ workspaceId: string }>;
}) {
  const [session, { workspaceId }] = await Promise.all([auth(), params]);

  let workspaceName = workspaceId;
  if (session?.accessToken) {
    try {
      const ws = await apiClient.get<Workspace>(
        `/api/v1/workspaces/${workspaceId}`,
        session.accessToken,
      );
      workspaceName = ws.name;
    } catch {
      // fallback to ID if fetch fails
    }
  }

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <WorkspaceSidebar workspaceId={workspaceId} workspaceName={workspaceName} />
      <main className="flex flex-1 flex-col overflow-hidden">{children}</main>
      <CommandPalette workspaceId={workspaceId} />
    </div>
  );
}
