"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { signOut, useSession } from "next-auth/react";
import {
  ArrowLeft,
  Brain,
  CheckSquare,
  FileText,
  MessageSquare,
  Moon,
  Sun,
  Users,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { useTheme } from "@/lib/theme";
import { cn } from "@/lib/utils";

interface WorkspaceSidebarProps {
  workspaceId: string;
  workspaceName: string;
}

const NAV_ITEMS = [
  { label: "Chat", href: "chat", icon: MessageSquare },
  { label: "Dokumente", href: "documents", icon: FileText },
  { label: "Aufgaben", href: "tasks", icon: CheckSquare },
  { label: "Mitglieder", href: "members", icon: Users },
  { label: "Erinnerungen", href: "memories", icon: Brain },
];

export function WorkspaceSidebar({ workspaceId, workspaceName }: WorkspaceSidebarProps) {
  const pathname = usePathname();
  const { data: session } = useSession();
  const { dark, toggle } = useTheme();

  return (
    <aside className="flex h-full w-56 flex-col border-r border-border bg-card">
      <div className="flex items-center gap-2 border-b border-border px-4 py-3">
        <Link
          href="/workspaces"
          className="text-muted-foreground hover:text-foreground transition-colors"
          aria-label="Alle Workspaces"
        >
          <ArrowLeft className="h-4 w-4" />
        </Link>
        <span className="truncate font-medium text-sm">{workspaceName}</span>
      </div>

      <nav className="flex-1 space-y-1 p-2">
        {NAV_ITEMS.map(({ label, href, icon: Icon }) => {
          const to = `/workspaces/${workspaceId}/${href}`;
          const active = pathname === to;
          return (
            <Link
              key={href}
              href={to}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
                active
                  ? "bg-accent text-accent-foreground font-medium"
                  : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-border p-4 space-y-2">
        <button
          className="w-full flex items-center gap-2 rounded-md border border-border bg-muted/40 px-2.5 py-1.5 text-xs text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
          onClick={() =>
            window.dispatchEvent(
              new KeyboardEvent("keydown", { key: "k", metaKey: true, bubbles: true }),
            )
          }
        >
          <span className="flex-1 text-left">Suchen…</span>
          <kbd className="rounded border border-border px-1 font-mono text-[10px]">⌘K</kbd>
        </button>
        <p className="truncate text-xs text-muted-foreground">{session?.user?.email ?? ""}</p>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            className="flex-1 justify-start text-xs"
            onClick={() => void signOut({ callbackUrl: "/login" })}
          >
            Abmelden
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 shrink-0 text-muted-foreground"
            onClick={toggle}
            title={dark ? "Helles Design" : "Dunkles Design"}
          >
            {dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </Button>
        </div>
      </div>
    </aside>
  );
}
