"use client";

import { use, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { CheckCircle2, Circle, Loader2, Plus, Trash2, XCircle } from "lucide-react";

import { useTasks, useCreateTask, useUpdateTask, useDeleteTask } from "@/hooks/useTasks";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import type { Task, TaskStatus } from "@/types";

const COLUMNS: { status: TaskStatus; label: string; color: string }[] = [
  { status: "pending", label: "Offen", color: "border-t-slate-400" },
  { status: "in_progress", label: "In Arbeit", color: "border-t-blue-500" },
  { status: "completed", label: "Erledigt", color: "border-t-green-500" },
  { status: "cancelled", label: "Abgebrochen", color: "border-t-rose-400" },
];

const STATUS_ICON: Record<TaskStatus, React.ReactNode> = {
  pending: <Circle className="h-3.5 w-3.5 text-slate-400" />,
  in_progress: <Loader2 className="h-3.5 w-3.5 text-blue-500 animate-spin" />,
  completed: <CheckCircle2 className="h-3.5 w-3.5 text-green-500" />,
  cancelled: <XCircle className="h-3.5 w-3.5 text-rose-400" />,
  failed: <XCircle className="h-3.5 w-3.5 text-destructive" />,
};

export default function TasksPage({ params }: { params: Promise<{ workspaceId: string }> }) {
  const { workspaceId } = use(params);
  const tasks = useTasks(workspaceId);
  const createTask = useCreateTask(workspaceId);
  const updateTask = useUpdateTask(workspaceId);
  const deleteTask = useDeleteTask(workspaceId);

  const [newTitle, setNewTitle] = useState("");
  const [addingTo, setAddingTo] = useState<TaskStatus | null>(null);

  const byStatus = (status: TaskStatus) => (tasks.data ?? []).filter((t) => t.status === status);

  async function handleCreate(_status: TaskStatus) {
    const title = newTitle.trim();
    if (!title) return;
    setNewTitle("");
    setAddingTo(null);
    await createTask.mutateAsync({ title });
  }

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <div className="border-b border-border px-6 py-4">
        <h1 className="text-lg font-semibold">Aufgaben</h1>
        <p className="text-sm text-muted-foreground mt-0.5">
          {tasks.data?.length ?? 0} Aufgaben insgesamt
        </p>
      </div>

      <div className="flex flex-1 gap-4 overflow-x-auto p-6">
        {COLUMNS.map(({ status, label, color }) => (
          <motion.div
            key={status}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2 }}
            className="flex w-72 shrink-0 flex-col rounded-xl border border-border bg-muted/30"
          >
            {/* Column header */}
            <div
              className={cn(
                "border-t-2 rounded-t-xl px-4 py-3 flex items-center justify-between",
                color,
              )}
            >
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium">{label}</span>
                <span className="rounded-full bg-border px-1.5 py-0.5 text-xs text-muted-foreground">
                  {byStatus(status).length}
                </span>
              </div>
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6 text-muted-foreground hover:text-foreground"
                onClick={() => setAddingTo(addingTo === status ? null : status)}
              >
                <Plus className="h-3.5 w-3.5" />
              </Button>
            </div>

            {/* New task input */}
            <AnimatePresence>
              {addingTo === status && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  className="overflow-hidden px-3 pt-3"
                >
                  <div className="rounded-lg border border-border bg-background p-2">
                    <input
                      autoFocus
                      placeholder="Aufgabentitel..."
                      value={newTitle}
                      onChange={(e) => setNewTitle(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") void handleCreate(status);
                        if (e.key === "Escape") {
                          setAddingTo(null);
                          setNewTitle("");
                        }
                      }}
                      className="w-full bg-transparent text-sm focus:outline-none"
                    />
                    <div className="mt-2 flex gap-1.5">
                      <Button
                        size="sm"
                        className="h-6 text-xs px-2"
                        onClick={() => void handleCreate(status)}
                        disabled={!newTitle.trim() || createTask.isPending}
                      >
                        Hinzufügen
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        className="h-6 text-xs px-2"
                        onClick={() => {
                          setAddingTo(null);
                          setNewTitle("");
                        }}
                      >
                        Abbrechen
                      </Button>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Task cards */}
            <div className="flex flex-col gap-2 p-3 flex-1 overflow-y-auto">
              {tasks.isLoading ? (
                Array.from({ length: 2 }).map((_, i) => (
                  <Skeleton key={i} className="h-16 w-full rounded-lg" />
                ))
              ) : (
                <AnimatePresence mode="popLayout">
                  {byStatus(status).map((task) => (
                    <TaskCard
                      key={task.id}
                      task={task}
                      onMove={(newStatus) =>
                        void updateTask.mutateAsync({ taskId: task.id, status: newStatus })
                      }
                      onDelete={() => void deleteTask.mutateAsync(task.id)}
                    />
                  ))}
                </AnimatePresence>
              )}
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}

function TaskCard({
  task,
  onMove,
  onDelete,
}: {
  task: Task;
  onMove: (status: TaskStatus) => void;
  onDelete: () => void;
}) {
  const nextStatuses = COLUMNS.map((c) => c.status).filter((s) => s !== task.status);

  return (
    <motion.div
      layout
      initial={{ opacity: 0, scale: 0.96 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.96 }}
      transition={{ duration: 0.15 }}
      className="group relative rounded-lg border border-border bg-background p-3 shadow-sm hover:shadow-md transition-shadow"
    >
      <div className="flex items-start gap-2">
        <span className="mt-0.5 shrink-0">{STATUS_ICON[task.status]}</span>
        <p className="flex-1 text-sm leading-snug">{task.title}</p>
        <Button
          variant="ghost"
          size="icon"
          className="h-6 w-6 shrink-0 opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-destructive transition-opacity"
          onClick={onDelete}
        >
          <Trash2 className="h-3 w-3" />
        </Button>
      </div>

      {/* Move to column buttons */}
      <div className="mt-2 flex flex-wrap gap-1">
        {nextStatuses.map((s) => {
          const col = COLUMNS.find((c) => c.status === s);
          return (
            <button
              key={s}
              onClick={() => onMove(s)}
              className="rounded px-1.5 py-0.5 text-xs text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
            >
              → {col?.label}
            </button>
          );
        })}
      </div>
    </motion.div>
  );
}
