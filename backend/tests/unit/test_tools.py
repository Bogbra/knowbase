"""Tests for agent tools: code_execute and vector_search."""

import pytest

from app.agents.tools.code_execute import CodeResult, code_execute


@pytest.mark.asyncio
async def test_code_execute_simple() -> None:
    result = await code_execute("print('hello')")
    assert result.exit_code == 0
    assert "hello" in result.stdout
    assert result.timed_out is False


@pytest.mark.asyncio
async def test_code_execute_math() -> None:
    result = await code_execute("print(2 + 2)")
    assert result.exit_code == 0
    assert "4" in result.stdout


@pytest.mark.asyncio
async def test_code_execute_blocked_os() -> None:
    result = await code_execute("import os\nprint(os.getcwd())")
    assert result.exit_code == 1
    assert "Blocked" in result.stderr
    assert "os" in result.stderr


@pytest.mark.asyncio
async def test_code_execute_blocked_subprocess() -> None:
    result = await code_execute("import subprocess\nsubprocess.run(['ls'])")
    assert result.exit_code == 1
    assert "Blocked" in result.stderr


@pytest.mark.asyncio
async def test_code_execute_syntax_error() -> None:
    result = await code_execute("def broken(::\n  pass")
    assert result.exit_code != 0


@pytest.mark.asyncio
async def test_code_execute_timeout() -> None:
    result = await code_execute("while True: pass", timeout_s=1)
    assert result.timed_out is True
    assert result.exit_code == 124


@pytest.mark.asyncio
async def test_code_execute_blocked_from_import() -> None:
    result = await code_execute("from os import path")
    assert result.exit_code == 1
    assert "Blocked" in result.stderr


def test_code_result_dataclass() -> None:
    r = CodeResult(stdout="out", stderr="err", exit_code=0, timed_out=False)
    assert r.stdout == "out"
    assert r.exit_code == 0
    assert r.timed_out is False
