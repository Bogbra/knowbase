"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSession } from "next-auth/react";

import { ApiError, apiClient, parseErrorResponse } from "@/lib/api-client";
import type { Document } from "@/types";

const BASE_URL = process.env["NEXT_PUBLIC_API_URL"] ?? "http://localhost:8000";

export function useDocuments(workspaceId: string) {
  const { data: session } = useSession();
  const token = session?.accessToken;

  return useQuery({
    queryKey: ["documents", workspaceId],
    queryFn: () => apiClient.get<Document[]>(`/api/v1/workspaces/${workspaceId}/documents`, token),
    enabled: !!token && !!workspaceId,
    // Poll every 4s while any document is still being processed
    refetchInterval: (query) => {
      const docs = query.state.data;
      if (!docs) return false;
      return docs.some((d) => d.status === "pending" || d.status === "processing") ? 4000 : false;
    },
  });
}

export function useUploadDocument(workspaceId: string) {
  const { data: session } = useSession();
  const token = session?.accessToken;
  const qc = useQueryClient();

  return useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;
      const res = await fetch(`${BASE_URL}/api/v1/workspaces/${workspaceId}/documents/upload`, {
        method: "POST",
        headers,
        body: formData,
      });
      if (!res.ok) throw await parseErrorResponse(res);
      return res.json() as Promise<Document>;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["documents", workspaceId] }),
  });
}

export function useDeleteDocument(workspaceId: string) {
  const { data: session } = useSession();
  const token = session?.accessToken;
  const qc = useQueryClient();

  return useMutation({
    mutationFn: async (documentId: string) => {
      try {
        await apiClient.delete<void>(`/api/v1/documents/${documentId}`, token);
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) return;
        throw err;
      }
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["documents", workspaceId] }),
  });
}

export function useRequeueDocument(workspaceId: string) {
  const { data: session } = useSession();
  const token = session?.accessToken;
  const qc = useQueryClient();

  return useMutation({
    mutationFn: (documentId: string) =>
      apiClient.post<Document>(`/api/v1/documents/${documentId}/requeue`, {}, token),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["documents", workspaceId] }),
  });
}
