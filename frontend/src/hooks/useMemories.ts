"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSession } from "next-auth/react";

import { ApiError, apiClient } from "@/lib/api-client";
import type { Memory } from "@/types";

export function useMemories() {
  const { data: session } = useSession();
  const token = session?.accessToken;

  return useQuery({
    queryKey: ["memories"],
    queryFn: () => apiClient.get<Memory[]>("/api/v1/memories", token),
    enabled: !!token,
  });
}

export function useDeleteMemory() {
  const { data: session } = useSession();
  const token = session?.accessToken;
  const qc = useQueryClient();

  return useMutation({
    mutationFn: async (memoryId: string) => {
      try {
        await apiClient.delete<void>(`/api/v1/memories/${memoryId}`, token);
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) return;
        throw err;
      }
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["memories"] }),
  });
}
