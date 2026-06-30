"""Python code execution with module blocklist and strict timeout.

Note: this is a best-effort blocklist, not a true sandbox. Do not expose
this tool to untrusted users in production without a proper sandbox (e.g. gVisor).
"""

from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass

_BLOCKED_MODULES = frozenset(
    {
        "os",
        "subprocess",
        "sys",
        "shutil",
        "pathlib",
        "socket",
        "requests",
        "httpx",
        "urllib",
        "ftplib",
        "smtplib",
        "importlib",
        "ctypes",
        "cffi",
        "builtins",
        "__import__",
    }
)

_IMPORT_RE = __import__("re").compile(r"^\s*(?:import|from)\s+(\w+)", __import__("re").MULTILINE)


@dataclass
class CodeResult:
    stdout: str
    stderr: str
    exit_code: int
    timed_out: bool


def _check_blocked(code: str) -> str | None:
    """Return the first blocked module name found, or None if clean."""
    for match in _IMPORT_RE.finditer(code):
        module: str = str(match.group(1))
        if module in _BLOCKED_MODULES:
            return module
    return None


async def code_execute(code: str, timeout_s: int = 10) -> CodeResult:
    """Run Python code in a subprocess with a hard timeout.

    Only pure-Python, no filesystem/network/os access. Returns stdout/stderr.
    """
    blocked = _check_blocked(code)
    if blocked:
        return CodeResult(
            stdout="",
            stderr=f"Blocked: import of '{blocked}' is not allowed",
            exit_code=1,
            timed_out=False,
        )

    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            "-c",
            code,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=float(timeout_s)
            )
            return CodeResult(
                stdout=stdout_bytes.decode(errors="replace")[:8192],
                stderr=stderr_bytes.decode(errors="replace")[:2048],
                exit_code=proc.returncode or 0,
                timed_out=False,
            )
        except TimeoutError:
            proc.kill()
            await proc.wait()
            return CodeResult(
                stdout="",
                stderr=f"Execution timed out after {timeout_s}s",
                exit_code=124,
                timed_out=True,
            )
    except Exception as exc:
        return CodeResult(
            stdout="",
            stderr=f"Execution error: {exc}",
            exit_code=1,
            timed_out=False,
        )
