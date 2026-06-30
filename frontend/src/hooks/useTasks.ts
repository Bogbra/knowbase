"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSession } from "next-auth/react";

import { apiClient } from "@/lib/api-client";
import type { Task, TaskStatus } from "@/types";

export function useTasks(workspaceId: string) {
  const { data: session } = useSession();
  const token = session?.accessToken;

  return useQuery({
    queryKey: ["tasks", workspaceId],
    queryFn: () => apiClient.get<Task[]>(`/api/v1/workspaces/${workspaceId}/tasks`, token),
    enabled: !!token && !!workspaceId,
  });
}

export function useCreateTask(workspaceId: string) {
  const { data: session } = useSession();
  const token = session?.accessToken;
  const qc = useQueryClient();

  return useMutation({
    mutationFn: (args: { title: string; description?: string }) =>
      apiClient.post<Task>("/api/v1/tasks", { workspace_id: workspaceId, ...args }, token),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tasks", workspaceId] }),
  });
}

export function useUpdateTask(workspaceId: string) {
  const { data: session } = useSession();
  const token = session?.accessToken;
  const qc = useQueryClient();

  return useMutation({
    mutationFn: (args: { taskId: string; status?: TaskStatus; title?: string }) =>
      apiClient.patch<Task>(
        `/api/v1/tasks/${args.taskId}`,
        { status: args.status, title: args.title },
        token,
      ),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tasks", workspaceId] }),
  });
}

export function useDeleteTask(workspaceId: string) {
  const { data: session } = useSession();
  const token = session?.accessToken;
  const qc = useQueryClient();

  return useMutation({
    mutationFn: (taskId: string) => apiClient.delete<void>(`/api/v1/tasks/${taskId}`, token),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tasks", workspaceId] }),
  });
}
