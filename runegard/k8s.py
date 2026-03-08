"""Thin kubectl wrapper with output capture."""

import subprocess
import time

from runegard.models import CommandResult


def execute(command: str, timeout: int = 30, dry_run: bool = False) -> CommandResult:
    """Execute a shell command and capture output."""
    if dry_run:
        return CommandResult(
            stdout=f"[DRY RUN] Would execute: {command}",
            stderr="",
            exit_code=0,
            command=command,
            duration_ms=0,
        )

    start = time.time()
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        duration_ms = int((time.time() - start) * 1000)
        return CommandResult(
            stdout=result.stdout,
            stderr=result.stderr,
            exit_code=result.returncode,
            command=command,
            duration_ms=duration_ms,
        )
    except subprocess.TimeoutExpired:
        duration_ms = int((time.time() - start) * 1000)
        return CommandResult(
            stdout="",
            stderr=f"Command timed out after {timeout}s",
            exit_code=-1,
            command=command,
            duration_ms=duration_ms,
        )
