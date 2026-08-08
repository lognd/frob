# frob:ticket T-1684
# frob:ticket T-1705
"""Unit tests for the close-time REL001 bump check (T-1684): an
already-applied bump must satisfy it, or no reachable state does.
T-1705 adds the rapid-profile skip and the agent-reachable remedy
message."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from typani.result import Err, Ok

from frob.app.ticket_runner._close_cmd import (
    _declared_pyproject_version,
    _own_obligations_rel_bump_dirty,
    _version_covers,
)


class TestDeclaredPyprojectVersion:
    """"Cannot verify" is `None`, never a version that satisfies."""

    def test_absent_pyproject_is_none(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_close_rel001_bump.py::TestDeclaredPyprojectVersion.test_absent_pyproject_is_none  # noqa: E501
        assert _declared_pyproject_version(tmp_path) is None

    def test_unparsable_pyproject_is_none(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_close_rel001_bump.py::TestDeclaredPyprojectVersion.test_unparsable_pyproject_is_none  # noqa: E501
        (tmp_path / "pyproject.toml").write_text("[project\n", encoding="utf-8")
        assert _declared_pyproject_version(tmp_path) is None

    def test_reads_the_declared_version(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_close_rel001_bump.py::TestDeclaredPyprojectVersion.test_reads_the_declared_version  # noqa: E501
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "x"\nversion = "0.356.0"\n', encoding="utf-8"
        )
        assert _declared_pyproject_version(tmp_path) == "0.356.0"


class TestVersionCovers:
    """Numeric dotted comparison; anything else is not satisfied."""

    def test_equal_covers(self) -> None:
        # frob:tests \
        # tests/unit/test_close_rel001_bump.py::TestVersionCovers.test_equal_covers
        assert _version_covers("0.356.0", "0.356.0") is True

    def test_higher_covers(self) -> None:
        # frob:tests \
        # tests/unit/test_close_rel001_bump.py::TestVersionCovers.test_higher_covers
        assert _version_covers("0.357.0", "0.356.0") is True

    def test_lower_does_not_cover(self) -> None:
        # frob:tests tests/unit/test_close_rel001_bump.py::TestVersionCovers.test_lower_does_not_cover  # noqa: E501
        assert _version_covers("0.355.0", "0.356.0") is False

    def test_non_numeric_never_covers(self) -> None:
        # frob:tests tests/unit/test_close_rel001_bump.py::TestVersionCovers.test_non_numeric_never_covers  # noqa: E501
        assert _version_covers("0.356.0rc1", "0.356.0") is False


# frob:ticket T-1705
class TestOwnObligationsRelBumpDirtyRapidSkip:
    """T-1705: under `rapid`, the REL001 preflight is skipped entirely
    (never computed, never blocks close) and the relaxation is recorded
    as debt -- the same seam `frob.tickets._land._land_is_rapid` already
    uses for every other rapid relaxation."""

    def test_rapid_skips_the_check_and_records_debt(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_close_rel001_bump.py::TestOwnObligationsRelBumpDirtyRapidSkip.test_rapid_skips_the_check_and_records_debt  # noqa: E501
        from frob.tickets._profile import ProfileName

        monkeypatch.setattr(
            "frob.tickets._profile.effective_profile",
            lambda root: Ok(ProfileName.RAPID),
        )
        debt_calls: list[tuple[Path, str, str]] = []
        monkeypatch.setattr(
            "frob.tickets._evidence.record_rapid_debt",
            lambda root, ticket_id, skipped: debt_calls.append(
                (root, ticket_id, skipped)
            ),
        )

        def _fail_if_called(*a: object, **k: object) -> object:
            raise AssertionError(
                "_required_release_bump must not be called under rapid"
            )

        monkeypatch.setattr(
            "frob.app.ticket_runner._required_release_bump", _fail_if_called
        )

        ticket = SimpleNamespace(id="T-0001")
        assert _own_obligations_rel_bump_dirty(tmp_path, ticket) is False
        assert debt_calls == [(tmp_path, "T-0001", "close-rel001-preflight-skipped")]

    def test_standard_still_runs_the_check(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_close_rel001_bump.py::TestOwnObligationsRelBumpDirtyRapidSkip.test_standard_still_runs_the_check  # noqa: E501
        from frob.tickets._profile import ProfileName

        monkeypatch.setattr(
            "frob.tickets._profile.effective_profile",
            lambda root: Ok(ProfileName.STANDARD),
        )
        monkeypatch.setattr(
            "frob.app.ticket_runner._required_release_bump",
            lambda root, ticket_id: Ok(None),
        )

        ticket = SimpleNamespace(id="T-0001")
        assert _own_obligations_rel_bump_dirty(tmp_path, ticket) is False

    def test_outstanding_bump_under_standard_names_land_as_the_remedy(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        # frob:tests tests/unit/test_close_rel001_bump.py::TestOwnObligationsRelBumpDirtyRapidSkip.test_outstanding_bump_under_standard_names_land_as_the_remedy  # noqa: E501
        """T-1705's second finding: the outstanding-bump message must name
        `frob ticket land` as the remedy, not merely say the bump is
        outstanding -- an agent cannot bump pyproject.toml itself (T-0731
        refuses that commit), so a message that stops short of naming the
        supported route sends the agent looking for a forbidden action."""
        from frob.tickets._profile import ProfileName

        monkeypatch.setattr(
            "frob.tickets._profile.effective_profile",
            lambda root: Ok(ProfileName.STANDARD),
        )
        monkeypatch.setattr(
            "frob.app.ticket_runner._required_release_bump",
            lambda root, ticket_id: Ok("0.400.0"),
        )
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "x"\nversion = "0.399.0"\n', encoding="utf-8"
        )

        ticket = SimpleNamespace(id="T-0001")
        with caplog.at_level("WARNING"):
            result = _own_obligations_rel_bump_dirty(tmp_path, ticket)

        assert result is True
        messages = " ".join(r.message for r in caplog.records)
        assert "frob ticket land T-0001" in messages
        assert "do NOT bump pyproject.toml by hand" in messages

    def test_unresolvable_profile_falls_back_to_running_the_check(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_close_rel001_bump.py::TestOwnObligationsRelBumpDirtyRapidSkip.test_unresolvable_profile_falls_back_to_running_the_check  # noqa: E501
        """An unreadable profile must never silently skip the check --
        fail-closed, same posture as every other "cannot verify" branch
        in this module. The error value itself is never inspected by
        `_own_obligations_rel_bump_dirty` (only `.is_ok`/`.danger_ok`
        matter), so a plain string stands in for the real `ProfileError`
        member -- avoids a SELFAUDIT001 cross-module interface
        declaration this test-only mock does not need."""
        monkeypatch.setattr(
            "frob.tickets._profile.effective_profile",
            lambda root: Err("unreadable"),
        )
        monkeypatch.setattr(
            "frob.app.ticket_runner._required_release_bump",
            lambda root, ticket_id: Ok(None),
        )

        ticket = SimpleNamespace(id="T-0001")
        assert _own_obligations_rel_bump_dirty(tmp_path, ticket) is False
