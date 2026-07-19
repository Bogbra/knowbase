# Knowbase — Multi-Agent Knowledge Workspace

A production-grade AI workspace that lets teams upload documents, ask questions, and get answers grounded in their own knowledge base — with inline citations down to the chapter level.

```
Browser
  │  SSE token stream        REST + multipart upload
  ▼                          ▼
Nginx ──────────────────── Next.js Frontend (port 3030)
  │                          │ typed API calls
  ▼                          ▼
FastAPI Backend (port 8000) ── PostgreSQL + pgvector
  │ asyncio.create_task        │
  ▼                          ▼
LangGraph Agent            Redis
  ├─ retrieval_node  ─────────├─ SSE stream buffers (sse:run:{id})
  ├─ web_search_node           ├─ ARQ job queue
  ├─ memory_read_node          └─ rate limit counters
  ├─ synthesize_node
  └─ memory_write_node       ARQ Worker
                               └─ ingest_document_task
                                    download → extract → chunk → embed → store
```

---

## Problem

Teams build knowledge in documents, Notion pages, and PDFs — but can't search across them naturally. Generic AI chat tools (ChatGPT, Claude.ai) have no access to private knowledge, hallucinate sources, and forget everything between sessions.

Existing RAG solutions are either locked behind SaaS pricing or require stitching together five separate services (vector DB, embedding API, queue, storage, auth). There is no self-hostable, production-ready starting point that handles the full pipeline end-to-end.

---

## Approach

Knowbase solves this with a **stateful multi-agent pipeline** built on LangGraph:

1. **Ingest** — documents are uploaded, extracted (PDF/HTML/TXT), chunked at sentence boundaries with overlap, embedded via OpenAI, and stored in PostgreSQL + pgvector. This runs asynchronously via an ARQ worker so uploads return instantly.

2. **Retrieve** — on each user message, a retrieval node and a memory-read node run in parallel. The retrieval node does cosine k-NN search over the user's workspace chunks; the memory node fetches facts the agent has written in previous sessions.

3. **Synthesize** — Claude (or GPT-4o-mini) generates a grounded answer that cites the exact source chunks. Tokens stream to the browser in real time via Server-Sent Events over a Redis stream buffer.

4. **Remember** — after each answer, a lightweight Haiku pass extracts new facts and writes them back as workspace memories, so the agent improves with every conversation.

The entire flow is auditable: every agent run snapshots its LangGraph state to the DB, and every tool call is logged with input, output, and duration.

---

## Run locally

```bash
cp .env.example .env  # add OPENAI_API_KEY
docker-compose up
# → http://localhost:3030
```

Seed data is applied automatically on first run (see below).

---

## Features

- **AI Chat** — Streaming responses token-by-token via SSE, powered by Claude or GPT-4o-mini
- **Strict Grounding** — Answers cite exact source chunks from study materials; uncovered topics are explicitly marked rather than hallucinated
- **Web Search Fallback** — When study material has no matching passage, Tavily web search runs automatically and results are clearly labelled as web sources
- **Document Pipeline** — Upload PDF, TXT, MD, HTML, JSON, Excel (xlsx/xls); automatic chunking + vector embedding via ARQ worker
- **Inline Citations** — Every paragraph cites the source document and chapter verbatim (`*(Quelle: Document, Chapter)*`)
- **Memory** — Agent writes and reads facts across conversations (workspace + global scope)
- **MCP Server** — Standalone FastMCP server exposes the workspace knowledge base to any MCP-compatible AI client (Claude Desktop, Cursor, etc.) via three tools: `search_knowledge`, `list_documents`, `get_document`
- **Personal Access Tokens** — Machine-to-machine auth for MCP and scripts: create `kb_<hex>` tokens scoped to a workspace; SHA-256 hashed at rest, shown once on creation
- **Drag & Drop Upload** — Multi-file drop zone on the documents page
- **Dark Mode** — Toggle in the sidebar, persists to localStorage
- **Workspace Members** — Invite collaborators by email, manage roles (owner / editor / viewer)
- **Conversation Management** — Rename, delete, auto-title on first message
- **Observability** — Prometheus `/metrics`, Sentry integration, structured JSON logs with request IDs
- **Eval Harness** — Golden-dataset evaluation suite: citation accuracy (deterministic, runs on every PR), retrieval recall (embedding-based, nightly CI), LLM-as-judge (optional flag)

