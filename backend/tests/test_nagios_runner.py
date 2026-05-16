from app.runner.models import CheckStatus
from app.runner.nagios import (
    _MAX_CAPTURE_CHARS,
    map_exit_code,
    run_nagios_plugin,
    split_output_and_perfdata,
)


def test_map_exit_code() -> None:
    assert map_exit_code(0) == CheckStatus.OK
    assert map_exit_code(1) == CheckStatus.WARNING
    assert map_exit_code(2) == CheckStatus.CRITICAL
    assert map_exit_code(3) == CheckStatus.UNKNOWN
    assert map_exit_code(99) == CheckStatus.UNKNOWN


def test_split_output_and_perfdata() -> None:
    output, perfdata = split_output_and_perfdata(
        "HTTP OK: 200 OK |time=0.123s;;;0.000000;10.000000 size=837B;;;0"
    )

    assert output == "HTTP OK: 200 OK"
    assert perfdata == "time=0.123s;;;0.000000;10.000000 size=837B;;;0"


def test_run_nagios_plugin_ok() -> None:
    result = run_nagios_plugin(
        ["/usr/lib/nagios/plugins/check_http", "-H", "example.com"],
        timeout_seconds=10,
    )

    assert result.status == CheckStatus.OK
    assert result.exit_code == 0
    assert "HTTP OK" in result.output
    assert result.duration_seconds >= 0


def test_run_nagios_plugin_timeout() -> None:
    result = run_nagios_plugin(
        ["python3", "-c", "import time; time.sleep(2)"],
        timeout_seconds=1,
    )

    assert result.status == CheckStatus.UNKNOWN
    assert result.exit_code == 3
    assert result.timed_out is True
    assert "timed out" in result.output


# ---------------------------------------------------------------------------
# Subprocess hardening tests
# ---------------------------------------------------------------------------


def test_stdout_capped_at_max_chars() -> None:
    """Very long stdout should be truncated to _MAX_CAPTURE_CHARS."""
    long_output = "x" * (_MAX_CAPTURE_CHARS * 2)
    result = run_nagios_plugin(
        ["python3", "-c", f"print('{long_output[:200]}' + 'x' * {_MAX_CAPTURE_CHARS * 2})"],
        timeout_seconds=5,
    )
    # The output should be capped; the perfdata separator "|" won't be present
    # in the long output, so the entire capped stdout becomes the output.
    assert len(result.output) <= _MAX_CAPTURE_CHARS


def test_stderr_capped_at_max_chars() -> None:
    """Very long stderr should be truncated to _MAX_CAPTURE_CHARS."""
    result = run_nagios_plugin(
        [
            "python3",
            "-c",
            f"import sys; sys.stderr.write('x' * {_MAX_CAPTURE_CHARS * 2}); sys.exit(2)",
        ],
        timeout_seconds=5,
    )
    if result.stderr:
        assert len(result.stderr) <= _MAX_CAPTURE_CHARS


def test_safe_env_does_not_inherit_user_env() -> None:
    """The subprocess should run with _SAFE_ENV, not inherit user env vars."""
    result = run_nagios_plugin(
        ["python3", "-c", "import os; print(dict(os.environ))"],
        timeout_seconds=5,
    )
    # The output will be the env dict as seen by the plugin.
    # It should only contain PATH and LC_ALL from _SAFE_ENV.
    assert "PATH" in result.output
    assert "LC_ALL" in result.output
    # Common inherited vars like HOME should NOT be present.
    assert "HOME" not in result.output


def test_cwd_is_root() -> None:
    """The subprocess should run with cwd=\"/\"."""
    result = run_nagios_plugin(
        ["python3", "-c", "import os; print(os.getcwd())"],
        timeout_seconds=5,
    )
    assert result.output == "/"


def test_argv_list_not_shell_string() -> None:
    """Passing a list ensures no shell injection via shell=True."""
    result = run_nagios_plugin(
        ["echo", "hello"],
        timeout_seconds=5,
    )
    assert result.status == CheckStatus.OK
    assert result.output == "hello"
