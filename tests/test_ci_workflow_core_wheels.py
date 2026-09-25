"""T-4479: `make core-wheels` (the T-4465 step that builds fresh
frob-core/strata-core wheels into target/wheels every CI run) spawned a
BARE `maturin` via `uv run maturin build ...` -- `uv run` only resolves
names the project's own synced venv/PATH already has, and this repo does
not declare `maturin` as a project dependency, so every CI leg (no
maturin preinstalled on PATH) failed to spawn it at all (CI run
34809307457, all three legs, the first run after T-4465 landed).
`frob natives build` (what `core-wheels`'s own `core` prerequisite runs)
already solves this via `uvx maturin ...` -- `uv tool run`, which
installs and runs an ephemeral maturin tool regardless of PATH content.
These tests lock the Makefile target onto that same, single resolution
mechanism so a future edit cannot silently regress back to a bare/`uv
run` spawn.
"""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]


def _core_wheels_recipe() -> str:
    """The `core-wheels:` target's own recipe lines out of the Makefile,
    the exact text a future edit is most likely to touch."""
    text = (_REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    match = re.search(r"^core-wheels:.*?\n((?:\t.*\n?)+)", text, re.MULTILINE)
    assert match is not None, (
        "Makefile has no 'core-wheels:' target at all -- T-4465's own "
        "step has regressed further than a maturin-resolution bug"
    )
    return match.group(1)


class TestCoreWheelsResolvesMaturinViaUvx:
    """T-4479 MUST-FIRE/MUST-STAY-QUIET: `core-wheels`'s own recipe must
    spawn maturin through `uvx`, never a bare `maturin` or `uv run
    maturin` (both fail on a runner with no maturin preinstalled on
    PATH, exactly the CI incident this ticket fixes)."""

    def test_recipe_invokes_uvx_maturin(self) -> None:
        # frob:tests Makefile
        recipe = _core_wheels_recipe()
        assert "uvx maturin" in recipe, (
            "core-wheels' recipe does not call 'uvx maturin' -- it will "
            "fail to spawn maturin on any runner that has uv but no "
            "maturin preinstalled on PATH (CI run 34809307457)\n" + recipe
        )

    def test_recipe_does_not_invoke_uv_run_maturin(self) -> None:
        # frob:tests Makefile
        recipe = _core_wheels_recipe()
        assert "uv run maturin" not in recipe, (
            "core-wheels' recipe still calls 'uv run maturin' -- this is "
            "the exact T-4479 regression: 'uv run' only resolves names "
            "the project's own synced venv/PATH already has, and maturin "
            "is not a declared project dependency, so this fails to spawn "
            "on every CI leg\n" + recipe
        )

    def test_recipe_does_not_invoke_bare_maturin(self) -> None:
        # frob:tests Makefile
        recipe = _core_wheels_recipe()
        # every "maturin" occurrence must be immediately preceded by
        # "uvx " -- stripping the good pairs first and then checking
        # what remains gives a precise failure instead of a blunt
        # substring count.
        stripped = recipe.replace("uvx maturin", "")
        assert "maturin" not in stripped, (
            "core-wheels' recipe calls 'maturin' somewhere other than "
            "'uvx maturin' -- a bare spawn is not resolvable on a runner "
            "with no maturin on PATH\n" + recipe
        )

    def test_recipe_still_rebuilds_target_wheels_per_crate(self) -> None:
        """T-4465's own acceptance must survive T-4479's fix: stale
        wheels removed first, then a fresh `maturin build --release
        --out .../target/wheels` per crate."""
        # frob:tests Makefile
        recipe = _core_wheels_recipe()
        assert "rm -f" in recipe and "target/wheels" in recipe, (
            "core-wheels no longer removes stale wheels before "
            "rebuilding -- T-4465's own stale-cache fix has regressed\n" + recipe
        )
        assert "maturin build" in recipe and "--release" in recipe, (
            "core-wheels no longer builds a release wheel per crate\n" + recipe
        )
        assert "--out" in recipe, (
            "core-wheels no longer directs maturin's output at target/wheels\n" + recipe
        )


# frob:ticket T-5811
def _install_stamp_recipe() -> str:
    """The `$(STAMP): pyproject.toml` rule's own recipe lines out of the
    Makefile -- same extraction shape as `_core_wheels_recipe` above, for
    the sibling regression this ticket closes."""
    text = (_REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    match = re.search(
        r"^\$\(STAMP\): pyproject\.toml\n((?:\t.*\n?)+)", text, re.MULTILINE
    )
    assert match is not None, (
        "Makefile has no '$(STAMP): pyproject.toml' rule at all -- T-0340's "
        "own install-stamp target has regressed further than an extras bug"
    )
    return match.group(1)


class TestInstallStampSyncsSqlExtra:
    """T-5811 MUST-FIRE/MUST-STAY-QUIET: the `$(STAMP)` rule's `uv sync`
    must request `--extra sql` -- CI's `make core-wheels` step reaches
    this same rule (via `core-wheels` -> `core` -> `$(STAMP)`) AFTER the
    workflow's own initial `uv sync --all-extras --all-groups`, so a
    narrower sync here silently UNINSTALLS `sqlfluff` (a real top-level
    import in the tracked `src/frob/sql/_sqlfluff_plugin.py`) before the
    later `Typecheck` step runs -- measured directly: CI run 36086669322,
    `ty check` failing with `unresolved-import` on every `sqlfluff.*`
    name, on all three platforms."""

    def test_recipe_syncs_sql_extra(self) -> None:
        # frob:tests Makefile
        recipe = _install_stamp_recipe()
        assert "--extra sql" in recipe, (
            "$(STAMP)'s recipe does not sync --extra sql -- it will "
            "silently uninstall sqlfluff (a real top-level import in "
            "src/frob/sql/_sqlfluff_plugin.py) whenever this rule runs "
            "after a wider sync, breaking ty check (CI run 36086669322, "
            "all three platforms)\n" + recipe
        )

    def test_recipe_does_not_sync_smt_extra(self) -> None:
        # frob:tests Makefile
        recipe = _install_stamp_recipe()
        assert "--extra smt" not in recipe and "smt" not in recipe, (
            "$(STAMP)'s recipe now syncs --extra smt -- z3-solver "
            "(the smt extra) can fail to build from source on some "
            "platforms (see the comment above this rule); it must stay "
            "opt-in, not part of the routine install-stamp sync\n" + recipe
        )
