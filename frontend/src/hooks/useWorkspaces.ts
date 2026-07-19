"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSession } from "next-auth/react";

import { apiClient } from "@/lib/api-client";
import type { Workspace } from "@/types";

export function useWorkspaces() {
  const { data: session } = useSession();
  const token = session?.accessToken;

  return useQuery({
    queryKey: ["workspaces"],
    queryFn: () => apiClient.get<Workspace[]>("/api/v1/workspaces", token),
    enabled: !!token,
  });
}

export function useCreateWorkspace() {
  const { data: session } = useSession();
  const token = session?.accessToken;
  const qc = useQueryClient();

  return useMutation({
    mutationFn: (name: string) => apiClient.post<Workspace>("/api/v1/workspaces", { name }, token),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["workspaces"] }),
  });
}
