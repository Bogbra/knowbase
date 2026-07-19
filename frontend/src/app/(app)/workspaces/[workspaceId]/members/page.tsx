"use client";

import { use, useState } from "react";
import { Crown, Eye, Pencil, Trash2, UserPlus, Users } from "lucide-react";

import { useMembers, useInviteMember, useRemoveMember } from "@/hooks/useMembers";
import { useSession } from "next-auth/react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { WorkspaceMember, WorkspaceMemberRole } from "@/types";

const ROLE_ICON: Record<WorkspaceMemberRole, React.ReactNode> = {
  owner: <Crown className="h-3.5 w-3.5" />,
  editor: <Pencil className="h-3.5 w-3.5" />,
  viewer: <Eye className="h-3.5 w-3.5" />,
};

const ROLE_VARIANT: Record<WorkspaceMemberRole, "default" | "secondary" | "outline"> = {
  owner: "default",
  editor: "secondary",
  viewer: "outline",
};

export default function MembersPage({ params }: { params: Promise<{ workspaceId: string }> }) {
  const { workspaceId } = use(params);
  const { data: session } = useSession();
  const { data: members, isLoading } = useMembers(workspaceId);
  const invite = useInviteMember(workspaceId);
  const remove = useRemoveMember(workspaceId);

  const [email, setEmail] = useState("");
  const [role, setRole] = useState<WorkspaceMemberRole>("viewer");

  const currentUserId = session?.user?.id as string | undefined;
  const isOwner = members?.some((m) => m.user_id === currentUserId && m.role === "owner");

  async function handleInvite(e: React.FormEvent) {
    e.preventDefault();
    if (!email.trim()) return;
    await invite.mutateAsync({ email: email.trim(), role });
    setEmail("");
  }

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <div className="border-b border-border px-6 py-4">
        <h2 className="font-semibold">Mitglieder</h2>
        <p className="text-xs text-muted-foreground">Verwalte den Zugriff auf diesen Workspace.</p>
      </div>

      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {/* Invite form — only for owners */}
        {isOwner && (
          <form
            onSubmit={(e) => void handleInvite(e)}
            className="flex gap-2 rounded-lg border border-border bg-card p-4"
          >
            <input
              type="email"
              placeholder="E-Mail-Adresse"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="flex-1 rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              required
            />
            <select
              value={role}
              onChange={(e) => setRole(e.target.value as WorkspaceMemberRole)}
              className="rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            >
              <option value="viewer">Betrachter</option>
              <option value="editor">Bearbeiter</option>
            </select>
            <Button type="submit" disabled={invite.isPending || !email.trim()}>
              <UserPlus className="h-4 w-4" />
              {invite.isPending ? "Einladen…" : "Einladen"}
            </Button>
          </form>
        )}

        {invite.isError && (
          <p className="text-sm text-destructive">
            {invite.error instanceof Error ? invite.error.message : "Fehler beim Einladen"}
          </p>
        )}

        {/* Member list */}
        {isLoading && (
          <div className="space-y-3">
            {[1, 2].map((i) => (
              <Skeleton key={i} className="h-14 rounded-lg" />
            ))}
          </div>
        )}

        {!isLoading && (!members || members.length === 0) && (
          <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-border py-20 text-center">
            <Users className="mb-3 h-10 w-10 text-muted-foreground" />
            <p className="font-medium">Keine Mitglieder gefunden</p>
          </div>
        )}

        {!isLoading && members && members.length > 0 && (
          <div className="space-y-2">
            {members.map((member) => (
              <MemberRow
                key={member.id}
                member={member}
                canRemove={!!isOwner && member.role !== "owner"}
                onRemove={() => void remove.mutateAsync(member.user_id)}
                removing={remove.isPending}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function MemberRow({
  member,
  canRemove,
  onRemove,
  removing,
}: {
  member: WorkspaceMember;
  canRemove: boolean;
  onRemove: () => void;
  removing: boolean;
}) {
  return (
    <div className="flex items-center gap-4 rounded-lg border border-border bg-card px-4 py-3">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-muted text-sm font-medium">
        {member.user_email?.[0]?.toUpperCase() ?? "?"}
      </div>
      <div className="flex-1 min-w-0">
        <p className="truncate text-sm font-medium">{member.user_email ?? member.user_id}</p>
        <p className="text-xs text-muted-foreground">
          Beigetreten {new Date(member.joined_at).toLocaleDateString("de-DE")}
        </p>
      </div>
      <Badge variant={ROLE_VARIANT[member.role]} className="flex items-center gap-1">
        {ROLE_ICON[member.role]}
        {member.role}
      </Badge>
      {canRemove && (
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 text-muted-foreground hover:text-destructive"
          onClick={onRemove}
          disabled={removing}
          aria-label="Mitglied entfernen"
        >
          <Trash2 className="h-4 w-4" />
        </Button>
      )}
    </div>
  );
}
