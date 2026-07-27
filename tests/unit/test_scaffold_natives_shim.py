"""T-0865: natives build estate conformance -- the scaffolded Makefile
`core:` shim is the one-line `uv run frob natives build` delegate (T-0864),
and a repo whose Makefile `core:` recipe still carries its own per-repo
native-build/cache logic instead of the shim is reported as drift by
`scaffold_conformance_status`, naming the shim as the remedy."""

from __future__ import annotations

import subprocess
from pathlib import Path

from frob.scaffold._managed import (
    MANAGED_TEXT_BLOCKS,
    _has_legacy_core_cache_logic,
    apply_managed_blocks,
    scaffold_conformance_status,
)


# frob:ticket T-0865
def _git(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    """Run a git command in `cwd`, never raising -- callers assert on the
    returncode/output themselves."""
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=False
    )


# frob:ticket T-0865
def _init_repo(root: Path) -> None:
    """A minimal git repo at `root`, enough for `_hooks_dir` resolution
    during `scaffold_conformance_status`/`apply_managed_blocks`."""
    root.mkdir(parents=True, exist_ok=True)
    _git("init", "-q", "-b", "main", cwd=root)
    _git("config", "user.email", "test@example.com", cwd=root)
    _git("config", "user.name", "Test", cwd=root)
    (root / "frob.toml").write_text('[project]\nname = "x"\n')


def _core_shim_block():
    """The `makefile-core-shim` entry out of `MANAGED_TEXT_BLOCKS`."""
    return next(b for b in MANAGED_TEXT_BLOCKS if b.block_id == "makefile-core-shim")


# frob:ticket T-0865
class TestMakefileCoreShimTemplate:
    """The scaffold-owned shim content itself is the one-line delegate,
    not the old per-repo cargo/CARGO_TARGET_DIR recipe (T-0864)."""

    # frob:ticket T-0865
    def test_shim_content_is_one_line_natives_build_delegate(self) -> None:
        # frob:tests \
        # tests/unit/test_scaffold_natives_shim.py::TestMakefileCoreShimTemplate.test_\
        # shim_content_is_one_line_natives_build_delegate  # noqa: E501
        """The canonical shim recipe body is exactly `uv run frob natives
        build`, no cache logic (CARGO_TARGET_DIR, raw maturin calls)."""
        block = _core_shim_block()
        assert "uv run frob natives build" in block.content
        assert not _has_legacy_core_cache_logic(block.content)

    # frob:ticket T-0865
    def test_applying_to_fresh_repo_installs_one_line_shim(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/unit/test_scaffold_natives_shim.py::TestMakefileCoreShimTemplate.test_\
        # applying_to_fresh_repo_installs_one_line_shim  # noqa: E501
        """`frob scaffold apply` on a repo with no Makefile yet creates one
        carrying the shim, and conformance reports clean afterward."""
        _init_repo(tmp_path)
        result = apply_managed_blocks(tmp_path)
        assert result.is_ok

        makefile_text = (tmp_path / "Makefile").read_text()
        assert "uv run frob natives build" in makefile_text
        assert not _has_legacy_core_cache_logic(makefile_text)

        statuses = scaffold_conformance_status(tmp_path)
        shim_status = next(s for s in statuses if s.block_id == "makefile-core-shim")
        assert shim_status.present
        assert not shim_status.stale


# frob:ticket T-0865
class TestLegacyCoreCacheDrift:
    """A Makefile `core:` target still carrying the pre-T-0864 per-repo
    cache recipe, with NO managed-block markers, is flagged as drift."""

    # frob:ticket T-0865
    def test_legacy_marker_detection_true_for_old_recipe(self) -> None:
        # frob:tests \
        # tests/unit/test_scaffold_natives_shim.py::TestLegacyCoreCacheDrift.test_lega\
        # cy_marker_detection_true_for_old_recipe  # noqa: E501
        """`_has_legacy_core_cache_logic` recognizes the old CARGO_TARGET_DIR
        + raw `maturin develop` recipe shape."""
        legacy = (
            "CARGO_TARGET_DIR := $(shell git rev-parse --git-common-dir)"
            "/frob-cargo-target-cache\n"
            "core: $(STAMP)\n"
            "\tmaturin develop --uv --release -m frob-core/Cargo.toml\n"
        )
        assert _has_legacy_core_cache_logic(legacy)

    # frob:ticket T-0865
    def test_legacy_marker_detection_false_for_current_shim(self) -> None:
        # frob:tests \
        # tests/unit/test_scaffold_natives_shim.py::TestLegacyCoreCacheDrift.test_lega\
        # cy_marker_detection_false_for_current_shim  # noqa: E501
        """The current one-line shim text is never mistaken for the legacy
        recipe."""
        assert not _has_legacy_core_cache_logic(_core_shim_block().content)

    # frob:ticket T-0865
    def test_legacy_unmanaged_core_target_reports_stale(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/unit/test_scaffold_natives_shim.py::TestLegacyCoreCacheDrift.test_lega\
        # cy_unmanaged_core_target_reports_stale  # noqa: E501
        """A repo whose Makefile has a hand-written `core:` recipe with its
        own cache logic, and NO `frob:managed-block` markers at all, is
        reported present+stale (a real drift), not silently `present=False`
        (which would read as 'nothing here yet, apply cleanly')."""
        _init_repo(tmp_path)
        (tmp_path / "Makefile").write_text(
            "STAMP := .venv/.install-stamp\n\n"
            "CARGO_TARGET_DIR := $(shell git rev-parse --git-common-dir)"
            "/frob-cargo-target-cache\n"
            "core: $(STAMP)\n"
            "\tmaturin develop --uv --release -m frob-core/Cargo.toml\n"
        )

        statuses = scaffold_conformance_status(tmp_path)
        shim_status = next(s for s in statuses if s.block_id == "makefile-core-shim")
        assert shim_status.present
        assert shim_status.stale

    # frob:ticket T-0865
    def test_missing_core_target_entirely_is_plain_absent_not_drift(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/unit/test_scaffold_natives_shim.py::TestLegacyCoreCacheDrift.test_miss\
        # ing_core_target_entirely_is_plain_absent_not_drift  # noqa: E501
        """A Makefile with no `core:` recipe at all (never adopted, no
        legacy cache logic either) is plain `present=False` -- a clean
        `apply` append, not a named drift finding."""
        _init_repo(tmp_path)
        (tmp_path / "Makefile").write_text(
            "STAMP := .venv/.install-stamp\n\ntest: $(STAMP)\n\tuv run pytest\n"
        )

        statuses = scaffold_conformance_status(tmp_path)
        shim_status = next(s for s in statuses if s.block_id == "makefile-core-shim")
        assert not shim_status.present
        assert not shim_status.stale
