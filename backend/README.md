# Backend

See the [repo root README](../README.md) for architecture, setup, and deployment.

## Decisions log

- **`code_execute` agent tool removed (not shipped).** An earlier prototype tool
  ran arbitrary Python in a subprocess behind an import-name blocklist
  (`_BLOCKED_MODULES`). It was never wired into `agents/orchestrator.py` — no
  live RCE path existed — but the blocklist itself was trivially bypassable
  (`__import__("os")`, `().__class__.__bases__`, etc.) and its own docstring
  said as much. Rather than ship an unreachable tool that invites a future
  contributor to wire it in without addressing the sandboxing, it was deleted
  outright. If code execution becomes a real requirement, it needs a proper
  sandbox (e.g. gVisor/Firecracker), not a regex blocklist.
