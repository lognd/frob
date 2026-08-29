"""`frob.gates._detector_scope`: the one shared "which packages can
contain a detector" declaration LEXCHECK001 (T-2466) consumes, and
PORT001's own widening (T-2405) is expected to reuse rather than
re-hardcode."""

from __future__ import annotations

from frob.gates._detector_scope import (
    DETECTOR_PACKAGE_ROOTS,
    is_detector_package_file,
    tracked_gate_files,
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

    def test_tracked_gate_files_filters_to_detector_roots(self) -> None:
        """T-2966: `tracked_gate_files` (extracted from the byte-identical
        `_tracked_gate_files` PORT001/LEXCHECK001 each carried privately)
        returns only files under `DETECTOR_PACKAGE_ROOTS`, sourced from
        this repo's own tracked tree (no fixture repo needed -- every
        result must satisfy `is_detector_package_file`)."""
        from pathlib import Path

        root = Path(__file__).resolve().parents[3]
        files = tracked_gate_files(root, log_prefix="test_tracked_gate_files")
        assert files
        assert all(is_detector_package_file(rel) for rel in files)

    def test_tracked_repo_python_files_is_repo_wide_not_detector_scoped(self) -> None:
        """T-3275: `tracked_repo_python_files` returns the UNFILTERED
        `src/frob/**/*.py` population (PORT001's own scan population,
        since the "can this embed project identity" question is not
        bounded to `DETECTOR_PACKAGE_ROOTS`) -- unlike `tracked_gate_
        files`, results are NOT required to satisfy `is_detector_package_
        file`; a non-detector-package file (e.g. under `testing/` or
        `app/`) is expected to appear."""
        from pathlib import Path

        from frob.gates._detector_scope import tracked_repo_python_files

        root = Path(__file__).resolve().parents[3]
        detector_files = set(tracked_gate_files(root, log_prefix="test_detector"))
        repo_files = set(tracked_repo_python_files(root, log_prefix="test_repo_wide"))
        assert repo_files
        # every detector file is also in the repo-wide population
        assert detector_files <= repo_files
        # the repo-wide population is a strict superset (non-detector
        # packages like testing/ carry tracked .py files too)
        assert any(rel.startswith("src/frob/testing/") for rel in repo_files)
        assert not all(is_detector_package_file(rel) for rel in repo_files)
