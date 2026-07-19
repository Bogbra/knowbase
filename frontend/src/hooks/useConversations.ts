"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSession } from "next-auth/react";

import { apiClient } from "@/lib/api-client";
import type { Conversation, Message } from "@/types";

interface MessageSentRead {
  message: Message;
  run_id: string | null;
}

export function useConversations(workspaceId: string) {
  const { data: session } = useSession();
  const token = session?.accessToken;

  return useQuery({
    queryKey: ["conversations", workspaceId],
    queryFn: () =>
      apiClient.get<Conversation[]>(`/api/v1/workspaces/${workspaceId}/conversations`, token),
    enabled: !!token && !!workspaceId,
  });
}

export function useCreateConversation(workspaceId: string) {
  const { data: session } = useSession();
  const token = session?.accessToken;
  const qc = useQueryClient();

  return useMutation({
    mutationFn: (title: string) =>
      apiClient.post<Conversation>(
        "/api/v1/conversations",
        { workspace_id: workspaceId, title },
        token,
      ),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["conversations", workspaceId] }),
  });
}

export function useMessages(conversationId: string | null) {
  const { data: session } = useSession();
  const token = session?.accessToken;

  return useQuery({
    queryKey: ["messages", conversationId],
    queryFn: () =>
      apiClient.get<Message[]>(`/api/v1/conversations/${conversationId}/messages`, token),
    enabled: !!token && !!conversationId,
  });
}

export function useSendMessage(conversationId: string | null) {
  const { data: session } = useSession();
  const token = session?.accessToken;

  return useMutation({
    mutationFn: (content: string) =>
      apiClient.post<MessageSentRead>(
        `/api/v1/conversations/${conversationId}/messages`,
        { content },
        token,
      ),
  });
}

export function useRenameConversation(workspaceId: string) {
  const { data: session } = useSession();
  const token = session?.accessToken;
  const qc = useQueryClient();

  return useMutation({
    mutationFn: ({ conversationId, title }: { conversationId: string; title: string }) =>
      apiClient.patch<Conversation>(`/api/v1/conversations/${conversationId}`, { title }, token),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["conversations", workspaceId] }),
  });
}
