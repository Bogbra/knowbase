// ── Agent SSE Events ────────────────────────────────────────
export interface TokenUsage {
  input_tokens: number;
  output_tokens: number;
}

export interface SourceDoc {
  document_id: string;
  document_name: string;
  chapter: string;
}

export type AgentEvent =
  | { type: "thinking"; data: { step: string; agent: string } }
  | { type: "tool_call"; data: { name: string; input: unknown; agent: string } }
  | {
      type: "tool_result";
      data: { name: string; output: unknown; status: "ok" | "error"; duration_ms: number };
    }
  | { type: "token"; data: { text: string } }
  | { type: "sources"; data: { documents: SourceDoc[] } }
  | { type: "done"; data: { message_id: string; usage: TokenUsage } }
  | { type: "error"; data: { code: string; message: string } };

// ── Auth ────────────────────────────────────────────────────
export type UserRole = "admin" | "user";

export interface User {
  id: string;
  email: string;
  role: UserRole;
  created_at: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
}

// ── Workspace ───────────────────────────────────────────────
export type WorkspaceMemberRole = "owner" | "editor" | "viewer";

export interface WorkspaceMember {
  id: string;
  workspace_id: string;
  user_id: string;
  role: WorkspaceMemberRole;
  joined_at: string;
  user_email: string | null;
}

export interface Workspace {
  id: string;
  name: string;
  owner_id: string;
  created_at: string;
}

// ── Conversation & Messages ──────────────────────────────────
export type MessageRole = "user" | "assistant" | "system";

export interface Message {
  id: string;
  conversation_id: string;
  role: MessageRole;
  content: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface Conversation {
  id: string;
  workspace_id: string;
  user_id: string;
  title: string;
  created_at: string;
}

// ── Documents ───────────────────────────────────────────────
export type DocumentStatus = "pending" | "processing" | "ready" | "failed";

export interface Document {
  id: string;
  workspace_id: string;
  name: string;
  status: DocumentStatus;
  s3_key: string;
  mime_type: string;
  created_at: string;
}

// ── Memory ──────────────────────────────────────────────────
export type MemoryScope = "session" | "workspace" | "global";

export interface Memory {
  id: string;
  user_id: string;
  workspace_id: string | null;
  scope: MemoryScope;
  content: string;
  tags: string[];
  created_at: string;
}

// ── Tasks ───────────────────────────────────────────────────
export type TaskStatus = "pending" | "in_progress" | "completed" | "cancelled" | "failed";

export interface Task {
  id: string;
  workspace_id: string;
  title: string;
  status: TaskStatus;
  assigned_agent: string | null;
  created_by: string;
  created_at: string;
}

// ── Pagination ──────────────────────────────────────────────
export interface CursorPage<T> {
  items: T[];
  next_cursor: string | null;
  has_more: boolean;
}

// ── Error (RFC 7807) ─────────────────────────────────────────
export interface ProblemDetail {
  type: string;
  title: string;
  status: number;
  detail: string;
  instance: string;
}
