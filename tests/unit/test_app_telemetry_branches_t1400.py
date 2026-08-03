"""T-1400 branch-gap closure for `frob.app.telemetry.tips_disabled`.

`tests/test_telemetry.py::test_detect_footguns_returns_empty_when_tips_disabled`
already covers the `FROB_NO_FOOTGUN_TIPS=1` branch (opt-out via the
footgun-specific env var). This file targets the other three: telemetry
itself disabled (`is_disabled()` short-circuit), the default/unset case
(neither env var set -- tips enabled), and an explicit `"0"`/`"false"`
opt-back-in value for the footgun-specific var.
"""

from __future__ import annotations

import pytest

from frob.app.telemetry import tips_disabled


class TestTipsDisabledTelemetryOff:
    """The `if is_disabled(): return True` short-circuit branch."""

    def test_telemetry_disabled_short_circuits_true(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`FROB_NO_TELEMETRY=1` alone (footgun var unset) is enough to
        disable tips -- no corpus, no detection, regardless of the
        footgun-specific flag."""
        monkeypatch.setenv("FROB_NO_TELEMETRY", "1")
        monkeypatch.delenv("FROB_NO_FOOTGUN_TIPS", raising=False)
        assert tips_disabled() is True


class TestTipsDisabledDefaultEnabled:
    """The default (both env vars unset/falsy) case -- tips stay enabled."""

    def test_neither_env_set_tips_enabled(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """With telemetry on and no footgun opt-out, tips are enabled."""
        monkeypatch.delenv("FROB_NO_TELEMETRY", raising=False)
        monkeypatch.delenv("FROB_NO_FOOTGUN_TIPS", raising=False)
        assert tips_disabled() is False

    @pytest.mark.parametrize("falsy_value", ["0", "false", "False", ""])
    def test_explicit_falsy_footgun_value_tips_enabled(
        self, monkeypatch: pytest.MonkeyPatch, falsy_value: str
    ) -> None:
        """An explicit `"0"`/`"false"`/empty `FROB_NO_FOOTGUN_TIPS` value is
        the opt-back-in case -- tips stay enabled, same as unset."""
        monkeypatch.delenv("FROB_NO_TELEMETRY", raising=False)
        monkeypatch.setenv("FROB_NO_FOOTGUN_TIPS", falsy_value)
        assert tips_disabled() is False
