import { create } from "zustand";

import type { AgentEvent, SourceDoc } from "@/types";

interface AgentEventRecord {
  id: number;
  event: AgentEvent;
}

export type { SourceDoc };

interface ChatState {
  conversationId: string | null;
  streamingText: string;
  isStreaming: boolean;
  agentEvents: AgentEventRecord[];
  sources: SourceDoc[];
  runId: string | null;
  setConversation: (id: string) => void;
  startStream: (runId: string) => void;
  appendToken: (text: string) => void;
  addEvent: (event: AgentEvent) => void;
  setSources: (docs: SourceDoc[]) => void;
  finishStream: () => void;
  reset: () => void;
}

let _counter = 0;

export const useChatStore = create<ChatState>()((set) => ({
  conversationId: null,
  streamingText: "",
  isStreaming: false,
  agentEvents: [],
  sources: [],
  runId: null,

  setConversation: (id) => set({ conversationId: id }),
  startStream: (runId) =>
    set({ isStreaming: true, streamingText: "", agentEvents: [], sources: [], runId }),
  appendToken: (text) => set((s) => ({ streamingText: s.streamingText + text })),
  addEvent: (event) =>
    set((s) => ({
      agentEvents: [...s.agentEvents, { id: _counter++, event }],
    })),
  setSources: (docs) => set({ sources: docs }),
  finishStream: () => set({ isStreaming: false }),
  reset: () =>
    set({ streamingText: "", isStreaming: false, agentEvents: [], sources: [], runId: null }),
}));
