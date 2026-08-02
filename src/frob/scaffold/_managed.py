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
# frob:waive INV006 reason="T-1023 INV006 burn-down: this file's \
# exclusivity-vocabulary hit is source-level design-rationale/scope-cut prose (a \
# docstring or comment describing already-implemented internal behavior, verifiable by \
# reading the code it annotates) rather than a separate cross-module contract needing \
# its own tracked invariant; disposed as a calibration batch, not claim-by-claim, same \
# INV006 first-turn-on-pool disposition this repo already applies elsewhere (T-0585)"

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

#: T-0574: git has NO native pre-stash hook, and this was checked
#: empirically rather than assumed -- two candidates were tried and one
#: was disproven before landing on this one:
#:
#: 1. A repo-local `alias.stash` override (`git config alias.stash '!...'`)
#:    -- DISPROVEN. Empirically, git refuses to let an alias shadow a
#:    built-in subcommand name at all (`git stash` with `alias.stash` set
#:    to an arbitrary shell command still runs the real, unmodified
#:    `stash` -- verified with git 2.34.1 by aliasing `stash` to a command
#:    that unconditionally prints a sentinel and exits nonzero, then
#:    observing plain stash behavior and exit 0 regardless). Built-in
#:    command names are simply not alias-able in git; do not resurrect
#:    this approach without re-verifying against whatever git version is
#:    in play.
#: 2. The standard hook names (`pre-commit`, `pre-merge-commit`, ...) --
#:    DOES NOT FIRE for stash either: `git stash push` builds its commits
#:    with plumbing (`commit-tree`), not `git commit`, so no pre-commit
#:    hook runs, matching well-known git behavior (the same reason
#:    `--no-verify` has no effect on `git stash`).
#: 3. The `reference-transaction` hook (native, git >=2.28) -- WORKS.
#:    It fires for EVERY ref update, including `refs/stash`, in a
#:    "prepared" phase whose nonzero exit ABORTS the transaction
#:    (`githooks(5)`). Verified empirically: with this hook watching for
#:    `refs/stash` updates, `git stash` with >1 `git worktree list` entry
#:    is refused with `fatal: ref updates aborted by hook` (exit 128,
#:    nothing stashed), a plain `git commit` in the same repo is
#:    completely unaffected (different refname, hook exits 0 immediately),
#:    and `git stash` succeeds normally once back down to one worktree.
#:
#: T-0870: the initial version of this hook refused EVERY `refs/stash`
#: line unconditionally, which also aborted `git gc`'s `pack-refs`
#: maintenance rewrite of an existing `refs/stash` (a same-clone-wide
#: repo-maintenance failure, not a stash-collision hazard). Fixed by
#: refusing only a line that WRITES a value refs/stash does not already
#: resolve to -- see `_STASH_GUARD_HOOK_SCRIPT`'s own inline comment for
#: the mechanics (pack-refs presents its rewrite as two separate
#: transactions, so `old_oid == new_oid` within one line is not a usable
#: signal; comparing the written value against the ref's current
#: resolution is).
#:
#: Coverage limits (documented honestly, not oversold): this is a
#: PER-CLONE git hook (`.git/hooks/reference-transaction`, or the shared
#: `core.hooksPath` dir if a repo uses one) -- like `git stash` itself,
#: hooks live in the common `.git` dir and so cover every worktree of the
#: clone uniformly, which is the intended scope here. It does NOT catch:
#: `git stash` run with `--no-verify`-adjacent tricks that skip hooks
#: entirely is not applicable here (no such flag exists for reference-
#: transaction), but `GIT_HOOKS_PATH`/`core.hooksPath` overridden to an
#: empty or different directory at invocation time DOES bypass it, as
#: does deleting/renaming the hook file, or a non-CLI git binding
#: (libgit2, an IDE's stash panel) that does not invoke the hook chain the
#: same way the `git` CLI does. It is the strongest mechanical option
#: verified to actually intercept `git stash` through this repo's own git
#: version -- not an unbypassable sandbox.
_STASH_GUARD_HOOK_NAME = "reference-transaction"

