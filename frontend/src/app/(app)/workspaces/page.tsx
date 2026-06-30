"use client";

import { useState } from "react";
import Link from "next/link";
import { signOut } from "next-auth/react";
import { FolderOpen, Plus } from "lucide-react";

import { useWorkspaces, useCreateWorkspace } from "@/hooks/useWorkspaces";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";

export default function WorkspacesPage() {
  const { data: workspaces, isLoading } = useWorkspaces();
  const createWorkspace = useCreateWorkspace();
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const [createError, setCreateError] = useState("");

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    const name = newName.trim();
    if (!name) return;
    setCreateError("");
    try {
      await createWorkspace.mutateAsync(name);
      setNewName("");
      setCreating(false);
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : "Failed to create workspace");
    }
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
          <h1 className="text-xl font-semibold">Knowbase</h1>
          <Button variant="ghost" size="sm" onClick={() => void signOut({ callbackUrl: "/login" })}>
            Sign out
          </Button>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-6 py-10">
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold">Workspaces</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Select a workspace or create a new one.
            </p>
          </div>
          <Button onClick={() => setCreating(true)}>
            <Plus className="h-4 w-4" />
            New Workspace
          </Button>
        </div>

        {creating && (
          <form
            onSubmit={handleCreate}
            className="mb-6 flex flex-col gap-3 rounded-lg border border-border bg-card p-4"
          >
            <div className="flex items-center gap-3">
              <Input
                autoFocus
                placeholder="Workspace name"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                className="max-w-xs"
              />
              <Button type="submit" disabled={createWorkspace.isPending || !newName.trim()}>
                {createWorkspace.isPending ? "Creating…" : "Create"}
              </Button>
              <Button
                type="button"
                variant="ghost"
                onClick={() => {
                  setCreating(false);
                  setNewName("");
                  setCreateError("");
                }}
              >
                Cancel
              </Button>
            </div>
            {createError && <p className="text-sm text-destructive">{createError}</p>}
          </form>
        )}

        {isLoading && (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-32 rounded-lg" />
            ))}
          </div>
        )}

        {!isLoading && workspaces?.length === 0 && (
          <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-border py-20 text-center">
            <FolderOpen className="mb-3 h-10 w-10 text-muted-foreground" />
            <p className="font-medium">No workspaces yet</p>
            <p className="mt-1 text-sm text-muted-foreground">Create one to get started.</p>
          </div>
        )}

        {!isLoading && workspaces && workspaces.length > 0 && (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {workspaces.map((ws) => (
              <Link
                key={ws.id}
                href={`/workspaces/${ws.id}/chat`}
                className="group flex flex-col gap-2 rounded-lg border border-border bg-card p-5 transition-colors hover:border-foreground/20 hover:bg-accent"
              >
                <div className="flex items-start justify-between">
                  <FolderOpen className="h-6 w-6 text-muted-foreground group-hover:text-foreground transition-colors" />
                </div>
                <p className="font-semibold leading-tight">{ws.name}</p>
                <p className="text-xs text-muted-foreground">
                  {new Date(ws.created_at).toLocaleDateString()}
                </p>
              </Link>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
