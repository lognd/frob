"""Managed boilerplate blocks (T-0736): the Makefile core-shim, standard
`.gitignore` entries, and the two T-0431/T-0577 worktree-lease git hooks,
each defined ONCE here and drift-checked/installed everywhere else --
mirroring the deploy script<->model drift-lock precedent
(`frob.deploy._drift`, docs/guides/agent-playbook.md) but for scaffold
boilerplate instead of generated deploy scripts.

Two kinds of managed block:

- "text" blocks are inserted into an existing file (Makefile, .gitignore)
  between a `# frob:managed-block BEGIN <id>` / `END <id>` marker pair --
  present-and-matching is left alone, present-and-different is replaced
  in place (between the markers only), absent is appended. A repo's own
  content outside the markers is never touched.
- "hook" blocks are whole git hook files (`install_worktree_lease_hook`
  already owns their exact body) -- `apply_managed_blocks` reuses that
  installer rather than re-deriving hook content here, so there is still
  exactly one place the hook body is defined.

Every block's "current" content is deterministic and versioned only by
this module's source (no separate stamp file) -- the same "regenerate
fresh, compare byte-identical" posture `deploy_drift_violations` uses:
staleness is always measured against what `frob` would install *right
now*, not against a frozen snapshot that can itself go stale.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel
from typani import Ok
from typani.result import Result

from frob.logging import get_logger
from frob.scaffold.project import (
    _FORBID_LAND_OWNED_FILES_SCRIPT,
    _FORBID_RAW_TICKET_MERGE_SCRIPT,
    _WORKTREE_LEASE_HOOK_NAMES,
    _WORKTREE_LEASE_HOOK_SCRIPT,
    _WORKTREE_LEASE_HOOK_TERMINATOR,
    ScaffoldError,
    _hooks_dir,
    install_worktree_lease_hook,
)

_log = get_logger(__name__)

#: A hook file written by `install_worktree_lease_hook` always starts with
#: this literal comment line -- used to tell "ours, safe to update" apart
#: from a repo's own genuinely custom hook of the same name, which must
#: never be silently overwritten.
_OURS_MARKER = "# Installed by `frob scaffold install-worktree-lease-hook` (T-0431)."


def _marker_begin(block_id: str) -> str:
    """The opening marker line for managed-block `block_id` -- content
    between this and `_marker_end(block_id)` is frob-owned and safe to
    replace; content outside it is the repo's own and never touched."""
    return (
        f"# frob:managed-block BEGIN {block_id} "
        "(frob scaffold apply -- do not hand-edit within markers)"
    )


def _marker_end(block_id: str) -> str:
    """The closing marker line for managed-block `block_id` (see
    `_marker_begin`)."""
    return f"# frob:managed-block END {block_id}"


def _digest(content: str) -> str:
    """Stable short fingerprint of `content`, used to detect drift between
    a repo's installed block and what `frob` would install right now."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


# frob:doc docs/commands/scaffold.md#managed-blocks-t-0736
@dataclass(frozen=True)
class ManagedTextBlock:
    """One frob-owned marked region: `block_id` identifies it, `target` is
    the repo-relative file it lives in, `content` is the exact text
    installed between its markers (T-0736)."""

    block_id: str
    target: str
    content: str


#: T-0732's core-build shim, verbatim from this repo's own Makefile --
#: this IS the canonical definition; T-0732's landed `core:` target is
#: read here as source of truth, not duplicated by hand. T-0735's planned
#: `frob-natives-build` subcommand will replace this literal recipe with a
#: call into that subcommand in one place, once it exists (it does not
#: yet -- see this ticket's Done report).
_MAKEFILE_CORE_SHIM = """\
# Build and install the frob-core/strata-core native extensions into the
# venv (T-0732). Smart-dup R3+ and strata design-model parsing need them;
# everything else works without them, so this is a best-effort step that
# warns rather than fails when the Rust toolchain is absent. Requires a
# STAMP variable (venv install stamp) to already be defined -- see the
# Makefile shim installed by `frob scaffold apply`.
# T-0732: CARGO_TARGET_DIR shared per CLONE (not per worktree) via the
# common .git dir, so a fresh worktree reuses another worktree's already-
# compiled dependency crates instead of a from-scratch cargo build.
CARGO_TARGET_DIR := $(shell git rev-parse --git-common-dir \
2>/dev/null)/frob-cargo-target-cache
core: $(STAMP)
\t@command -v cargo >/dev/null 2>&1 || { \\
\t\techo "cargo not found; skipping frob-core (smart-dup R3+ disabled)"; \\
\t\texit 0; }
\tVIRTUAL_ENV=$(CURDIR)/.venv CARGO_TARGET_DIR=$(CARGO_TARGET_DIR) uvx \
maturin develop --uv --release -m frob-core/Cargo.toml
\tVIRTUAL_ENV=$(CURDIR)/.venv CARGO_TARGET_DIR=$(CARGO_TARGET_DIR) uvx \
maturin develop --uv --release -m strata-core/Cargo.toml
"""

#: The standard cross-language `.gitignore` entries every frob-managed
#: repo should carry (build artifacts, Python caches, frob local state,
#: secrets) -- the same list this project's own global CLAUDE.md
#: mandates for every repo, made mechanically checkable instead of a
#: rule an agent has to remember by hand each time.
_GITIGNORE_STANDARD_ENTRIES = """\
# Build artifacts
build/
dist/
*.egg-info/
cmake-build-*/
CMakeFiles/
CMakeCache.txt
*.o
*.a
*.so
*.dylib
target/

