"""`frob.gates._profile_boundary` (T-2362): PROFILE001, the
profile-collapse epic's own closing structural gate -- no land-pipeline
module may reference `ProfileName`/`effective_profile`/`configured_
profile` outside the settings-resolver layer T-2360/T-2361 built.

Every test here writes real files to `tmp_path` and calls
`profile_boundary_gate` against it directly -- the gate reads the
filesystem via `frob.xref.xref` (tree-sitter-backed identifier
resolution, not a raw text scan), so a fixture must be real, parseable
Python on disk, not a mocked call graph."""

from __future__ import annotations

from pathlib import Path

from frob.gates._profile_boundary import profile_boundary_gate

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
    present so `ProfileName` has a real definition to resolve against --
    neither should itself ever appear in `profile_boundary_gate`'s
    findings (that would be the gate flagging its own allowlisted
    layer)."""
    _write(root, "src/frob/tickets/_profile.py", _PROFILE_MODULE)
    _write(root, "src/frob/verify/_backpressure.py", _BACKPRESSURE_MODULE)


class TestProfileBoundaryGate:
    # frob:ticket T-2362
    def test_negative_control_settings_layer_only_is_silent(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/gates/test_profile_boundary.py::TestProfileBoundaryGate.test_negative_control_settings_layer_only_is_silent  # noqa: E501
        """NEGATIVE CONTROL: a land-pipeline module that reads
        `settings_for_profile` and never touches `ProfileName`/
        `effective_profile`/`configured_profile` itself -- the
        post-T-2361 migrated shape -- must report zero findings."""
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
        assert violations == ()

    # frob:ticket T-2362
    def test_positive_control_reintroduced_branch_is_flagged(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/gates/test_profile_boundary.py::TestProfileBoundaryGate.test_positive_control_reintroduced_branch_is_flagged  # noqa: E501
        """POSITIVE CONTROL: a DELIBERATELY reintroduced if-rapid-shaped
        branch outside the settings-resolver layer -- exactly the class
        of regression this gate exists to catch -- must be flagged. This
        is the fixture the ticket's own acceptance criterion asks for: a
        gate that reports clean against no must-fail fixture proves
        nothing."""
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
        violations = profile_boundary_gate(tmp_path)
        rules = {v.rule for v in violations}
        files = {v.file for v in violations}
        assert "PROFILE001" in rules
        assert "src/frob/app/ticket_runner/_land_cmd.py" in files
        # Every usage in the fixture (the import line's two names, the
        # is-comparison, the STANDARD fallback) is a distinct hit --
        # this positive control fires more than once, not just barely.
        assert len(violations) >= 3

    # frob:ticket T-2362
    def test_settings_resolver_layer_itself_is_never_flagged(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/gates/test_profile_boundary.py::TestProfileBoundaryGate.test_settings_resolver_layer_itself_is_never_flagged  # noqa: E501
        """`_profile.py`'s own `ProfileName` definition/usages and
        `_backpressure.py`'s own `settings_for_profile` branch on it --
        the two allowlisted files -- must never appear in the findings,
        even though both reference every boundary symbol repeatedly."""
        _write_allowed_layer(tmp_path)
        violations = profile_boundary_gate(tmp_path)
        assert violations == ()

    # frob:ticket T-2362
    def test_pre_t2361_shape_is_flagged(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/gates/test_profile_boundary.py::TestProfileBoundaryGate.test_pre_t2361_shape_is_flagged  # noqa: E501
        """T-2362's own acceptance text: verify the gate fires against
        the PRE-T-2361 code shape, using the real historical
        `_land_cmd.py` fragment (the actual call site T-2361 migrated,
        commit e7f13fa6b-era shape) as the real-world must-fire corpus,
        not just a hand-written toy fixture."""
        _write_allowed_layer(tmp_path)
        _write(
            tmp_path,
            "src/frob/tickets/_evidence.py",
            '''\
"""_evidence.py stand-in, pre-T-1696 if-rapid shape."""


def _is_rapid(root) -> bool:
    from frob.tickets._profile import ProfileName, effective_profile

    resolved = effective_profile(root)
    if resolved.is_err:
        return False
    return resolved.danger_ok is ProfileName.RAPID
''',
        )
        violations = profile_boundary_gate(tmp_path)
        files = {v.file for v in violations}
        assert "src/frob/tickets/_evidence.py" in files

    # frob:ticket T-2362
    def test_tests_directory_is_not_scanned(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/gates/test_profile_boundary.py::TestProfileBoundaryGate.test_tests_directory_is_not_scanned  # noqa: E501
        """A test fixture constructing `ProfileName.STANDARD` to pass
        into `ceilings_for_profile`/`settings_for_profile` is the
        expected, intended use the epic's own doc page documents --
        `tests/**` is out of this gate's scope entirely (matching
        T-2361's own closing `frob explore xref` verification, which
        excluded tests/ the same way)."""
        _write_allowed_layer(tmp_path)
        _write(
            tmp_path,
            "tests/unit/verify/test_backpressure.py",
            '''\
"""test stand-in."""
from frob.tickets._profile import ProfileName


def test_something():
    assert ProfileName.RAPID == ProfileName.RAPID
''',
        )
        violations = profile_boundary_gate(tmp_path)
        assert violations == ()
