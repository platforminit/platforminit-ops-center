from __future__ import annotations

import subprocess
import time

from app.runner.models import CheckStatus, PluginResult

EXIT_CODE_STATUS_MAP = {
    0: CheckStatus.OK,
    1: CheckStatus.WARNING,
    2: CheckStatus.CRITICAL,
    3: CheckStatus.UNKNOWN,
}

# Maximum number of characters to capture from stdout and stderr.
_MAX_CAPTURE_CHARS = 8192

# Minimal safe environment for plugin execution.
_SAFE_ENV: dict[str, str] = {
    "PATH": "/usr/lib/nagios/plugins:/usr/bin:/bin",
    "LC_ALL": "C.UTF-8",
}


def map_exit_code(exit_code: int) -> CheckStatus:
    return EXIT_CODE_STATUS_MAP.get(exit_code, CheckStatus.UNKNOWN)


def split_output_and_perfdata(raw_output: str) -> tuple[str, str | None]:
    first_line = raw_output.strip().splitlines()[0] if raw_output.strip() else ""

    if "|" not in first_line:
        return first_line, None

    output, perfdata = first_line.split("|", 1)
    return output.strip(), perfdata.strip() or None


def run_nagios_plugin(command: list[str], timeout_seconds: int = 10) -> PluginResult:
    start = time.monotonic()

    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
            env=_SAFE_ENV,
            cwd="/",
        )

        duration = time.monotonic() - start

        # Cap captured output to prevent unbounded memory usage.
        capped_stdout = completed.stdout[:_MAX_CAPTURE_CHARS] if completed.stdout else ""
        capped_stderr = completed.stderr[:_MAX_CAPTURE_CHARS] if completed.stderr else ""

        output, perfdata = split_output_and_perfdata(capped_stdout)

        return PluginResult(
            command=command,
            exit_code=completed.returncode,
            status=map_exit_code(completed.returncode),
            output=output,
            perfdata=perfdata,
            stderr=capped_stderr.strip() or None,
            duration_seconds=duration,
            timed_out=False,
        )

    except subprocess.TimeoutExpired as exc:
        duration = time.monotonic() - start
        stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")

        # Cap captured output.
        capped_stdout = stdout[:_MAX_CAPTURE_CHARS]
        capped_stderr = stderr[:_MAX_CAPTURE_CHARS]

        output, perfdata = split_output_and_perfdata(capped_stdout)

        return PluginResult(
            command=command,
            exit_code=3,
            status=CheckStatus.UNKNOWN,
            output=output or f"Plugin timed out after {timeout_seconds}s",
            perfdata=perfdata,
            stderr=capped_stderr.strip() or None,
            duration_seconds=duration,
            timed_out=True,
        )