#: T-0574: the stash-guard hook's own name(s), exposed the same shape as
#: `MANAGED_HOOK_NAMES` (a tuple, even though there is exactly one today)
#: so a block-count computation like `scaffold_conformance_status`'s test
#: can stay structural (`len(MANAGED_TEXT_BLOCKS) + len(MANAGED_HOOK_NAMES)
#: + len(STASH_GUARD_HOOK_NAMES)`) instead of a magic `+1` that silently
#: goes stale the next time a managed block is added or removed.
# frob:doc docs/commands/scaffold.md#managed-blocks-t-0736
STASH_GUARD_HOOK_NAMES: tuple[str, ...] = (_STASH_GUARD_HOOK_NAME,)
_STASH_GUARD_HOOK_MARKER = "# Installed by `frob scaffold apply` (T-0574 stash guard)."
# frob:ticket T-0870
_STASH_GUARD_HOOK_SCRIPT = f"""#!/bin/sh
{_STASH_GUARD_HOOK_MARKER}
#
# Refuses to let a `git stash` ref-update land while more than one
# worktree exists for this clone (docs/guides/agent-playbook.md#1b) --
# see this module's `_STASH_GUARD_HOOK_SCRIPT` docstring-comment for why
# a `reference-transaction` hook, not a hook name / alias, is what this
# has to be.
#
# T-0870: `git gc` (pack-refs) rewrites refs/stash's STORAGE (loose ->
# packed) WITHOUT changing its resolved VALUE -- but it does this as TWO
# separate reference-transaction invocations (one 0000->X adding the
# packed entry, one X->0000 pruning the now-redundant loose file), never
# as a single old==new line -- so old_oid == new_oid never actually
# happens in practice and is not a usable signal. Instead: only refuse a
# line that WRITES a new/changed value (new_oid not all-zero) whose value
# does not already match what refs/stash currently resolves to -- a
# maintenance repack's "add to packed-refs" half writes the SAME value
# refs/stash already has (the loose ref file is still present at
# "prepared" time, so `git rev-parse refs/stash` still resolves to it),
# so it is let through; a genuine `git stash push`/update always writes a
# value that does not match what refs/stash currently resolves to (there
# is no ref yet, or it resolves to the OLD, different, entry), so it is
# still refused. Pure deletions (new_oid all-zero -- a repack's loose-file
# prune, or a `stash pop`/`drop`) never collide across worktrees and are
# never blocked either way.
state="$1"
[ "$state" = "prepared" ] || exit 0
zero_oid="0000000000000000000000000000000000000000"
blocked=0
while read -r old_oid new_oid refname; do
    case "$refname" in
        refs/stash)
            if [ "$new_oid" != "$zero_oid" ]; then
                current_oid=$(git rev-parse -q --verify refs/stash 2>/dev/null)
                [ "$current_oid" = "$new_oid" ] || blocked=1
            fi
            ;;
    esac
done
[ "$blocked" -eq 1 ] || exit 0
n=$(git worktree list --porcelain 2>/dev/null | grep -c '^worktree ')
if [ "$n" -gt 1 ]; then
    echo "frob: refusing 'git stash' -- $n worktrees exist for this clone" >&2
    echo "frob: git stash writes to refs/stash, SHARED across every worktree" >&2
    echo "frob: docs/guides/agent-playbook.md#1b -- commit WIP, don't stash" >&2
    exit 1
fi
exit 0
"""

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
# frob:waive COV007 reason="T-0871: same -- see COV005 waiver above"
@dataclass(frozen=True)
class _ManagedTextBlock:
    """One frob-owned marked region: `block_id` identifies it, `target` is
    the repo-relative file it lives in, `content` is the exact text
    installed between its markers (T-0736)."""

    block_id: str
    target: str
    content: str


