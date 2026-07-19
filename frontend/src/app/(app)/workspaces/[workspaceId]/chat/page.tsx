"use client";

import { use, useEffect, useRef, useState } from "react";
import { useSession } from "next-auth/react";
import { AnimatePresence, motion } from "framer-motion";
import { Bot, Send, Trash2, User } from "lucide-react";

import {
  useConversations,
  useCreateConversation,
  useMessages,
  useSendMessage,
  useRenameConversation,
} from "@/hooks/useConversations";
import { useSSE } from "@/hooks/useSSE";
import { useChatStore, type SourceDoc } from "@/store/chat";
import { apiClient } from "@/lib/api-client";
import { MarkdownContent } from "@/components/markdown-content";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import type { AgentEvent, Message } from "@/types";
import { useMutation, useQueryClient } from "@tanstack/react-query";

export default function ChatPage({ params }: { params: Promise<{ workspaceId: string }> }) {
  const { workspaceId } = use(params);
  const { data: session } = useSession();

  const conversations = useConversations(workspaceId);
  const createConversation = useCreateConversation(workspaceId);
  const renameConversation = useRenameConversation(workspaceId);
  const qc = useQueryClient();

  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);

  useEffect(() => {
    if (conversations.data && conversations.data.length > 0) {
      setActiveConversationId((prev) => prev ?? conversations.data[0]!.id);
    }
  }, [conversations.data]);

  const messages = useMessages(activeConversationId);
  const sendMessage = useSendMessage(activeConversationId);
  const { connect } = useSSE();

  const deleteConversation = useMutation({
    mutationFn: (id: string) =>
      apiClient.delete<void>(`/api/v1/conversations/${id}`, session?.accessToken),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["conversations", workspaceId] });
      setActiveConversationId(null);
    },
  });

  const {
    streamingText,
    isStreaming,
    agentEvents,
    sources,
    startStream,
    appendToken,
    addEvent,
    setSources,
    finishStream,
  } = useChatStore();

  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.data, streamingText]);

  // Auto-select first conversation after delete
  useEffect(() => {
    if (!activeConversationId && conversations.data && conversations.data.length > 0) {
      setActiveConversationId(conversations.data[0]!.id);
    }
  }, [activeConversationId, conversations.data]);

  async function handleCreateConversation() {
    const conv = await createConversation.mutateAsync("New conversation");
    setActiveConversationId(conv.id);
  }

  async function handleSend() {
    const content = input.trim();
    if (!content || !activeConversationId || isStreaming) return;
    setInput("");

    const { run_id } = await sendMessage.mutateAsync(content);
    await messages.refetch();
    // Backend auto-renames: refresh conversation list to show new title
    void conversations.refetch();

    if (run_id && session?.accessToken) {
      startStream(run_id);
      connect(
        `/api/v1/conversations/${activeConversationId}/stream?run_id=${run_id}`,
        session.accessToken,
        (event: AgentEvent) => {
          if (event.type === "token") appendToken(event.data.text);
          else if (event.type === "sources") setSources(event.data.documents);
          else addEvent(event);
        },
        () => {
          finishStream();
          void messages.refetch();
        },
      );
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void handleSend();
    }
  }

  const activeConversation = conversations.data?.find((c) => c.id === activeConversationId);
  const [editingTitle, setEditingTitle] = useState(false);
  const [titleInput, setTitleInput] = useState("");

  function startEditTitle() {
    if (!activeConversation) return;
    setTitleInput(activeConversation.title);
    setEditingTitle(true);
  }

  async function saveTitle() {
    if (!activeConversationId || !titleInput.trim()) {
      setEditingTitle(false);
      return;
    }
    await renameConversation.mutateAsync({
      conversationId: activeConversationId,
      title: titleInput.trim(),
    });
    setEditingTitle(false);
  }

  const messageList = messages.data ?? [];
  const hasConversation = !!activeConversationId;
  const noConversations = !conversations.isLoading && conversations.data?.length === 0;

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      {/* Conversation tabs */}
      <div className="flex items-center gap-2 border-b border-border px-4 py-2">
        <div className="flex flex-1 items-center gap-1 overflow-x-auto">
          {conversations.data?.map((conv) => (
            <button
              key={conv.id}
              onClick={() => setActiveConversationId(conv.id)}
              className={cn(
                "whitespace-nowrap rounded px-3 py-1 text-sm transition-colors",
                conv.id === activeConversationId
                  ? "bg-accent text-accent-foreground font-medium"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              {conv.title}
            </button>
          ))}
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleCreateConversation}
          disabled={createConversation.isPending}
        >
          + Neu
        </Button>
      </div>

      {/* Active conversation header */}
      {hasConversation && activeConversation && (
        <div className="flex items-center gap-2 border-b border-border px-6 py-2">
          {editingTitle ? (
            <input
              autoFocus
              value={titleInput}
              onChange={(e) => setTitleInput(e.target.value)}
              onBlur={() => void saveTitle()}
              onKeyDown={(e) => {
                if (e.key === "Enter") void saveTitle();
                if (e.key === "Escape") setEditingTitle(false);
              }}
              className="flex-1 rounded border border-ring bg-background px-2 py-0.5 text-sm focus:outline-none"
            />
          ) : (
            <button
              onClick={startEditTitle}
              className="flex-1 text-left text-sm font-medium hover:text-muted-foreground truncate"
              title="Klicken zum Umbenennen"
            >
              {activeConversation.title}
            </button>
          )}
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 text-muted-foreground hover:text-destructive"
            onClick={() => void deleteConversation.mutateAsync(activeConversationId)}
            disabled={deleteConversation.isPending}
            title="Gespräch löschen"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
        </div>
      )}

      {/* Message list */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        {noConversations && (
          <div className="flex flex-col items-center justify-center h-full gap-4 text-center">
            <Bot className="h-12 w-12 text-muted-foreground" />
            <p className="font-medium">Gespräch starten</p>
            <p className="text-sm text-muted-foreground max-w-sm">
              Stelle Fragen zu deinen Dokumenten, lass dir Zusammenfassungen erstellen oder
              delegiere Aufgaben an den KI-Agenten.
            </p>
            <Button onClick={handleCreateConversation}>Erstes Gespräch erstellen</Button>
          </div>
        )}

        {hasConversation && messages.isLoading && (
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className={cn("flex gap-3", i % 2 === 0 && "flex-row-reverse")}>
                <Skeleton className="h-8 w-8 rounded-full" />
                <Skeleton className="h-16 max-w-xs flex-1 rounded-lg" />
              </div>
            ))}
          </div>
        )}

        {hasConversation && !messages.isLoading && (
          <div className="space-y-4">
            <AnimatePresence initial={false}>
              {messageList.map((msg) => (
                <MessageBubble key={msg.id} message={msg} />
              ))}
            </AnimatePresence>

            {isStreaming && agentEvents.length > 0 && (
              <div className="space-y-1 pl-11">
                {agentEvents
                  .filter((r) => r.event.type === "thinking" || r.event.type === "tool_call")
                  .slice(-3)
                  .map((r) => (
                    <AgentEventRow key={r.id} event={r.event} />
                  ))}
              </div>
            )}

            {isStreaming && (
              <div className="flex gap-3">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground">
                  <Bot className="h-4 w-4" />
                </div>
                <div className="max-w-prose space-y-2">
                  <div className="rounded-lg bg-muted px-4 py-3 text-sm">
                    {streamingText ? (
                      <MarkdownContent content={streamingText} />
                    ) : (
                      <span className="flex gap-1">
                        <span className="animate-bounce">·</span>
                        <span className="animate-bounce delay-100">·</span>
                        <span className="animate-bounce delay-200">·</span>
                      </span>
                    )}
                  </div>
                  {sources.length > 0 && <SourcesList sources={sources} />}
                </div>
              </div>
            )}

            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* Input bar */}
      {hasConversation && (
        <div className="border-t border-border p-4">
          <div className="flex items-end gap-3">
            <Textarea
              placeholder="Frage stellen… (Enter zum Senden, Shift+Enter für neue Zeile)"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isStreaming || sendMessage.isPending}
              className="min-h-[60px] max-h-[200px] resize-none flex-1"
              rows={2}
            />
            <Button
              onClick={() => void handleSend()}
              disabled={!input.trim() || isStreaming || sendMessage.isPending}
              size="icon"
              className="h-[60px] w-10 shrink-0"
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2, ease: "easeOut" }}
      className={cn("flex gap-3", isUser && "flex-row-reverse")}
    >
      <div
        className={cn(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
          isUser ? "bg-secondary" : "bg-primary text-primary-foreground",
        )}
      >
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>
      <div
        className={cn(
          "max-w-prose rounded-lg px-4 py-3 text-sm",
          isUser ? "bg-secondary text-secondary-foreground" : "bg-muted",
        )}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap">{message.content}</p>
        ) : (
          <MarkdownContent content={message.content} />
        )}
      </div>
    </motion.div>
  );
}