# Python
.venv/
__pycache__/
*.pyc
.pytest_cache/
.ruff_cache/
.mypy_cache/
.coverage
htmlcov/
coverage.xml

# frob local state
.frob/
FROBLEMS.md

# Secrets
.env
"""

# frob:doc docs/commands/scaffold.md#managed-blocks-t-0736
#: All text-kind managed blocks. Order matters only for `apply`'s report
#: ordering, not for correctness (each targets a distinct file/marker id).
MANAGED_TEXT_BLOCKS: tuple[ManagedTextBlock, ...] = (
    ManagedTextBlock(
        block_id="makefile-core-shim", target="Makefile", content=_MAKEFILE_CORE_SHIM
    ),
    ManagedTextBlock(
        block_id="gitignore-standard",
        target=".gitignore",
        content=_GITIGNORE_STANDARD_ENTRIES,
    ),
)

# frob:doc docs/commands/scaffold.md#managed-blocks-t-0736
#: The two T-0431/T-0577 worktree-lease guard hooks (`install_worktree_
#: lease_hook` owns their body) -- treated as managed blocks so `doctor`
#: and `apply` cover them the same way as the text blocks above.
MANAGED_HOOK_NAMES: tuple[str, ...] = _WORKTREE_LEASE_HOOK_NAMES


# frob:doc docs/commands/scaffold.md#managed-blocks-t-0736
class ManagedBlockStatus(BaseModel):
    """One managed block's conformance in a repo, as observed by `frob
    doctor`/`scaffold_conformance_status`: `kind` is `"text"` or `"hook"`,
    `present` is whether the target exists at all, `stale` is whether
    present content's digest differs from what `frob` would install right
    now (T-0736)."""

    model_config = {}

    block_id: str
    target: str
    kind: str
    present: bool
    stale: bool
    expected_digest: str
    actual_digest: str | None = None


def _extract_region(text: str, block_id: str) -> str | None:
    """The text strictly between `block_id`'s begin/end markers in `text`,
    or `None` if the marker pair is not present (malformed -- only one
    marker present -- is also treated as absent, safest default: `apply`
    will append a fresh, well-formed block rather than guess at repair)."""
    begin = _marker_begin(block_id)
    end = _marker_end(block_id)
    try:
        begin_idx = text.index(begin)
        end_idx = text.index(end, begin_idx)
    except ValueError:
        return None
    inner_start = begin_idx + len(begin)
    return text[inner_start:end_idx].strip("\n")


def _text_block_status(root: Path, block: ManagedTextBlock) -> ManagedBlockStatus:
    """`ManagedBlockStatus` for one `ManagedTextBlock` under `root`: absent
    file or absent marker pair is `present=False`; a present region whose
    digest differs from the canonical content's is `stale=True`."""
    expected_digest = _digest(block.content.rstrip("\n"))
    path = root / block.target
    if not path.exists():
        return ManagedBlockStatus(
            block_id=block.block_id,
            target=block.target,
            kind="text",
            present=False,
            stale=False,
            expected_digest=expected_digest,
        )
    region = _extract_region(path.read_text(encoding="utf-8"), block.block_id)
    if region is None:
        return ManagedBlockStatus(
            block_id=block.block_id,
            target=block.target,
            kind="text",
            present=False,
            stale=False,
            expected_digest=expected_digest,
        )
    actual_digest = _digest(region)
    return ManagedBlockStatus(
        block_id=block.block_id,
        target=block.target,
        kind="text",
        present=True,
        stale=actual_digest != expected_digest,
        expected_digest=expected_digest,
        actual_digest=actual_digest,
    )


def _expected_hook_body(hook_name: str) -> str:
    """The exact hook body `install_worktree_lease_hook` would write for
    `hook_name` right now -- reconstructed from the SAME private script
    constants that function uses (never a second copy of the text), so
    this can never drift from what installing actually produces."""
    body = _WORKTREE_LEASE_HOOK_SCRIPT
    if hook_name == "pre-merge-commit":
        body += _FORBID_RAW_TICKET_MERGE_SCRIPT
    if hook_name == "pre-commit":
        body += _FORBID_LAND_OWNED_FILES_SCRIPT
    return body + _WORKTREE_LEASE_HOOK_TERMINATOR


def _hook_status(root: Path, hook_name: str) -> ManagedBlockStatus:
    """`ManagedBlockStatus` for one worktree-lease hook file: `present`
    reflects whether the hooks-dir file exists (missing hooks dir/not a
    git repo also reports `present=False`, never raises); `stale` is
    True only for a hook that IS ours (carries `_OURS_MARKER`) but whose
    body no longer matches current `install_worktree_lease_hook` output
    -- a foreign (non-frob) hook of the same name is reported present,
    not-stale, so `apply` never silently claims it."""
    expected_digest = _digest(_expected_hook_body(hook_name))
    hooks_dir_result = _hooks_dir(root)
    if hooks_dir_result.is_err:
        return ManagedBlockStatus(
            block_id=f"hook-{hook_name}",
            target=f".git/hooks/{hook_name}",
            kind="hook",
            present=False,
            stale=False,
            expected_digest=expected_digest,
        )
    path = hooks_dir_result.danger_ok / hook_name
    if not path.exists():
        return ManagedBlockStatus(
            block_id=f"hook-{hook_name}",
            target=f".git/hooks/{hook_name}",
            kind="hook",
            present=False,
            stale=False,
            expected_digest=expected_digest,
        )
    body = path.read_text(encoding="utf-8")
    is_ours = _OURS_MARKER in body
    actual_digest = _digest(body)
    return ManagedBlockStatus(
        block_id=f"hook-{hook_name}",
        target=f".git/hooks/{hook_name}",
        kind="hook",
        present=True,
        stale=is_ours and actual_digest != expected_digest,
        expected_digest=expected_digest,
        actual_digest=actual_digest if is_ours else None,
    )


# frob:doc docs/commands/scaffold.md#managed-blocks-t-0736
# frob:tests tests/unit/test_scaffold_managed.py::TestScaffoldConformanceStatus.test_non_frob_repo_reports_nothing  # noqa: E501
# frob:tests tests/unit/test_scaffold_managed.py::TestScaffoldConformanceStatus.test_clean_after_apply  # noqa: E501
def scaffold_conformance_status(root: Path) -> tuple[ManagedBlockStatus, ...]:
    """Every managed text block's and hook's conformance under `root` --
    the one pass `frob doctor` folds into `DoctorReport.scaffold_blocks`
    so a repo missing/behind on current frob boilerplate standards is a
    named finding instead of silent rot (T-0736).

    Opt-in on `root/frob.toml` existing, same posture `deploy_drift_
    violations` uses for `deploy/`: a directory with no frob adoption at
    all (a bare `tmp_path` in a test, a repo that has never run `frob
    scaffold apply`/`frob scaffold new`) has nothing to be behind ON, so
    it reports empty/clean rather than flagging every block as
    "missing"."""
    if not (root / "frob.toml").exists():
        _log.debug("scaffold conformance: no frob.toml under %s, skipping", root)
        return ()

    statuses = tuple(_text_block_status(root, b) for b in MANAGED_TEXT_BLOCKS) + tuple(
        _hook_status(root, name) for name in MANAGED_HOOK_NAMES
    )
    _log.info(
        "scaffold conformance: %d block(s), %d missing, %d stale",
        len(statuses),
        sum(1 for s in statuses if not s.present),
        sum(1 for s in statuses if s.stale),
    )
    return statuses


def _apply_text_block(root: Path, block: ManagedTextBlock) -> str:
    """Idempotently install/update one `ManagedTextBlock` under `root`:
    no-op if already present and matching, in-place replace of the marked
    region if present and different, else append a fresh marked region
    (creating the file/parent dirs if needed). Returns a one-line
    description of what happened, for `apply`'s report."""
    path = root / block.target
    begin = _marker_begin(block.block_id)
    end = _marker_end(block.block_id)
    marked = f"{begin}\n{block.content.rstrip(chr(10))}\n{end}"

    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(marked + "\n", encoding="utf-8")
        _log.info("scaffold apply: created %s with block %s", path, block.block_id)
        return f"{block.target}: created with block {block.block_id}"

    text = path.read_text(encoding="utf-8")
    region = _extract_region(text, block.block_id)
    if region is not None and _digest(region) == _digest(block.content.rstrip("\n")):
        return f"{block.target}: block {block.block_id} already current"

    if region is None:
        sep = "" if text.endswith("\n") or text == "" else "\n"
        new_text = f"{text}{sep}\n{marked}\n"
        path.write_text(new_text, encoding="utf-8")
        _log.info("scaffold apply: appended block %s to %s", block.block_id, path)
        return f"{block.target}: appended new block {block.block_id}"

    begin_idx = text.index(begin)
    end_idx = text.index(end, begin_idx) + len(end)
    new_text = text[:begin_idx] + marked + text[end_idx:]
    path.write_text(new_text, encoding="utf-8")
    _log.info("scaffold apply: updated stale block %s in %s", block.block_id, path)
    return f"{block.target}: updated stale block {block.block_id}"


def _apply_hooks(root: Path) -> list[str]:
    """Idempotently install/update the T-0431/T-0577 worktree-lease hooks
    under `root`: installs when absent, force-updates when present and
    recognizably frob's own (`_OURS_MARKER`), and reports (without
    touching) a present hook that is NOT ours -- never overwrites a
    repo's genuine custom hook of the same name."""
    changes: list[str] = []
    statuses = {
        s.block_id: s for s in (_hook_status(root, n) for n in MANAGED_HOOK_NAMES)
    }
    any_foreign = any(s.present and s.actual_digest is None for s in statuses.values())
    if not any_foreign:
        result = install_worktree_lease_hook(root, force=True)
        if result.is_err:
            changes.append(f"hooks: install failed ({result.danger_err.value})")
        else:
            changes.append(
                f"hooks: installed/refreshed {[p.name for p in result.danger_ok]}"
            )
        return changes

    for name, status in statuses.items():
        if status.present and status.actual_digest is None:
            changes.append(f"hook {name}: present and NOT frob's own, left untouched")
        else:
            changes.append(
                f"hook {name}: skipped (sibling hook is foreign, "
                "apply is all-or-nothing)"
            )
    return changes


# frob:doc docs/commands/scaffold.md#managed-blocks-t-0736
# frob:tests tests/unit/test_scaffold_managed.py::TestApplyManagedBlocks.test_idempotent_second_run_is_noop  # noqa: E501
# frob:tests tests/unit/test_scaffold_managed.py::TestApplyManagedBlocks.test_creates_missing_and_updates_stale  # noqa: E501
# frob:tests tests/unit/test_scaffold_managed.py::TestApplyManagedBlocks.test_refuses_to_clobber_foreign_hook  # noqa: E501
def apply_managed_blocks(root: Path) -> Result[tuple[str, ...], ScaffoldError]:
    """Idempotently install/update every managed text block and the
    worktree-lease hooks under `root` (T-0736). Never fails on a foreign
    (non-frob) hook of the same name -- reports it and leaves it alone
    instead. Returns one description string per block/hook, in
    `MANAGED_TEXT_BLOCKS` order followed by the hooks, for `frob scaffold
    apply`'s CLI output and the Done-report evidence trail."""
    changes: list[str] = [_apply_text_block(root, b) for b in MANAGED_TEXT_BLOCKS]
    changes.extend(_apply_hooks(root))
    return Ok(tuple(changes))


__all__ = [
    "MANAGED_HOOK_NAMES",
    "MANAGED_TEXT_BLOCKS",
    "ManagedBlockStatus",
    "ManagedTextBlock",
    "apply_managed_blocks",
    "scaffold_conformance_status",
]
