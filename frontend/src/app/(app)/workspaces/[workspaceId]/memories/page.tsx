"use client";

import { Brain, Trash2 } from "lucide-react";

import { useMemories, useDeleteMemory } from "@/hooks/useMemories";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { Memory, MemoryScope } from "@/types";

const SCOPE_VARIANT: Record<MemoryScope, "default" | "secondary" | "outline"> = {
  global: "default",
  workspace: "secondary",
  session: "outline",
};

const SCOPE_LABEL: Record<MemoryScope, string> = {
  global: "Global",
  workspace: "Workspace",
  session: "Session",
};

export default function MemoriesPage() {
  const { data: memories, isLoading } = useMemories();
  const deleteMemory = useDeleteMemory();

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <div className="border-b border-border px-6 py-4">
        <h2 className="font-semibold">KI-Erinnerungen</h2>
        <p className="text-xs text-muted-foreground">
          Fakten, die der KI-Agent aus Gesprächen gelernt hat.
        </p>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        {isLoading && (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-20 rounded-lg" />
            ))}
          </div>
        )}

        {!isLoading && (!memories || memories.length === 0) && (
          <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-border py-20 text-center">
            <Brain className="mb-3 h-10 w-10 text-muted-foreground" />
            <p className="font-medium">Noch keine Erinnerungen</p>
            <p className="mt-1 text-sm text-muted-foreground">
              Der KI-Agent speichert wichtige Fakten aus euren Gesprächen automatisch.
            </p>
          </div>
        )}

        {!isLoading && memories && memories.length > 0 && (
          <div className="space-y-3">
            {memories.map((memory) => (
              <MemoryCard
                key={memory.id}
                memory={memory}
                onDelete={() => void deleteMemory.mutateAsync(memory.id)}
                deleting={deleteMemory.isPending}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function MemoryCard({
  memory,
  onDelete,
  deleting,
}: {
  memory: Memory;
  onDelete: () => void;
  deleting: boolean;
}) {
  return (
    <div className="flex gap-4 rounded-lg border border-border bg-card px-4 py-3">
      <Brain className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
      <div className="flex-1 min-w-0">
        <p className="text-sm leading-relaxed">{memory.content}</p>
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <Badge variant={SCOPE_VARIANT[memory.scope]}>{SCOPE_LABEL[memory.scope]}</Badge>
          {memory.tags.map((tag) => (
            <span
              key={tag}
              className="rounded bg-accent px-1.5 py-0.5 text-xs text-accent-foreground"
            >
              {tag}
            </span>
          ))}
          <span className="text-xs text-muted-foreground ml-auto">
            {new Date(memory.created_at).toLocaleDateString("de-DE")}
          </span>
        </div>
      </div>
      <Button
        variant="ghost"
        size="icon"
        className="h-8 w-8 shrink-0 text-muted-foreground hover:text-destructive"
        onClick={onDelete}
        disabled={deleting}
        aria-label="Erinnerung löschen"
      >
        <Trash2 className="h-4 w-4" />
      </Button>
    </div>
  );
}