#: T-0864's `frob natives build` shim, verbatim from this repo's own
#: Makefile -- this IS the canonical definition; the landed `core:` target
#: is read here as source of truth, not duplicated by hand. T-0865: this
#: replaced T-0732's old literal per-repo maturin/CARGO_TARGET_DIR recipe
#: (kept as `_LEGACY_CARGO_CACHE_MARKERS` below purely as the drift
#: signature to detect, never re-emitted) now that `frob natives build`
#: owns the shared-cache mechanism itself -- no cache logic belongs in an
#: adopter repo's Makefile anymore.
_MAKEFILE_CORE_SHIM = """\
# Build and install every declared [[native]] extension into the venv
# (T-0732/T-0864). Smart-dup R3+ and strata design-model parsing need
# them; everything else works without them. `frob natives build` (frob's
# own subcommand) reads frob.toml's [[native]] entries, is best-effort
# when the Rust toolchain is absent, and owns the git-common-dir-keyed
# shared CARGO_TARGET_DIR mechanism itself -- no cache logic lives in this
# Makefile anymore. Requires a STAMP variable (venv install stamp) to
# already be defined -- see the Makefile shim installed by `frob scaffold
# apply`.
core: $(STAMP)
\tuv run frob natives build
"""

# frob:ticket T-0865
#: A repo's OWN `core:` recipe still carrying the pre-T-0864 per-repo
#: native-build/cache logic (the exact drift that motivated T-0735's
#: parent) rather than the one-line shim above -- these are the literal
#: variable-assignment / recipe-invocation shapes only the OLD hand-
#: maintained recipe used (never the current shim's own prose, which
#: mentions "CARGO_TARGET_DIR" and "maturin develop" only descriptively,
#: never as an actual assignment or invocation), so their presence in a
#: Makefile's `core:` recipe outside the managed-block markers is an
#: unambiguous drift signature.
_LEGACY_CARGO_CACHE_MARKERS: tuple[str, ...] = (
    "CARGO_TARGET_DIR :=",
    "maturin develop --uv --release",
)

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
MANAGED_TEXT_BLOCKS: tuple[_ManagedTextBlock, ...] = (
    _ManagedTextBlock(
        block_id="makefile-core-shim", target="Makefile", content=_MAKEFILE_CORE_SHIM
    ),
    _ManagedTextBlock(
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


# frob:waive EXHAUST003 reason="T-1402: EXHAUST001 narrowed to fire for an own \
# ambiguous bare re-raise; this leaked Unknown traces to an unresolved callee instead \
# (the demoted case). T-1062: leaked Unknown traces to _marker_begin/ _marker_end \
# (plain str-formatting helpers) and str.strip on the sliced result, neither of which \
# the resolver can statically bound; the one real raise path (str.index) is caught \
# below"
# frob:waive EXHAUST002 reason="T-1062: same resolver artifact as EXHAUST001 above"
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


# frob:ticket T-0865
# frob:tests \
# tests/unit/test_scaffold_natives_shim.py::TestLegacyCoreCacheDrift.test_legacy_unmana\
# ged_core_target_reports_stale  # noqa: E501
def _has_legacy_core_cache_logic(text: str) -> bool:
    """True if `text` (a Makefile's full contents, markers not yet
    stripped) still carries the pre-T-0864 per-repo native-build cache
    recipe (`_LEGACY_CARGO_CACHE_MARKERS`) instead of the current one-line
    `frob natives build` shim -- the estate-conformance drift T-0865
    exists to catch (T-0735's parent motivation: per-repo cache hacks at
    the wrong layer)."""
    return any(marker in text for marker in _LEGACY_CARGO_CACHE_MARKERS)


def _text_block_status(root: Path, block: _ManagedTextBlock) -> ManagedBlockStatus:
    """`ManagedBlockStatus` for one `_ManagedTextBlock` under `root`: absent
    file or absent marker pair is `present=False`; a present region whose
    digest differs from the canonical content's is `stale=True`.

    T-0865: for the `makefile-core-shim` block specifically, a Makefile
    with NO managed-block markers but that still carries the legacy
    per-repo cache recipe (`_has_legacy_core_cache_logic`) is reported as
    `present=True, stale=True` rather than plain `present=False` --
    distinguishing "never adopted the shim" (a real drift naming the shim
    as remedy) from "genuinely has nothing here yet" (a clean `apply`
    append)."""
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
    text = path.read_text(encoding="utf-8")
    region = _extract_region(text, block.block_id)
    if region is None:
        if block.block_id == "makefile-core-shim" and _has_legacy_core_cache_logic(
            text
        ):
            return ManagedBlockStatus(
                block_id=block.block_id,
                target=block.target,
                kind="text",
                present=True,
                stale=True,
                expected_digest=expected_digest,
            )
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
# frob:doc \
# docs/guides/agent-playbook.md#1b-never-git-stash-in-a-worktree-it-is-repo-global-not-\
# worktree-local  # noqa: E501
# frob:tests \
# tests/unit/test_scaffold_managed.py::TestScaffoldConformanceStatus.test_non_frob_repo\
# _reports_nothing  # noqa: E501
# frob:tests \
# tests/unit/test_scaffold_managed.py::TestScaffoldConformanceStatus.test_clean_after_a\
# pply  # noqa: E501
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

    statuses = (
        tuple(_text_block_status(root, b) for b in MANAGED_TEXT_BLOCKS)
        + tuple(_hook_status(root, name) for name in MANAGED_HOOK_NAMES)
        + (_stash_guard_status(root),)
    )
    _log.info(
        "scaffold conformance: %d block(s), %d missing, %d stale",
        len(statuses),
        sum(1 for s in statuses if not s.present),
        sum(1 for s in statuses if s.stale),
    )
    return statuses


# frob:tests \
# tests/unit/test_scaffold_managed.py::TestStashGuardBlock.test_refuses_to_clobber_fore\
# ign_reference_transaction_hook  # noqa: E501
# frob:tests \
# tests/unit/test_scaffold_managed.py::TestStashGuardBlock.test_stale_ours_stash_guard_\
# hook_is_updated  # noqa: E501
def _stash_guard_status(root: Path) -> ManagedBlockStatus:
    """`ManagedBlockStatus` for the T-0574 `reference-transaction` stash
    guard hook: `present` reflects whether the hooks-dir file exists
    (missing hooks dir/not a git repo reports `present=False`, never
    raises); `stale` is True only for a hook that IS ours (carries
    `_STASH_GUARD_HOOK_MARKER`) but whose body no longer matches the
    current canonical script -- a foreign (non-frob) hook of the same
    name is reported present, not-stale, mirroring `_hook_status`."""
    expected_digest = _digest(_STASH_GUARD_HOOK_SCRIPT)
    hooks_dir_result = _hooks_dir(root)
    if hooks_dir_result.is_err:
        return ManagedBlockStatus(
            block_id="hook-reference-transaction-stash-guard",
            target=f".git/hooks/{_STASH_GUARD_HOOK_NAME}",
            kind="hook",
            present=False,
            stale=False,
            expected_digest=expected_digest,
        )
    path = hooks_dir_result.danger_ok / _STASH_GUARD_HOOK_NAME
    if not path.exists():
        return ManagedBlockStatus(
            block_id="hook-reference-transaction-stash-guard",
            target=f".git/hooks/{_STASH_GUARD_HOOK_NAME}",
            kind="hook",
            present=False,
            stale=False,
            expected_digest=expected_digest,
        )
    body = path.read_text(encoding="utf-8")
    is_ours = _STASH_GUARD_HOOK_MARKER in body
    actual_digest = _digest(body)
    return ManagedBlockStatus(
        block_id="hook-reference-transaction-stash-guard",
        target=f".git/hooks/{_STASH_GUARD_HOOK_NAME}",
        kind="hook",
        present=True,
        stale=is_ours and actual_digest != expected_digest,
        expected_digest=expected_digest,
        actual_digest=actual_digest if is_ours else None,
    )


# frob:tests \
# tests/unit/test_scaffold_managed.py::TestStashGuardBlock.test_refuses_to_clobber_fore\
# ign_reference_transaction_hook  # noqa: E501
# frob:tests \
# tests/unit/test_scaffold_managed.py::TestStashGuardBlock.test_stale_ours_stash_guard_\
# hook_is_updated  # noqa: E501
def _apply_stash_guard(root: Path) -> str:
    """Idempotently install/update the T-0574 `reference-transaction`
    stash-guard hook under `root`: no-op if already current, force-
    updates a stale-but-ours hook, installs fresh if absent, and leaves a
    foreign (non-frob) hook of the same name untouched -- reported, never
    overwritten, same posture `_apply_hooks` takes for the T-0431 hooks."""
    status = _stash_guard_status(root)
    if status.present and status.actual_digest is None:
        return (
            f"hook {_STASH_GUARD_HOOK_NAME}: present and NOT frob's own, left untouched"
        )
    if status.present and not status.stale:
        return f"hook {_STASH_GUARD_HOOK_NAME}: already current"

    hooks_dir_result = _hooks_dir(root)
    if hooks_dir_result.is_err:
        _log.warning(
            "scaffold apply: could not resolve hooks dir under %s (%s)",
            root,
            hooks_dir_result.danger_err.value,
        )
        return f"hook {_STASH_GUARD_HOOK_NAME}: install failed (no hooks dir)"
    path = hooks_dir_result.danger_ok / _STASH_GUARD_HOOK_NAME
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_STASH_GUARD_HOOK_SCRIPT, encoding="utf-8")
        path.chmod(0o755)
    except OSError as exc:
        _log.warning(
            "scaffold apply: failed to write stash guard hook to %s: %s", path, exc
        )
        return f"hook {_STASH_GUARD_HOOK_NAME}: install failed ({exc})"
    verb = "updated stale" if status.present else "installed"
    _log.info("scaffold apply: %s stash guard hook under %s", verb, root)
    return f"hook {_STASH_GUARD_HOOK_NAME}: {verb}"


def _apply_text_block(root: Path, block: _ManagedTextBlock) -> str:
    """Idempotently install/update one `_ManagedTextBlock` under `root`:
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
# frob:tests \
# tests/unit/test_scaffold_managed.py::TestApplyManagedBlocks.test_idempotent_second_ru\
# n_is_noop  # noqa: E501
# frob:tests \
# tests/unit/test_scaffold_managed.py::TestApplyManagedBlocks.test_creates_missing_and_\
# updates_stale  # noqa: E501
# frob:tests \
# tests/unit/test_scaffold_managed.py::TestApplyManagedBlocks.test_refuses_to_clobber_f\
# oreign_hook  # noqa: E501
def apply_managed_blocks(root: Path) -> Result[tuple[str, ...], ScaffoldError]:
    """Idempotently install/update every managed text block and the
    worktree-lease hooks under `root` (T-0736). Never fails on a foreign
    (non-frob) hook of the same name -- reports it and leaves it alone
    instead. Returns one description string per block/hook, in
    `MANAGED_TEXT_BLOCKS` order followed by the hooks, for `frob scaffold
    apply`'s CLI output and the Done-report evidence trail."""
    changes: list[str] = [_apply_text_block(root, b) for b in MANAGED_TEXT_BLOCKS]
    changes.extend(_apply_hooks(root))
    changes.append(_apply_stash_guard(root))
    return Ok(tuple(changes))


__all__ = [
    "MANAGED_HOOK_NAMES",
    "MANAGED_TEXT_BLOCKS",
    "STASH_GUARD_HOOK_NAMES",
    "ManagedBlockStatus",
    "_ManagedTextBlock",
    "apply_managed_blocks",
    "scaffold_conformance_status",
]
