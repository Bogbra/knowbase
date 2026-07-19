"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSession } from "next-auth/react";

import { ApiError, apiClient } from "@/lib/api-client";
import type { WorkspaceMember, WorkspaceMemberRole } from "@/types";

export function useMembers(workspaceId: string) {
  const { data: session } = useSession();
  const token = session?.accessToken;

  return useQuery({
    queryKey: ["members", workspaceId],
    queryFn: () =>
      apiClient.get<WorkspaceMember[]>(`/api/v1/workspaces/${workspaceId}/members`, token),
    enabled: !!token && !!workspaceId,
  });
}

export function useInviteMember(workspaceId: string) {
  const { data: session } = useSession();
  const token = session?.accessToken;
  const qc = useQueryClient();

  return useMutation({
    mutationFn: (args: { email: string; role: WorkspaceMemberRole }) =>
      apiClient.post<WorkspaceMember>(
        `/api/v1/workspaces/${workspaceId}/members/invite`,
        args,
        token,
      ),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["members", workspaceId] }),
  });
}

export function useRemoveMember(workspaceId: string) {
  const { data: session } = useSession();
  const token = session?.accessToken;
  const qc = useQueryClient();

  return useMutation({
    mutationFn: async (userId: string) => {
      try {
        await apiClient.delete<void>(`/api/v1/workspaces/${workspaceId}/members/${userId}`, token);
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) return;
        throw err;
      }
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["members", workspaceId] }),
  });
}
