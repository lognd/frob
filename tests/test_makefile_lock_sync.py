"""T-0789: `make upload`'s version bump must re-lock and commit `uv.lock`.

Without this, a version bump lands with `pyproject.toml` changed but
`uv.lock` left stale (still recording the PREVIOUS frob version). Every
`uv run` invocation in every worktree cut from that commit then tries to
reconcile the two, leaving a silent working-tree `uv.lock` diff no agent
hand-edited -- SCOPE001 fires on it unless someone remembers to
`git checkout -- uv.lock` first (the recurring coordinator-land friction
this ticket exists to remove). This is a static assertion over the
`Makefile` recipe text, not a live `uv lock` invocation: the fix is about
what the recipe DOES, and running the real command here would need
network/registry access pytest should not depend on.
"""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent


# frob:waive DUP001 reason="parallel per-domain test scaffolding across \
# test_makefile_lock_sync.py, test_natives_build.py (2 sites) -- \
# each file exercises a structurally similar check for a distinct \
# domain/module with the same arrange-act shape; extracting would \
# blur which domain owns which check"
def _upload_recipe() -> str:
    """The `upload:` target's recipe lines from the repo's real Makefile,
    verbatim -- used to statically assert the T-0789 lock-sync fix stays
    in place rather than re-parsing a copy that could drift from it."""
    text = (_ROOT / "Makefile").read_text(encoding="utf-8")
    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("upload:"))
    end = start + 1
    while end < len(lines) and (lines[end].startswith("\t") or not lines[end].strip()):
        end += 1
    return "\n".join(lines[start:end])


def test_upload_relocks_after_version_bump():
    # frob:tests tests/test_makefile_lock_sync.py::test_upload_relocks_after_version_bump kind="unit"  # noqa: E501
    recipe = _upload_recipe()
    bump_idx = recipe.index("bump_version.py")
    lock_idx = recipe.index("uv lock")
    assert bump_idx < lock_idx, "uv lock must run AFTER the version bump, not before"


def test_upload_commits_uv_lock_with_pyproject():
    # frob:tests tests/test_makefile_lock_sync.py::test_upload_commits_uv_lock_with_pyproject kind="unit"  # noqa: E501
    recipe = _upload_recipe()
    add_line = next(
        line for line in recipe.splitlines() if line.strip().startswith("git add")
    )
    assert "pyproject.toml" in add_line
    assert "uv.lock" in add_line
