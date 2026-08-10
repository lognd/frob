"""T-1584: `frob profile show`/`frob profile downgrade` CLI wiring
(`frob.app.profile_runner`) -- wires `frob.tickets._profile.
effective_profile`/`downgrade_profile_ratchet` to a real CLI entrypoint,
neither of which had one before this ticket (T-1575's own WIRE001-waived
follow-up)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from frob.app.config import AppConfig
from frob.app.profile_runner import run
from frob.tickets._profile import ProfileName, _RatchetState, _write_ratchet


def _json_records(caplog: pytest.LogCaptureFixture) -> list[dict]:
    """Every JSON-shaped log record's parsed payload, matching
    `frob debt`'s own `--json`-via-logger test convention
    (tests/test_debt_runner.py)."""
    return [
        json.loads(r.message)
        for r in caplog.records
        if r.message.startswith("{") or r.message.startswith("[")
    ]


class TestProfileRunnerShow:
    """`frob profile show`: read-only, reports configured vs effective."""

    def test_show_reports_configured_and_effective(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests tests/unit/test_profile_runner.py::TestProfileRunnerShow.test_show_reports_configured_and_effective  # noqa: E501
        cfg = AppConfig(
            profile_command="show", profile_path=tmp_path, profile_json=False
        )
        with caplog.at_level("INFO"):
            run(cfg)
        assert "configured=standard" in caplog.text
        assert "effective=standard" in caplog.text

    def test_show_json_mode(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests tests/unit/test_profile_runner.py::TestProfileRunnerShow.test_show_json_mode  # noqa: E501
        cfg = AppConfig(
            profile_command="show", profile_path=tmp_path, profile_json=True
        )
        with caplog.at_level("INFO"):
            run(cfg)
        payloads = _json_records(caplog)
        assert len(payloads) == 1
        assert payloads[0] == {
            "configured": "standard",
            "effective": "standard",
            "ratcheted": False,
        }

    def test_bare_profile_defaults_to_show(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests tests/unit/test_profile_runner.py::TestProfileRunnerShow.test_bare_profile_defaults_to_show  # noqa: E501
        """`frob profile` with no sub-action (`profile_command=None`) is
        `show`, never a no-op or an error."""
        cfg = AppConfig(profile_command=None, profile_path=tmp_path)
        with caplog.at_level("INFO"):
            run(cfg)
        assert "configured=standard" in caplog.text

    def test_show_reports_a_real_ratchet(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests tests/unit/test_profile_runner.py::TestProfileRunnerShow.test_show_reports_a_real_ratchet  # noqa: E501
        (tmp_path / "frob.toml").write_text(
            '[profile]\nprofile = "rapid"\n', encoding="utf-8"
        )
        _write_ratchet(
            tmp_path,
            _RatchetState(
                ratcheted_to=ProfileName.STANDARD.value,
                reason="test trip",
                at=datetime.now(timezone.utc).isoformat(),
            ),
        )
        cfg = AppConfig(
            profile_command="show", profile_path=tmp_path, profile_json=True
        )
        with caplog.at_level("INFO"):
            run(cfg)
        payloads = _json_records(caplog)
        assert payloads[0] == {
            "configured": "rapid",
            "effective": "standard",
            "ratcheted": True,
        }


class TestProfileRunnerDowngrade:
    """`frob profile downgrade --reason TEXT`: the ONLY sanctioned caller
    of `downgrade_profile_ratchet`."""

    def test_downgrade_requires_a_reason(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_profile_runner.py::TestProfileRunnerDowngrade.test_downgrade_requires_a_reason  # noqa: E501
        cfg = AppConfig(profile_command="downgrade", profile_path=tmp_path)
        with pytest.raises(SystemExit) as exc:
            run(cfg)
        assert exc.value.code == 1

    def test_downgrade_and_reason_file_are_mutually_exclusive(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/test_profile_runner.py::TestProfileRunnerDowngrade.test_downgrade_and_reason_file_are_mutually_exclusive  # noqa: E501
        reason_file = tmp_path / "reason.txt"
        reason_file.write_text("from file", encoding="utf-8")
        cfg = AppConfig(
            profile_command="downgrade",
            profile_path=tmp_path,
            profile_downgrade_reason="inline",
            profile_downgrade_reason_file=reason_file,
        )
        with pytest.raises(SystemExit) as exc:
            run(cfg)
        assert exc.value.code == 1

    def test_downgrade_clears_a_real_ratchet(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests tests/unit/test_profile_runner.py::TestProfileRunnerDowngrade.test_downgrade_clears_a_real_ratchet  # noqa: E501
        (tmp_path / "frob.toml").write_text(
            '[profile]\nprofile = "rapid"\n', encoding="utf-8"
        )
        _write_ratchet(
            tmp_path,
            _RatchetState(
                ratcheted_to=ProfileName.STANDARD.value,
                reason="test trip",
                at=datetime.now(timezone.utc).isoformat(),
            ),
        )
        cfg = AppConfig(
            profile_command="downgrade",
            profile_path=tmp_path,
            profile_downgrade_reason="deliberate test downgrade",
        )
        with caplog.at_level("INFO"):
            run(cfg)
        assert "cleared" in caplog.text.lower()
        assert not (tmp_path / ".frob" / "profile-ratchet.json").exists()

        # And the effective profile reads rapid again afterward.
        cfg_show = AppConfig(
            profile_command="show", profile_path=tmp_path, profile_json=True
        )
        with caplog.at_level("INFO"):
            run(cfg_show)
        payloads = _json_records(caplog)
        assert payloads[-1]["effective"] == "rapid"

    def test_downgrade_reason_file_read_verbatim(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests tests/unit/test_profile_runner.py::TestProfileRunnerDowngrade.test_downgrade_reason_file_read_verbatim  # noqa: E501
        (tmp_path / "frob.toml").write_text(
            '[profile]\nprofile = "rapid"\n', encoding="utf-8"
        )
        _write_ratchet(
            tmp_path,
            _RatchetState(
                ratcheted_to=ProfileName.STANDARD.value,
                reason="test trip",
                at=datetime.now(timezone.utc).isoformat(),
            ),
        )
        reason_file = tmp_path / "reason.txt"
        reason_file.write_text(
            "a multi-sentence reason with a $(dangerous) substitution.\n",
            encoding="utf-8",
        )
        cfg = AppConfig(
            profile_command="downgrade",
            profile_path=tmp_path,
            profile_downgrade_reason_file=reason_file,
        )
        with caplog.at_level("INFO"):
            run(cfg)
        assert "$(dangerous)" in caplog.text

    def test_downgrade_is_a_noop_when_nothing_ratcheted(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests tests/unit/test_profile_runner.py::TestProfileRunnerDowngrade.test_downgrade_is_a_noop_when_nothing_ratcheted  # noqa: E501
        cfg = AppConfig(
            profile_command="downgrade",
            profile_path=tmp_path,
            profile_downgrade_reason="no-op check",
        )
        with caplog.at_level("INFO"):
            run(cfg)
        assert "no-op" in caplog.text.lower()
