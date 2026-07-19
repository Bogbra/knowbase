"use client";

import { useCallback, useRef, useState } from "react";

import type { AgentEvent } from "@/types";

const BASE_URL = process.env["NEXT_PUBLIC_API_URL"] ?? "http://localhost:8000";

interface UseSSEResult {
  isStreaming: boolean;
  connect: (
    path: string,
    token: string,
    onEvent: (e: AgentEvent) => void,
    onDone: () => void,
  ) => void;
  disconnect: () => void;
}

export function useSSE(): UseSSEResult {
  const [isStreaming, setIsStreaming] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const disconnect = useCallback(() => {
    abortRef.current?.abort();
    setIsStreaming(false);
  }, []);

  const connect = useCallback(
    (path: string, token: string, onEvent: (e: AgentEvent) => void, onDone: () => void) => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      setIsStreaming(true);

      void (async () => {
        try {
          const res = await fetch(`${BASE_URL}${path}`, {
            headers: { Authorization: `Bearer ${token}` },
            signal: controller.signal,
          });

          if (!res.ok || !res.body) {
            setIsStreaming(false);
            return;
          }

          const reader = res.body.getReader();
          const decoder = new TextDecoder();
          let buffer = "";

          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");
            buffer = lines.pop() ?? "";

            for (const line of lines) {
              if (!line.startsWith("data: ")) continue;
              const json = line.slice(6).trim();
              if (!json) continue;
              try {
                const event = JSON.parse(json) as AgentEvent;
                onEvent(event);
                if (event.type === "done" || event.type === "error") {
                  setIsStreaming(false);
                  onDone();
                  return;
                }
              } catch {
                // skip malformed SSE lines
              }
            }
          }
        } catch (err) {
          if (err instanceof Error && err.name !== "AbortError") {
            setIsStreaming(false);
          }
        } finally {
          if (!controller.signal.aborted) {
            setIsStreaming(false);
          }
        }
      })();
    },
    [],
  );

  return { isStreaming, connect, disconnect };
}
