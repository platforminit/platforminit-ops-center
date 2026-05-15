from app.runner.models import CheckStatus
from app.runner.nagios import map_exit_code, run_nagios_plugin, split_output_and_perfdata


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
