"""Tests for VERSION001 (T-3011): frob's own version, its `frob[native]`
extra's exact pins on `frob-core`/`strata-core`, and those two crates' own
`pyproject.toml` versions must all agree -- see
`frob.gates._version_coupling`'s module docstring for the full incident
reasoning (T-2884's git-SHA-check-because-versions-were-not-enough
precedent)."""

from __future__ import annotations

from pathlib import Path

from frob.gates._version_coupling import version_coupling_gate


def _write_repo(
    tmp_path: Path,
    *,
    frob_version: str = "1.2.3",
    native_extra: list[str] | None = None,
    core_version: str = "1.2.3",
    strata_version: str = "1.2.3",
) -> Path:
    """A minimal three-`pyproject.toml` fixture tree under `tmp_path`,
    matching the real repo's layout (root + frob-core/ + strata-core/)."""
    if native_extra is None:
        native_extra = [f"frob-core=={core_version}", f"strata-core=={strata_version}"]
    extra_lines = ", ".join(f'"{spec}"' for spec in native_extra)
    (tmp_path / "pyproject.toml").write_text(
        f"""\
[project]
name = "frob"
version = "{frob_version}"

[project.optional-dependencies]
native = [{extra_lines}]
""",
        encoding="utf-8",
    )
    core_dir = tmp_path / "frob-core"
    core_dir.mkdir()
    (core_dir / "pyproject.toml").write_text(
        f'[project]\nname = "frob-core"\nversion = "{core_version}"\n',
        encoding="utf-8",
    )
    strata_dir = tmp_path / "strata-core"
    strata_dir.mkdir()
    (strata_dir / "pyproject.toml").write_text(
        f'[project]\nname = "strata-core"\nversion = "{strata_version}"\n',
        encoding="utf-8",
    )
    return tmp_path


class TestVersionCouplingGate:
    """`version_coupling_gate`'s clean and skewed shapes."""

    def test_matched_versions_clean(self, tmp_path: Path) -> None:
        """All three versions matching, exact `==` pins: zero violations."""
        root = _write_repo(tmp_path)
        assert version_coupling_gate(root) == ()

    def test_skewed_core_version_fires(self, tmp_path: Path) -> None:
        """`frob-core/pyproject.toml`'s own version disagreeing with
        frob's is a named VERSION001 violation -- the exact T-2884-shaped
        skew this gate exists to catch mechanically."""
        root = _write_repo(tmp_path, core_version="1.2.4")
        violations = version_coupling_gate(root)
        assert violations
        assert all(v.rule == "VERSION001" for v in violations)
        assert any("frob-core" in v.message for v in violations)

    def test_loose_pin_fires(self, tmp_path: Path) -> None:
        """A `>=` pin on the native extra (instead of exact `==`) fires --
        a loose pin on an ABI-coupled native extension is rejected
        outright, not merely discouraged."""
        root = _write_repo(
            tmp_path, native_extra=["frob-core>=1.2.3", "strata-core==1.2.3"]
        )
        violations = version_coupling_gate(root)
        assert any(
            v.rule == "VERSION001" and "not an exact" in v.message
            for v in violations
        )

    def test_missing_extra_fires(self, tmp_path: Path) -> None:
        """No `native` extra at all is a named violation, not a silent
        pass -- the coupling policy must be enforced, not merely
        available to opt into."""
        root = _write_repo(tmp_path, native_extra=[])
        violations = version_coupling_gate(root)
        assert len(violations) == 2
        assert all(v.rule == "VERSION001" for v in violations)

    def test_mismatched_extra_pin_fires(self, tmp_path: Path) -> None:
        """An exact pin that simply names the wrong version (frob moved on,
        the extra pin did not) fires -- this is the "cut together" half
        of the policy, independent of the crate's own pyproject version."""
        root = _write_repo(
            tmp_path, native_extra=["frob-core==1.2.2", "strata-core==1.2.3"]
        )
        violations = version_coupling_gate(root)
        assert any(
            v.rule == "VERSION001" and "frob-core is pinned to" in v.message
            for v in violations
        )
