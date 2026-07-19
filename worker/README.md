# Worker

Standalone ARQ scaffold (separate `uv` workspace from `backend/`). It is **not** the worker
that actually runs — this project's `app/main.py` `WorkerSettings.functions` is intentionally
still `[]` (`# tasks registered here in later phases`), and its `pyproject.toml` doesn't carry
the dependencies (`sqlalchemy`, `openai`, `pypdf`, `openpyxl`, `boto3`, ...) the real tasks need.

Both `docker-compose.yml` and `worker/railway.toml` deploy the worker service from the
**`backend/`** Docker context, running `app.workers.arq_settings.WorkerSettings` —
the real task registry: `functions = [run_agent_task, ingest_document_task]`
(`backend/app/workers/arq_settings.py`).

If this project is ever meant to become the real worker, it needs the actual task
dependencies added and `WorkerSettings.functions` wired to the real implementations —
until then, treat `worker/Dockerfile` and `worker/app/main.py` as an unused scaffold.