---

## Modules

Each workspace has five modules accessible from the sidebar:

### Chat
The main interface. Users type a message and the agent responds in real time — tokens stream word-by-word via SSE. Each answer cites the exact source chunks it was grounded on. The agent remembers facts from previous conversations within the same workspace.

### Documents
Upload and manage the workspace knowledge base. Supported formats: PDF, TXT, Markdown, CSV, HTML, JSON, Excel (xlsx/xls). Each file goes through an async pipeline: extract text → split into chunks → generate vector embeddings → store in pgvector. Status badges (processing / ready / failed) update automatically. Failed documents can be retried without re-uploading.

### Tasks
A Kanban board for workspace-level tasks. Four columns: Open → In Progress → Done → Cancelled. Tasks can be created inline, dragged between columns, and optionally assigned to an agent for automated execution. Animated with Framer Motion.

### Members
Invite collaborators to the workspace by email. Three roles: **Owner** (full control), **Editor** (read + write), **Viewer** (read-only). Members can be removed at any time by the owner.

### Memories
The agent's persistent fact store. After each conversation the agent automatically extracts key facts and saves them here (workspace scope). Memories are embedded and used as additional context in future answers — the longer a workspace is used, the more precise the agent becomes.

---

## MCP Server

Knowbase ships a standalone [Model Context Protocol](https://modelcontextprotocol.io) server (`mcp-server/`) that exposes the workspace knowledge base to any MCP-compatible AI client — Claude Desktop, Cursor, Windsurf, custom agents, etc.

**Three tools:**

| Tool | Description |
|---|---|
| `search_knowledge(query, k=8)` | Semantic search over workspace documents. Returns top-k chunks with source labels. |
| `list_documents()` | List all indexed documents in the workspace. |
| `get_document(document_id)` | Metadata for a specific document. |

**Setup:**

```bash
# 1. Create an API key in the Knowbase UI → Settings → API Keys
#    (scoped to the workspace you want the MCP server to access)

# 2. Configure the MCP server
cd mcp-server
cp .env.example .env
# Set: KNOWBASE_API_URL, KNOWBASE_API_KEY, KNOWBASE_WORKSPACE_ID

# 3. Install and run
uv sync
knowbase-mcp     # starts stdio MCP server

# Or run directly
uv run python -m app.main
```

**Claude Desktop config** (`~/Library/Application Support/Claude/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "knowbase": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/knowbase/mcp-server", "knowbase-mcp"],
      "env": {
        "KNOWBASE_API_URL": "http://localhost:8000",
        "KNOWBASE_API_KEY": "kb_yourtoken"
      }
    }
  }
}
```

The MCP REST endpoints (`POST /mcp/search`, `GET /mcp/documents`) are rate-limited (20 req/min for search, 60/min for document reads) and accept only API key auth — no JWT. The workspace is derived from the key; callers cannot access other workspaces.

---

## Personal Access Tokens (API Keys)

PATs enable machine-to-machine access without going through the browser auth flow.

```bash
# Create a key (JWT required — do this in the Knowbase UI or via curl)
curl -X POST http://localhost:8000/api/v1/auth/api-keys \
  -H "Authorization: Bearer <jwt>" \
  -d '{"name": "My MCP key", "workspace_id": "<uuid>"}'
# → {"key": "kb_<64 hex chars>"}   ← shown once, store it securely

# List active keys
curl http://localhost:8000/api/v1/auth/api-keys \
  -H "Authorization: Bearer <jwt>"

# Revoke
curl -X DELETE http://localhost:8000/api/v1/auth/api-keys/<key-id> \
  -H "Authorization: Bearer <jwt>"
```

Keys are stored as SHA-256 hashes — raw tokens are never persisted. SHA-256 is sufficient here because tokens are 256-bit random (no brute-force risk unlike passwords).

---

## Stack

| Layer | Technology | Version |
|---|---|---|
| Frontend | Next.js App Router, TypeScript strict | 15/16 |
| Styling | Tailwind CSS v4, shadcn/ui primitives | 4.x |
| Server State | TanStack Query | v5 |
| Client State | Zustand | v5 |
| Auth | NextAuth v5 (JWT + refresh tokens) | v5 |
| Backend | FastAPI async | 0.115 |
| Agent | LangGraph stateful graph | 0.2 |
| ORM | SQLAlchemy async + Alembic | 2.0 |
| Validation | Pydantic v2 | 2.x |
| Vector Search | PostgreSQL + pgvector (HNSW cosine) | 0.7 |
| Queue | Redis + ARQ | — |
| Storage | S3-compatible (MinIO for local dev) | — |
| Embeddings | OpenAI `text-embedding-3-small` | — |
| LLM | Anthropic Claude 3 or OpenAI GPT-4o-mini | — |
| MCP Server | FastMCP (stdio transport) | 1.9+ |
| Metrics | Prometheus client | — |
| Errors | Sentry SDK | — |
| Logging | structlog JSON | — |

---

## Quick Start

```bash
# 1. Clone and configure
git clone <repo-url>
cd knowbase
cp .env.example .env
# Edit .env — set OPENAI_API_KEY (required), ANTHROPIC_API_KEY (optional)

# 2. One-command start
docker-compose up

# App:   http://localhost:3030
# API:   http://localhost:8000/docs
# MinIO: http://localhost:9001  (minioadmin / minioadmin)
```

On first run, seed data is applied automatically:
- **Local dev account:** `admin@knowbase.dev` / `Admin1234!` _(local only — change before any deployment)_
- **Demo workspace:** "AI Research 2025" with 2 conversations, 5 memories, 3 tasks

---

## Development (without Docker)

```bash
# Terminal 1 — infrastructure
docker-compose up postgres redis minio minio-init

# Terminal 2 — backend
cd backend
uv sync
uv run alembic upgrade head
uv run fastapi dev app/main.py

# Terminal 3 — worker
cd backend
uv run arq app.workers.arq_settings.WorkerSettings

# Terminal 4 — frontend
cd frontend
npm install
npm run dev
```

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `SECRET_KEY` | ✓ | — | JWT signing key (`openssl rand -hex 32`) |
| `DATABASE_URL` | ✓ | postgres://... | PostgreSQL async URL |
| `REDIS_URL` | ✓ | redis://... | Redis connection URL |
| `OPENAI_API_KEY` | ✓ | — | For embeddings (`text-embedding-3-small`) |
| `OPENAI_AGENT_MODEL` | — | `gpt-4o-mini` | OpenAI chat model |
| `OPENAI_API_BASE` | — | (official) | Custom base URL (e.g. Azure, proxy) |
| `ANTHROPIC_API_KEY` | — | — | If set, used instead of OpenAI for chat |
| `AGENT_MODEL` | — | `claude-3-5-haiku-20241022` | Anthropic model |
| `AGENT_MAX_TOKENS` | — | `4096` | Max tokens per agent response |
| `S3_ENDPOINT_URL` | — | — | S3 endpoint (omit for AWS, set for MinIO) |
| `S3_ACCESS_KEY_ID` | — | — | S3 credentials (omit for local filesystem fallback) |
| `S3_SECRET_ACCESS_KEY` | — | — | S3 credentials |
| `S3_BUCKET_NAME` | — | `knowbase` | S3 bucket |
| `SENTRY_DSN` | — | — | Sentry project DSN |
| `ENVIRONMENT` | — | `development` | `development` / `staging` / `production` |
| `ALLOWED_ORIGINS` | — | `http://localhost:3030` | Comma-separated or JSON-array CORS origins |
| `NEXTAUTH_SECRET` | ✓ (frontend) | — | NextAuth signing secret |
| `NEXTAUTH_URL` | ✓ (frontend) | — | App canonical URL |
| `NEXT_PUBLIC_API_URL` | ✓ (frontend) | — | Backend URL visible to browser |
| `TAVILY_API_KEY` | — | — | Enables web-search fallback when retrieval returns < 3 chunks |
| `TRUST_PROXY_HEADERS` | — | `false` | Set `true` when behind a trusted reverse proxy (Railway, Fly, nginx) |

**MCP server env vars** (set in `mcp-server/.env`):

| Variable | Description |
|---|---|
| `KNOWBASE_API_URL` | Backend base URL, e.g. `http://localhost:8000` |
| `KNOWBASE_API_KEY` | `kb_<hex>` personal access token (workspace is fixed by the key itself) |

---

## Deployment

### Frontend → Vercel

```bash
cd frontend
npx vercel --prod
```

Set environment variables in the Vercel dashboard. The `vercel.json` at the repo root configures security headers and API rewrites.

### Backend → Railway

```bash
railway login
railway link
railway up
```

The `railway.toml` at the repo root defines the API service and worker service. Set all environment variables in the Railway dashboard. Migrations run automatically — `startCommand` is `alembic upgrade head && uvicorn ...`.

### Backend → Fly.io

```bash
fly auth login
fly launch --config fly.toml
fly secrets set SECRET_KEY=$(openssl rand -hex 32) DATABASE_URL=... REDIS_URL=...
fly deploy
```

Migrations run automatically via `fly.toml`'s `release_command` (`alembic upgrade head`), executed on a fresh machine before traffic cuts over to the new release — a schema change can't be forgotten on either platform.

### Production Docker

```bash
cp .env.production.example .env.production
# Fill in all values
docker-compose -f docker-compose.prod.yml up -d
```

Nginx listens on port 80 and handles:
- SSE buffering disabled (`proxy_buffering off`) for the stream endpoint
- Rate limiting at the reverse proxy layer
- Static file caching for frontend assets

### Production Checklist

Items marked **(enforced)** aren't just advice — `Settings` refuses to boot
with `ENVIRONMENT=production` unless they're satisfied (`app/core/config.py`).

- [ ] `SECRET_KEY` — generated with `openssl rand -hex 32`, never reused **(enforced)**
- [ ] `NEXTAUTH_SECRET` — separate secret, also generated fresh
- [ ] `ENVIRONMENT=production` — disables `/docs`, `/redoc`, `/openapi.json`
- [ ] `DEBUG=false`
- [ ] `ALLOWED_ORIGINS` set to actual domain(s), not empty **(enforced)**
- [ ] `TRUST_PROXY_HEADERS=true` when behind Fly/Railway/Nginx — otherwise
      rate limiting keys on the proxy's IP instead of each client's, and
      every user shares one limit
- [ ] Postgres: connection pooling via PgBouncer or Railway's built-in pooler
- [ ] Redis: password set, not exposed publicly
- [ ] S3: bucket policy — private, no public access; `S3_ACCESS_KEY_ID` and
      `S3_SECRET_ACCESS_KEY` both set together, or both left unset for local
      fallback storage **(enforced — partial config rejected at boot)**
- [ ] Sentry DSN configured for both frontend and backend
- [ ] CORS `ALLOWED_ORIGINS` set to actual domain (not `*`)
- [ ] HTTPS enforced (Fly/Railway do this automatically; Nginx config uses HSTS)
- [ ] Migrations run on deploy — already wired for both platforms
      (`railway.toml` `startCommand`, `fly.toml` `release_command`); confirm
      the same is true for any other deploy target before shipping

---

## Development Commands

```bash
# Backend
uv run pytest                  # all tests
uv run mypy --strict .         # type check (must be clean)
uv run ruff check .            # lint
uv run ruff format .           # format
uv run alembic upgrade head    # apply migrations
uv run alembic revision --autogenerate -m "description"  # new migration

# Frontend
npm run type-check             # tsc --noEmit
npm run build                  # production build (must pass)
npm run lint                   # eslint

# MCP server
cd mcp-server
uv sync
uv run pytest                  # 7 unit tests (no network)
knowbase-mcp                   # start stdio MCP server

# CI (run all before push)
cd backend && uv run pytest && uv run mypy --strict . && uv run ruff check .
cd frontend && npm run type-check && npm run build
```

## Eval Harness

A golden-dataset evaluation suite lives in `backend/eval/`. It has three metric levels:

| Metric | When | Cost |
|---|---|---|
| Citation accuracy | Every PR (unit test) | Free — deterministic regex |
| Retrieval recall@8 | Nightly CI | OpenAI embedding call per question |
| LLM-as-judge faithfulness | Optional (`--judge`) | OpenAI/Anthropic call per question |

**Golden dataset:** 37 questions across three German Studienheft texts covering Marketing-Mix, Transaktionskostentheorie, and Organisationsformen. 34 factual/synthesis questions + 3 out-of-domain (expected: no citation).

```bash
cd backend

# Ingest corpus into a fresh eval workspace
uv run python -m eval.runner setup

# Run retrieval recall against a workspace
uv run python -m eval.runner recall --workspace-id <uuid> --k 8

# Check all metrics against baselines (baselines in eval/baselines/scores.json)
uv run python -m eval.runner check
```

Baselines are committed as JSON. CI fails when a metric drops below `baseline − tolerance`. When a score is stable above `baseline + tolerance/2`, the runner prints a ratchet hint to raise the baseline.

The nightly workflow (`.github/workflows/nightly-eval.yml`) runs recall and fails explicitly if `OPENAI_API_KEY` is not set in CI secrets — skipped tests emit a `::warning::` annotation on `main`.

---

## Architecture Decisions

### Repository Pattern (not ActiveRecord)
DB access goes through typed repository classes in `backend/app/db/repositories/`. Route handlers and services never import SQLAlchemy models directly. This makes the data layer independently testable and keeps business logic out of the ORM layer.

### LangGraph (not raw LangChain)
LangGraph provides a stateful graph with explicit node transitions, which makes the agent flow auditable and debuggable. Each run's graph state is snapshotted to `agent_runs.graph_state` so you can replay any conversation step. Raw LangChain chains are harder to introspect and don't support parallel fan-out natively.

### SSE (not WebSockets) for Streaming
SSE is unidirectional (server → browser), which is all we need for token streaming. It works over HTTP/1.1, doesn't require a separate protocol handshake, and is trivially proxied by Nginx. WebSockets would add complexity (connection management, heartbeats, reconnect logic) for no benefit here.

### pgvector (not Pinecone/Weaviate)
Keeps the stack to one database. The HNSW index on `document_chunks.embedding` gives sub-millisecond k-NN queries at this scale. For >10M chunks, a dedicated vector DB would make sense, but the operational overhead isn't justified for an MVP.

### ARQ (not Celery) for Background Jobs
ARQ is async-native (built on asyncio + Redis), lighter than Celery (no broker/backend config split), and integrates cleanly with the FastAPI async stack. Document ingestion is the only background job type, so Celery's feature set is overkill.

### API Key Auth (SHA-256, not bcrypt)
Personal Access Tokens are 256-bit random values (`kb_` + 64 hex chars). They are hashed with SHA-256 before storage and looked up by hash. bcrypt is deliberately not used here: its cost factor is designed to slow brute-force attacks against low-entropy passwords. A 256-bit random token has no brute-force surface — the bottleneck is the search space, not the hash speed. Using bcrypt would add ~100 ms of unnecessary latency to every API call without any security benefit.

### JWT Rotation Strategy
Access tokens (30 min) are stateless JWTs. Refresh tokens are stored in Redis with their JTI — on each refresh, the old token is deleted and a new one issued. This enables single-use refresh tokens: a stolen refresh token can only be used once before it's invalidated by the legitimate user's next refresh.

### Cursor-based Pagination
All list endpoints use `?cursor=` + `?limit=` instead of offset/page. Cursor pagination is stable under concurrent inserts (no skipped rows), consistent across pages, and more efficient on large tables (no `COUNT(*)` or `OFFSET` scan).

---

## Known Limitations

- **No WebSocket support** — Agent runs fire-and-forget via `asyncio.create_task`. If the backend process restarts mid-run, the SSE stream closes. Completed message is still saved to DB.
- **Single-tenant embeddings** — All document chunks in a workspace share the same pgvector table. Cross-workspace isolation is enforced in queries, not at the DB layer.
- **No file virus scanning** — Upload validates MIME type and magic bytes, but does not run ClamAV or equivalent.
- **Memory embeddings** — Memory entries are saved without embeddings; the embedding field is null. Semantic memory search is therefore degraded (falls back to repository scan rather than vector similarity).
- **No re-ranking** — Initial k=25 cosine retrieval is used directly. Adding a cross-encoder re-ranker would improve answer quality for ambiguous queries.
- **Web-search fallback is global, not per sub-query** — Query decomposition can produce up to 5 sub-queries. The web-search trigger (`< 3 relevant chunks`) checks the total retrieved set, not per sub-query. A sub-topic with no document coverage can be missed if other sub-topics supply enough chunks to satisfy the global threshold.
- **Upload buffers entirely in memory** — `await file.read()` loads the full file (up to 10 MB) before streaming to storage. There is no global concurrency cap on uploads, so simultaneous large uploads from different IPs can exhaust container memory. The fix is streaming upload directly to S3/R2 without buffering.
- **API key revocation is creator-only** — `DELETE /auth/api-keys/{id}` filters on `user_id`, so only the key creator can revoke their own key. A workspace owner cannot revoke a key created by another member, even if that key is scoped to their workspace. Sufficient for single-user or trusted-team scenarios; a team product would require owner-level revocation as an additional query path.
- **All workspace roles can create API keys** — Members with Viewer role can issue `kb_` tokens for their workspace. This is intentional: all MCP endpoints are read-only (`search`, `list_documents`, `get_document`), so a Viewer-scoped key cannot write anything. If write tools are ever added to the MCP server, key issuance should be gated on Editor role or above.

---

## Data Protection

Knowbase provides three endpoints for user data control:

### Account deletion — `DELETE /auth/me`

Requires password confirmation in the request body (protection against session hijacking).

**Three-case workspace rule:**

| Situation | Action |
|---|---|
| User is sole member of a workspace | Workspace deleted entirely (DB cascade + S3 files) |
| User is non-owner member of a shared workspace | Membership removed; workspace and other members' data are unaffected |
| User is **owner** of a shared workspace | **409 Conflict** — transfer ownership or delete the workspace first |

Ownership transfer is not implemented to avoid scope creep. S3 files from deleted workspaces are removed in a best-effort loop after the DB commit (failures are logged, not retried). Redis event-streams (`sse:run:{id}`) are not actively purged — they carry a 1 h TTL and expire automatically.

### Data export — `GET /auth/me/export`

Returns a single JSON document containing all user-generated data:

- Profile (id, email, role, created_at)
- Workspace memberships (name + role)
- Conversations and all messages
- Memories (all scopes)
- Document metadata (name, status, mime_type, size — not file contents)
- API key metadata (name, created_at, last_used_at — **never** key hashes or raw keys)

### Memory management — `GET /workspaces/{id}/memories`, `DELETE /memories/{id}`

`GET /workspaces/{id}/memories` lists all agent-extracted memories for a workspace (requires membership). `DELETE /memories/{id}` removes a specific memory (user must be the memory's creator).

**What the memory system collects:** after each AI response, a lightweight extraction pass identifies facts, preferences, and context stated by the user and saves them as workspace-scoped memories. Memories are stored in the `memories` table, visible via the Memories module in the sidebar, and deletable at any time.

---

## Roadmap

- [ ] Re-ranking with FlashRank cross-encoder
- [ ] Full memories browser page
- [ ] Google OAuth provider (NextAuth Google provider is wired, needs client credentials)
- [ ] Grafana dashboard provisioning (`infra/grafana/`)
- [ ] Prometheus alerting rules
- [ ] WebSocket upgrade for lower-latency streaming
- [ ] `/admin/reindex` ARQ task — re-embed all chunks whose `metadata.embedding_model` differs from the current model (enables safe model upgrades without downtime)
- [ ] Per-sub-query web-search fallback — trigger web search for individual sub-queries that return zero results rather than checking the global chunk count
