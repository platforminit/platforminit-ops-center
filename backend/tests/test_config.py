"""Tests for the centralized configuration module.

Verifies that ``load_settings()`` returns correct defaults when no
environment variables are set, and that each setting can be overridden
via the corresponding env var.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.config import Settings, _parse_bool, load_settings


# ---------------------------------------------------------------------------
# _parse_bool unit tests
# ---------------------------------------------------------------------------


class TestParseBool:
    """Cover all truthy/falsy inputs for the internal parser."""

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("1", True),
            ("true", True),
            ("TRUE", True),
            ("yes", True),
            ("YES", True),
            ("0", False),
            ("false", False),
            ("FALSE", False),
            ("no", False),
            ("", False),
            (None, False),
            ("anything", False),
        ],
    )
    def test_various_inputs(self, raw: str | None, expected: bool) -> None:
        assert _parse_bool(raw) is expected

    def test_default_used_when_none(self) -> None:
        assert _parse_bool(None, default="true") is True

    def test_default_used_when_empty(self) -> None:
        assert _parse_bool("", default="true") is True


# ---------------------------------------------------------------------------
# Settings defaults (no env vars set)
# ---------------------------------------------------------------------------


class TestSettingsDefaults:
    """When no env vars are set, all settings should use safe defaults."""

    def test_auth_disabled_by_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("OPS_CENTER_AUTH_ENABLED", raising=False)
        assert load_settings().auth_enabled is False

    def test_api_token_none_by_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("OPS_CENTER_API_TOKEN", raising=False)
        assert load_settings().api_token is None

    def test_adhoc_disabled_by_default(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv("OPS_CENTER_ENABLE_ADHOC_CHECKS", raising=False)
        assert load_settings().enable_adhoc_checks is False

    def test_check_results_db_none_by_default(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv("PLATFORMINIT_CHECK_RESULTS_DB", raising=False)
        assert load_settings().check_results_db is None


# ---------------------------------------------------------------------------
# Settings env-override tests
# ---------------------------------------------------------------------------


class TestSettingsEnvOverrides:
    """Each setting should be overridable via its environment variable."""

    def test_auth_enabled_via_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OPS_CENTER_AUTH_ENABLED", "true")
        assert load_settings().auth_enabled is True

    def test_auth_enabled_via_env_1(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OPS_CENTER_AUTH_ENABLED", "1")
        assert load_settings().auth_enabled is True

    def test_api_token_via_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OPS_CENTER_API_TOKEN", "s3cret")
        assert load_settings().api_token == "s3cret"

    def test_api_token_empty_string_becomes_none(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("OPS_CENTER_API_TOKEN", "")
        assert load_settings().api_token is None

    def test_adhoc_enabled_via_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OPS_CENTER_ENABLE_ADHOC_CHECKS", "true")
        assert load_settings().enable_adhoc_checks is True

    def test_check_results_db_via_env(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    ) -> None:
        db_path = tmp_path / "custom.sqlite3"
        monkeypatch.setenv("PLATFORMINIT_CHECK_RESULTS_DB", str(db_path))
        assert load_settings().check_results_db == db_path


# ---------------------------------------------------------------------------
# Settings immutability
# ---------------------------------------------------------------------------


class TestSettingsImmutability:
    """Settings dataclass is frozen — fields cannot be mutated."""

    def test_settings_is_frozen(self) -> None:
        settings = Settings()
        with pytest.raises(AttributeError):
            settings.auth_enabled = True  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Integration: load_settings returns a frozen Settings
# ---------------------------------------------------------------------------


class TestLoadSettingsReturnsFrozen:
    """``load_settings()`` should return a frozen ``Settings`` instance."""

    def test_return_type(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("OPS_CENTER_AUTH_ENABLED", raising=False)
        monkeypatch.delenv("OPS_CENTER_API_TOKEN", raising=False)
        monkeypatch.delenv("OPS_CENTER_ENABLE_ADHOC_CHECKS", raising=False)
        monkeypatch.delenv("PLATFORMINIT_CHECK_RESULTS_DB", raising=False)

        settings = load_settings()
        assert isinstance(settings, Settings)
        with pytest.raises(AttributeError):
            settings.auth_enabled = True  # type: ignore[misc]
