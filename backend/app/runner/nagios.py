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
        )

        duration = time.monotonic() - start
        output, perfdata = split_output_and_perfdata(completed.stdout)

        return PluginResult(
            command=command,
            exit_code=completed.returncode,
            status=map_exit_code(completed.returncode),
            output=output,
            perfdata=perfdata,
            stderr=completed.stderr.strip() or None,
            duration_seconds=duration,
            timed_out=False,
        )

    except subprocess.TimeoutExpired as exc:
        duration = time.monotonic() - start
        stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        output, perfdata = split_output_and_perfdata(stdout)

        return PluginResult(
            command=command,
            exit_code=3,
            status=CheckStatus.UNKNOWN,
            output=output or f"Plugin timed out after {timeout_seconds}s",
            perfdata=perfdata,
            stderr=stderr.strip() or None,
            duration_seconds=duration,
            timed_out=True,
        )
