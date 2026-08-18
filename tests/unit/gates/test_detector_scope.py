"""`frob.gates._detector_scope`: the one shared "which packages can
contain a detector" declaration LEXCHECK001 (T-2466) consumes, and
PORT001's own widening (T-2405) is expected to reuse rather than
re-hardcode."""

from __future__ import annotations

from frob.gates._detector_scope import (
    DETECTOR_PACKAGE_ROOTS,
    is_detector_package_file,
)


class TestDetectorScope:
    """`DETECTOR_PACKAGE_ROOTS`/`is_detector_package_file`: membership by
    prefix, measured (not guessed) package set."""

    def test_gates_vet_strata_check_are_members(self) -> None:
        """The four MEASURED detector packages (module docstring) are all
        present -- `vet/` specifically, since T-2457's own bug is the
        proof this package must be included."""
        assert is_detector_package_file("src/frob/gates/_sys.py")
        assert is_detector_package_file("src/frob/vet/_capability_core.py")
        assert is_detector_package_file("src/frob/strata/_selfconform.py")
        assert is_detector_package_file("src/frob/check/_python.py")

    def test_arch_is_not_a_member(self) -> None:
        """`arch/` was measured (module docstring) to construct ZERO
        `Violation(...)`-shaped calls at T-2466 time and is deliberately
        excluded -- not silently omitted by guesswork."""
        assert not is_detector_package_file("src/frob/arch/_layering.py")

    def test_unrelated_package_is_not_a_member(self) -> None:
        """A package with no detector shape at all (`app/`) stays
        excluded -- this is a narrow, measured allowlist, not a repo-wide
        default."""
        assert not is_detector_package_file("src/frob/app/config.py")

    def test_roots_are_sorted_and_slash_terminated(self) -> None:
        """Every root is a directory PREFIX (trailing slash, so
        `src/frob/gates_extra/` can never falsely match `src/frob/gates/`
        by bare string prefix) in deterministic sorted order."""
        assert list(DETECTOR_PACKAGE_ROOTS) == sorted(DETECTOR_PACKAGE_ROOTS)
        assert all(root.endswith("/") for root in DETECTOR_PACKAGE_ROOTS)
