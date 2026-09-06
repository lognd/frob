"""`frob.gates._profile_boundary.profile_boundary_subject_count` (T-3985):
the subject-count primitive wired to PROFILE001 as the proof of concept.

Kept in a SEPARATE file from `tests/unit/gates/test_profile_boundary.py`
(which carries the rest of PROFILE001's own coverage) purely because that
file was under another ticket's active scope lease at the time this
ticket was implemented -- not a statement that these tests belong to a
different subsystem. Reuses the same fixture-writing conventions."""

from __future__ import annotations

from pathlib import Path

from frob.gates._profile_boundary import (
    profile_boundary_gate,
    profile_boundary_subject_count,
)

_PROFILE_MODULE = '''\
"""frob.tickets._profile stand-in."""
from enum import StrEnum
from typani.result import Ok, Result


class ProfileName(StrEnum):
    RAPID = "rapid"
    STANDARD = "standard"
    FORTRESS = "fortress"


class ProfileError:
    pass


def effective_profile(root) -> Result[ProfileName, ProfileError]:
    return Ok(ProfileName.STANDARD)


def configured_profile(root) -> Result[ProfileName, ProfileError]:
    return Ok(ProfileName.STANDARD)
'''

_BACKPRESSURE_MODULE = '''\
"""frob.verify._backpressure stand-in -- the settings-resolver module."""


def settings_for_profile(profile):
    from frob.tickets._profile import ProfileName

    if profile is ProfileName.RAPID:
        return "relaxed"
    return "strict"
'''


def _write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_allowed_layer(root: Path) -> None:
    """The two settings-resolver-layer files every fixture below needs
    present so `ProfileName` has a real definition to resolve against."""
    _write(root, "src/frob/tickets/_profile.py", _PROFILE_MODULE)
    _write(root, "src/frob/verify/_backpressure.py", _BACKPRESSURE_MODULE)


class TestProfileBoundarySubjectCount:
    """T-3985: `profile_boundary_subject_count` reports how many
    `ProfileName` usages were actually examined -- independent of how many
    were flagged. This is the exact number that stayed silently `0` on
    Windows (T-3941) while `profile_boundary_gate` reported zero
    violations, an outcome indistinguishable from a clean pass without
    this count."""

    # frob:ticket T-3985
    def test_counts_every_usage_examined(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/unit/gates/test_profile_boundary_subject_count.py::TestProfileBoundaryS\
        # ubjectCount.test_counts_every_usage_examined
        """The allowed layer's own two definitions/references plus one
        allowed-outside usage should all count as examined subjects, not
        just the ones flagged as violations (there are none here)."""
        _write_allowed_layer(tmp_path)
        _write(
            tmp_path,
            "src/frob/app/ticket_runner/_land_cmd.py",
            '''\
"""land_cmd stand-in, migrated shape."""
from frob.verify import effective_profile_or_standard, settings_for_profile


def _land_core(root, worktree):
    effective = effective_profile_or_standard(worktree)
    if not settings_for_profile(effective).pre_commit_sweep_enabled:
        return "rapid"
    return "not-rapid"
''',
        )
        violations = profile_boundary_gate(tmp_path)
        subject_count = profile_boundary_subject_count(tmp_path)
        assert violations == ()
        assert subject_count > 0

    # frob:ticket T-3985
    def test_zero_reproduces_t3941_windows_shape(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests \
        # tests/unit/gates/test_profile_boundary_subject_count.py::TestProfileBoundaryS\
        # ubjectCount.test_zero_reproduces_t3941_windows_shape
        """T-3985 acceptance[2]: reproduce T-3941's own root cause
        directly -- `_symbol_usages` (backed by `frob.xref.xref`)
        returning nothing, the way it silently did on Windows -- and show
        that `profile_boundary_gate` alone cannot distinguish this from a
        real clean pass (both report zero violations), while
        `profile_boundary_subject_count` reports the missing signal:
        `0`, on a fixture that has real `ProfileName` usages to find."""
        import frob.gates._profile_boundary as mod

        _write_allowed_layer(tmp_path)
        _write(
            tmp_path,
            "src/frob/app/ticket_runner/_land_cmd.py",
            '''\
"""land_cmd stand-in, a regression reintroducing the if-rapid shape."""
from frob.tickets._profile import ProfileName, effective_profile


def _land_core(root, worktree):
    profile_result = effective_profile(worktree)
    effective = (
        profile_result.danger_ok if profile_result.is_ok else ProfileName.STANDARD
    )
    if effective is ProfileName.RAPID:
        return "rapid"
    return "not-rapid"
''',
        )
        # sanity: this fixture DOES produce a real violation under the
        # normal (working) xref path.
        assert profile_boundary_gate(tmp_path) != ()

        monkeypatch.setattr(mod, "_symbol_usages", lambda root, symbol: ())
        violations = profile_boundary_gate(tmp_path)
        subject_count = profile_boundary_subject_count(tmp_path)
        assert violations == ()  # the T-3941 shape: silently "clean"
        assert subject_count == 0  # the signal that distinguishes it