function AgentEventRow({ event }: { event: AgentEvent }) {
  if (event.type === "thinking") {
    return <p className="text-xs text-muted-foreground italic">⟳ {event.data.step}</p>;
  }
  if (event.type === "tool_call") {
    return <p className="text-xs text-muted-foreground">⚙ {event.data.name}</p>;
  }
  return null;
}

function stripExt(name: string): string {
  return name.replace(/\.[^.]+$/, "");
}

function shortChapter(chapter: string): string {
  const m = chapter.match(/^\d+(?:\.\d+)*/);
  return m ? m[0] : chapter.slice(0, 20);
}

function SourcesList({ sources }: { sources: SourceDoc[] }) {
  if (sources.length === 0) return null;
  return (
    <div className="flex flex-wrap items-center gap-1.5 pt-1">
      <span className="text-xs text-muted-foreground">Quellen:</span>
      {sources.map((s, i) => (
        <span
          key={`${s.document_id}-${i}`}
          className="inline-flex items-center gap-1 rounded border border-border bg-muted/60 px-2 py-0.5 text-xs text-muted-foreground"
        >
          📄{" "}
          <span className="font-medium text-foreground">
            {stripExt(s.document_name)}
            {s.chapter && `, Kap. ${shortChapter(s.chapter)}`}
          </span>
        </span>
      ))}
    </div>
  );
}
