"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import { Brain, CheckSquare, FileText, MessageSquare, Search, Users, X } from "lucide-react";

import { cn } from "@/lib/utils";

interface CommandItem {
  id: string;
  label: string;
  description?: string;
  icon: React.ReactNode;
  href: string;
}

function buildCommands(workspaceId: string): CommandItem[] {
  return [
    {
      id: "chat",
      label: "Chat öffnen",
      description: "KI-Assistent für deine Dokumente",
      icon: <MessageSquare className="h-4 w-4" />,
      href: `/workspaces/${workspaceId}/chat`,
    },
    {
      id: "documents",
      label: "Dokumente",
      description: "Dateien hochladen und verwalten",
      icon: <FileText className="h-4 w-4" />,
      href: `/workspaces/${workspaceId}/documents`,
    },
    {
      id: "tasks",
      label: "Aufgaben",
      description: "Kanban-Board für dein Team",
      icon: <CheckSquare className="h-4 w-4" />,
      href: `/workspaces/${workspaceId}/tasks`,
    },
    {
      id: "members",
      label: "Mitglieder",
      description: "Workspace-Zugang verwalten",
      icon: <Users className="h-4 w-4" />,
      href: `/workspaces/${workspaceId}/members`,
    },
    {
      id: "memories",
      label: "Erinnerungen",
      description: "Agent-Gedächtnis anzeigen",
      icon: <Brain className="h-4 w-4" />,
      href: `/workspaces/${workspaceId}/memories`,
    },
    {
      id: "workspaces",
      label: "Alle Workspaces",
      description: "Workspace-Übersicht",
      icon: <Search className="h-4 w-4" />,
      href: "/workspaces",
    },
  ];
}

interface CommandPaletteProps {
  workspaceId: string;
}

export function CommandPalette({ workspaceId }: CommandPaletteProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState(0);
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);

  const commands = buildCommands(workspaceId);
  const filtered = commands.filter(
    (c) =>
      c.label.toLowerCase().includes(query.toLowerCase()) ||
      c.description?.toLowerCase().includes(query.toLowerCase()),
  );

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setOpen((prev) => !prev);
        setQuery("");
        setSelected(0);
      }
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 50);
  }, [open]);

  useEffect(() => {
    setSelected(0);
  }, [query]);

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelected((s) => Math.min(s + 1, filtered.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelected((s) => Math.max(s - 1, 0));
    } else if (e.key === "Enter" && filtered[selected]) {
      navigate(filtered[selected].href);
    }
  }

  function navigate(href: string) {
    setOpen(false);
    setQuery("");
    router.push(href);
  }

  return (
    <>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="fixed inset-0 z-50 flex items-start justify-center pt-[15vh] px-4"
            onClick={() => setOpen(false)}
          >
            {/* backdrop */}
            <div className="absolute inset-0 bg-background/60 backdrop-blur-sm" />

            <motion.div
              initial={{ opacity: 0, scale: 0.97, y: -8 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.97, y: -8 }}
              transition={{ duration: 0.15 }}
              className="relative z-10 w-full max-w-md rounded-2xl border border-border bg-card shadow-2xl overflow-hidden"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Search input */}
              <div className="flex items-center gap-3 border-b border-border px-4 py-3">
                <Search className="h-4 w-4 shrink-0 text-muted-foreground" />
                <input
                  ref={inputRef}
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Suchen oder navigieren…"
                  className="flex-1 bg-transparent text-sm focus:outline-none placeholder:text-muted-foreground"
                />
                <button
                  onClick={() => setOpen(false)}
                  className="text-muted-foreground hover:text-foreground transition-colors"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              {/* Results */}
              <div className="max-h-72 overflow-y-auto py-2">
                {filtered.length === 0 ? (
                  <p className="px-4 py-6 text-center text-sm text-muted-foreground">
                    Keine Ergebnisse
                  </p>
                ) : (
                  filtered.map((item, i) => (
                    <button
                      key={item.id}
                      className={cn(
                        "flex w-full items-center gap-3 px-4 py-2.5 text-left transition-colors",
                        i === selected ? "bg-accent text-accent-foreground" : "hover:bg-accent/50",
                      )}
                      onMouseEnter={() => setSelected(i)}
                      onClick={() => navigate(item.href)}
                    >
                      <span className="shrink-0 text-muted-foreground">{item.icon}</span>
                      <div className="min-w-0">
                        <p className="text-sm font-medium truncate">{item.label}</p>
                        {item.description && (
                          <p className="text-xs text-muted-foreground truncate">
                            {item.description}
                          </p>
                        )}
                      </div>
                    </button>
                  ))
                )}
              </div>

              {/* Footer */}
              <div className="border-t border-border px-4 py-2 flex items-center gap-3 text-xs text-muted-foreground">
                <span>
                  <kbd className="rounded border border-border px-1 py-0.5 font-mono text-xs">
                    ↑↓
                  </kbd>{" "}
                  Navigieren
                </span>
                <span>
                  <kbd className="rounded border border-border px-1 py-0.5 font-mono text-xs">
                    ↵
                  </kbd>{" "}
                  Öffnen
                </span>
                <span>
                  <kbd className="rounded border border-border px-1 py-0.5 font-mono text-xs">
                    Esc
                  </kbd>{" "}
                  Schließen
                </span>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
