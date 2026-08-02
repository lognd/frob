"""`frob ticket land` -- git-plumbing/wip-commit machinery.

See docs/modules/tickets.md#frob-ticket-land.

Split out of `frob.tickets._land_merge` (T-1251, continuing the verbatim-
move discipline T-1186/T-1189/T-1192/T-1194 established): the git-plumbing
and wip-commit family -- main-into-worktree merge staging
(`_merge_main_into_worktree`), out-of-scope conflict auto-resolution
(`_auto_resolve_out_of_scope_conflicts`), the wip-commit trio
(`_wip_commit`/`_wip_add_excluding_frob`/`_do_wip_commit`), ledger/archive
splice-and-stage (`_splice_and_stage`/`_splice_and_stage_archive`,
`_verify_archive_merge`), the deletion-authorization pair
(`_deletion_glob_too_broad`/`_deletion_owned`, moved alongside
`_unowned_deletions` which uses them, per T-1251's own residue note), the
`frob:waive`-deletion laundering guards (T-1323/T-1326), and the small git
primitives this family shares (`_rev_parse`, `_true_merge_base`,
`_land_internal_git_env`, `_describe_git_failure`,
`_is_ignored_path_refusal`, `_verified_reset_root`, `_porcelain_dirty`,
`_diff_is_frob_version_line_only`, `_restore_lock_version_only_drift`,
`_conflicted_files`, `_abort_merge`, `_archived_ids`). Zero caller-visible
behavior change -- every moved function keeps its original body, docstring,
and `frob:ticket`/`frob:tests` directives verbatim; `frob.tickets._land_merge`
and `frob.tickets._land_finalize` import what they still need back from
here.

`_land_merge.py` keeps the closeability-validation family
(`_validate_closeable`/`_validate_acceptance_bound`/
`_validate_evidence_kind_consistency`) and the commit-message helper
(`_commit_message`), plus its re-export of `splice_ledger` for
`frob.tickets.__init__`'s stable public import path.
"""
# frob:waive INV006 preset="split-carried-prose"
# frob:waive LARGE001 reason="T-1251 verbatim extraction seam: 1063 lines is the moved git-plumbing family intact, one seam per land; the follow-on split of this family (and _land_finalize.py's) is the T-1251-residue draft ticket filed at close -- waived rather than force-split in the same diff to preserve the byte-identical-move review guarantee"  # noqa: E501

from __future__ import annotations

import fnmatch
import json
import os
import re
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from typani.result import Err, Ok, Result

from frob.gitio import run_argv
from frob.logging import get_logger
from frob.tickets._land_ledger_merge import (
    _merge_ledger_tickets,
    _splice_only_ticket,
    splice_ledger,
)
from frob.tickets._land_merge_zones import (
    _resolve_union_zone_conflicts,
    _zone_for_path,
)
from frob.tickets._models import (
    LandError,
    Ticket,
    _done_report_section_lines,
    scope_matches,
)
from frob.tickets._store import (
    _check_ledger_id_integrity,
    _parse_ledger,
    _render_ledger,
    archive_path,
    ledger_path,
)

_log = get_logger(__name__)


@contextmanager
def _land_internal_git_env() -> Iterator[None]:
    """Set `FROB_LAND_INTERNAL=1` in the process environment for the
    duration of a land-internal git commit spawn (T-0828). The T-0731
    scaffolded `pre-commit` hook refuses a worktree/main commit that
    touches a land-owned file (CHANGELOG.md, uv.lock, pyproject.toml's
    version line) unless this is set -- `land()`'s OWN commits (the
    worktree wip snapshot, the main-into-worktree merge commit, the
    finalize/close commit, and the main-side squash-apply commit, which
    can legitimately carry a REL001 version bump + generated changelog
    entry) must set it around every one of those spawns or the hook
    deadlocks land against itself. Restores the prior value (or absence)
    of the variable on exit rather than leaking it into unrelated spawns
    this process makes afterward."""
    # frob:waive SEC110 reason="internal reentrancy marker, not a secret"
    prior = os.environ.get("FROB_LAND_INTERNAL")
    # frob:waive SEC110 reason="internal reentrancy marker, not a secret"
    os.environ["FROB_LAND_INTERNAL"] = "1"
    try:
        yield
    finally:
        if prior is None:
            os.environ.pop("FROB_LAND_INTERNAL", None)
        else:
            # frob:waive SEC110 reason="restoring reentrancy marker, not a secret"
            os.environ["FROB_LAND_INTERNAL"] = prior


def _describe_git_failure(argv: Sequence[str], spawned: Result[Any, Any]) -> str:
    """A one-line, diagnosable description of a failed `run_argv` spawn --
    the failing argv plus its stderr (or the spawn-level error if the
    process never even completed) -- so a hook-class refusal (e.g. the
    T-0731 pre-commit guard) is readable from a single log line instead of
    collapsing to a bare `GitFailed` with no context (T-0828)."""
    rendered_argv = " ".join(str(a) for a in argv)
    if spawned.is_err:
        return f"git {rendered_argv} -- spawn error: {spawned.danger_err}"
    result = spawned.danger_ok
    stderr = str(getattr(result, "stderr", "")).strip() or "(no stderr)"
    returncode = getattr(result, "returncode", "?")
    return f"git {rendered_argv} -- exit {returncode}: {stderr}"


# frob:ticket T-1184
def _is_ignored_path_refusal(stderr: str) -> bool:
    """Whether a failed `git add` spawn's stderr is git's "explicitly named
    an ignored path" refusal (T-1184) -- narrowly matched on
    git's own fixed message text so `_do_wip_commit`'s fallback only
    triggers on this exact known failure mode, never masking a genuinely
    different `git add` error as if it were this one."""
    return "ignored by one of your .gitignore files" in stderr


# frob:ticket T-0907
def _verified_reset_root(
    root: Path, pre_land_tip: str, ticket_id: str
) -> Result[None, LandError]:
    """Unwind `root`'s staged squash-apply back to `pre_land_tip` -- the
    T-0907 replacement for a bare `git reset --hard` (which resolves its
    target from whatever `HEAD` happens to be AT RESET TIME, the exact
    hazard the incident this ticket fixes exploited): resets to an
    EXPLICIT sha captured once at this run's start, and refuses loudly
    (`Err(GitFailed)`, no reset performed) if `root`'s current tip has
    already drifted from `pre_land_tip` by the time this runs -- root's
    tip must never move between this run's start and its own final commit
    (`_commit_squash_apply`), so any drift here means something else
    touched `root` mid-run and blindly resetting over it would risk
    exactly the T-0907 incident class."""
    current = _rev_parse(root, "HEAD")
    if current.is_err:
        return Err(current.danger_err)
    if current.danger_ok != pre_land_tip:
        _log.error(
            "land: %s refused to unwind %s -- current tip is %s but this "
            "run's recorded pre-land tip is %s (drift detected mid-"
            "staging, T-0907) -- NOT resetting; inspect `git -C %s reflog` "
            "and `git -C %s log --oneline -5` by hand before retrying",
            ticket_id,
            root,
            current.danger_ok,
            pre_land_tip,
            root,
            root,
        )
        return Err(LandError.GitFailed)
    reset = run_argv(["git", "-C", str(root), "reset", "--hard", pre_land_tip])
    if reset.is_err or reset.danger_ok.returncode != 0:
        return Err(LandError.GitFailed)
    clean = run_argv(["git", "-C", str(root), "clean", "-fd"])
    if clean.is_err or clean.danger_ok.returncode != 0:
        return Err(LandError.GitFailed)
    return Ok(None)


def _porcelain_dirty(root: Path) -> Result[bool, LandError]:
    """Whether `root`'s working tree has any uncommitted change (tracked or
    not), ignoring `.frob/` (T-0577): `land`'s own `ledger_lock` creates
    `.frob/tickets.lock` in `root` BEFORE this check ever runs (the whole
    `land()` body, `_refuse_if_main_dirty` included, now runs under that
    lock -- see `land`'s docstring), and `.frob/` is frob-local scratch
    state a repo is expected to `.gitignore` anyway (baseline/coverage
    stamps, journal records, this same lock file) -- never a real
    "uncommitted change" a landing should refuse on."""
    spawned = run_argv(["git", "-C", str(root), "status", "--porcelain"])
    if spawned.is_err or spawned.danger_ok.returncode != 0:
        _log.error("land: git status failed in %s", root)
        return Err(LandError.GitFailed)
    dirty_lines = [
        line
        for line in spawned.danger_ok.stdout.splitlines()
        if line.strip() and not line[3:].strip().startswith(".frob/")
    ]
    return Ok(bool(dirty_lines))


# frob:ticket T-0793
_LOCK_VERSION_LINE = re.compile(r'^[+-]version = "[^"]*"$')


# frob:ticket T-0793
def _diff_is_frob_version_line_only(diff_text: str) -> bool:
    """Whether a unified `git diff` body touches nothing but a single
    `version = "..."` line flip (one removed, one added) inside the
    `name = "frob"` package stanza -- the shape uv.lock's own frob-
    version line takes on every `uv run`/`uv lock` against a pyproject
    whose version was just bumped by a sibling land, with no other lock
    content changed. Used to gate the DirtyMain auto-restore (T-0793) so
    a REAL lock drift (a dependency actually changed) still refuses
    normally instead of being silently discarded."""
    changed = [
        line
        for line in diff_text.splitlines()
        if (line.startswith("+") or line.startswith("-"))
        and not line.startswith("+++")
        and not line.startswith("---")
    ]
    if len(changed) != 2:
        return False
    if not all(_LOCK_VERSION_LINE.match(line) for line in changed):
        return False
    return 'name = "frob"' in diff_text


# frob:ticket T-0793
def _restore_lock_version_only_drift(root: Path) -> bool:
    """Auto-restore `root`'s `uv.lock` (T-0793) when the ONLY uncommitted
    change in the whole tree is uv.lock's frob-version line flapping on
    every `uv run` against a pyproject bumped by a prior land -- left
    alone, this alone trips `_refuse_if_main_dirty`'s DirtyMain refusal
    on every subsequent land attempt until someone runs `git checkout --
    uv.lock` by hand first (the recurring friction this ticket exists to
    kill). Returns `True` (and restores the file, clearing the drift)
    only when `uv.lock` is the SOLE dirty path AND its diff is exactly
    the version-line-only shape `_diff_is_frob_version_line_only` checks
    for; any other drift (a real lock change, a second dirty file) is
    left completely untouched and this returns `False` so the ordinary
    DirtyMain refusal still fires unchanged."""
    status = run_argv(["git", "-C", str(root), "status", "--porcelain"])
    if status.is_err or status.danger_ok.returncode != 0:
        return False
    dirty_lines = [
        line
        for line in status.danger_ok.stdout.splitlines()
        if line.strip() and not line[3:].strip().startswith(".frob/")
    ]
    if len(dirty_lines) != 1 or dirty_lines[0][3:].strip() != "uv.lock":
        return False
    diff = run_argv(["git", "-C", str(root), "diff", "--", "uv.lock"])
    if diff.is_err or diff.danger_ok.returncode != 0:
        return False
    if not _diff_is_frob_version_line_only(diff.danger_ok.stdout):
        return False
    restored = run_argv(["git", "-C", str(root), "checkout", "--", "uv.lock"])
    return restored.is_ok and restored.danger_ok.returncode == 0


# T-1434: the literal path `frob.gates._coverage._LOCK_REL` names -- NOT
# imported from there. `frob.gates` already imports FROM `frob.tickets`
# (e.g. `frob.gates._coverage.enforce_worktree_lease`,
# `frob.gates._todo_fmt.TicketQueue`), so importing `frob.gates._coverage`
# from this module would be circular; a plain string literal is the
# cheapest way to name the one path this module needs to special-case
# without inventing a shared constants module for a single filename.
_COVERAGE_LOCK_PATH = "frob-coverage.lock.json"


# frob:ticket T-1434
def _merged_lock_doc(ours_text: str, theirs_text: str) -> dict | None:
    """The elementwise-max merge of two coverage-lock JSON texts
    (`_merge_coverage_lock_conflict`'s pure half): per module, the higher
    of both sides' `module_line` percentage; `source_sha` from whichever
    side carries more modules (proxy for the more complete run). `None`
    when either side fails to parse as the expected
    `{"source_sha": ..., "module_line": {...}}` shape."""
    try:
        ours_doc = json.loads(ours_text)
        theirs_doc = json.loads(theirs_text)
    except ValueError:
        return None
    ours_lines = ours_doc.get("module_line")
    theirs_lines = theirs_doc.get("module_line")
    if not isinstance(ours_lines, dict) or not isinstance(theirs_lines, dict):
        return None
    merged_lines: dict[str, float] = dict(ours_lines)
    for module, theirs_pct in theirs_lines.items():
        ours_pct = merged_lines.get(module)
        if ours_pct is None or theirs_pct > ours_pct:
            merged_lines[module] = theirs_pct
    source_sha = (
        ours_doc.get("source_sha")
        if len(ours_lines) >= len(theirs_lines)
        else theirs_doc.get("source_sha")
    )
    return {
        "source_sha": source_sha,
        "module_line": dict(sorted(merged_lines.items())),
    }


# frob:ticket T-1434
# frob:tests tests/test_ticket_land.py::TestCoverageLockConflictMerges.test_conflicting_lock_merges_to_the_higher_of_both_sides  # noqa: E501
def _merge_coverage_lock_conflict(cwd: Path, path: str) -> bool:
    """Resolve a genuine merge conflict on `frob-coverage.lock.json` by
    taking the ELEMENTWISE MAX of both sides' `module_line` percentages,
    rather than blindly keeping one side (T-1434).

    T-1434 confirmed a real defect: `_auto_resolve_out_of_scope_conflicts`
    resolves any out-of-scope conflicted path by unconditionally keeping
    one side (`git checkout --<keep>`) -- correct for an ordinary source
    file (main's side is definitionally authoritative for something the
    landing ticket never touched), but wrong for this file specifically.
    `frob-coverage.lock.json` is a committed coverage-ratchet artifact
    (`write_coverage_lock`/`_apply_lock_ratchet` in
    `frob.gates._coverage`, T-1363): a conflict here means BOTH sides ran
    their own `--stamp-coverage` since diverging, and blindly keeping one
    side silently discards the other's real, freshly measured numbers --
    exactly the "a freshly stamped lock reverted to an older committed
    value" shape T-1270's agent observed. This is the same "never
    silently lower a committed floor" principle `_apply_lock_ratchet`
    already applies to a single side's own write, extended across a
    two-sided merge: for every module present on either side, keep
    whichever side's percentage is HIGHER (a module only on one side
    keeps that side's value unchanged). `source_sha` is taken from
    whichever side has the larger `module_line` (a rough proxy for "more
    complete run"; a real re-stamp is expected to correct it at the next
    `--stamp-coverage` regardless).

    Returns `True` (and stages the merged file) only when BOTH sides
    parse as the expected `{"source_sha": ..., "module_line": {...}}`
    shape; returns `False` (leave conflicted, exactly as before T-1434)
    for anything else -- a malformed side, a missing stage, or a git
    failure -- so this never guesses on data it cannot make sense of.
    """
    ours = run_argv(["git", "-C", str(cwd), "show", f":2:{path}"])
    theirs = run_argv(["git", "-C", str(cwd), "show", f":3:{path}"])
    if ours.is_err or ours.danger_ok.returncode != 0:
        return False
    if theirs.is_err or theirs.danger_ok.returncode != 0:
        return False
    merged_doc = _merged_lock_doc(ours.danger_ok.stdout, theirs.danger_ok.stdout)
    if merged_doc is None:
        return False
    full_path = cwd / path
    try:
        full_path.write_text(
            json.dumps(merged_doc, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except OSError:
        return False
    add = run_argv(["git", "-C", str(cwd), "add", "--", path])
    if add.is_err or add.danger_ok.returncode != 0:
        return False
    _log.info(
        "land: merged conflicting %s -- kept the higher of both sides' "
        "module_line percentages for every module (T-1434), never "
        "blindly discarding one side's freshly stamped data",
        path,
    )
    return True


def _conflicted_files(root: Path) -> set[str]:
    """Paths git currently reports unmerged (`U`) in `root`'s index."""
    spawned = run_argv(
        ["git", "-C", str(root), "diff", "--name-only", "--diff-filter=U"]
    )
    if spawned.is_err or spawned.danger_ok.returncode != 0:
        return set()
    return {
        line.strip() for line in spawned.danger_ok.stdout.splitlines() if line.strip()
    }


def _deletion_glob_too_broad(glob: str) -> bool:
    """Whether a scope glob is too broad to trust for authorizing a
    DELETION (D-12): a bare top-level directory (`src/`, expanded to
    `src/**`) or the whole-tree `.`/`*` pattern. `scope_matches`'s
    ordinary dir-glob expansion (T-0241) is correct for the general
    "is this file in scope" question, but a ticket scoped only to a
    single top-level directory silently authorizes deleting ANYTHING
    under it -- exactly the stale-base incident class this filter exists
    to catch. A more specific glob (`src/frob/`, `src/frob/tickets/**`)
    is still trusted."""
    stripped = glob.removesuffix("/**").removesuffix("/*").rstrip("/")
    if stripped in ("", ".", "*"):
        return True
    return "/" not in stripped


def _deletion_owned(path: str, scope: tuple[str, ...]) -> bool:
    """Whether `path` is authorized as an OWNED deletion by `scope`: matches
    `scope_matches` AND is not matched only via an over-broad glob (D-12).
    Deliberately stricter than plain `scope_matches`, and used only
    by the deletion filter -- every other scope-consulting site (SCOPE001,
    pre-work digests, ordinary in-scope checks) keeps the normal
    `scope_matches` semantics unchanged."""
    from frob.tickets._models import _scope_globs, _split_scope_entries

    narrow_globs = [
        glob
        for glob in _scope_globs(_split_scope_entries(scope))
        if not _deletion_glob_too_broad(glob)
    ]
    return any(fnmatch.fnmatch(path, glob) for glob in narrow_globs)


def _abort_merge(worktree: Path) -> None:
    """Best-effort `git merge --abort` to leave the worktree exactly as found."""
    run_argv(["git", "-C", str(worktree), "merge", "--abort"])


def _archived_ids(root: Path) -> frozenset[str]:
    """Every ticket id in `root`'s `tickets-archive.md` -- the authoritative
    "already archived, must never re-enter the active ledger" set a splice
    guards against (T-0176 reviewer fix). An unreadable/malformed archive
    degrades to empty rather than blocking the land -- archive resurrection
    is a correctness bug worth guarding against, not a reason to hard-fail
    a landing whose archive happens to be unparseable for an unrelated
    reason."""
    path = archive_path(root)
    if not path.exists():
        return frozenset()
    parsed = _parse_ledger(path.read_text(encoding="utf-8"))
    if parsed.is_err:
        _log.warning(
            "land: %s unreadable (%s), archive-resurrection guard degraded to empty",
            path,
            parsed.danger_err,
        )
        return frozenset()
    return frozenset(parsed.danger_ok)


def _splice_and_stage(
    checkout: Path,
    pre_text: str,
    incoming_text: str,
    *,
    archived_ids: frozenset[str] = frozenset(),
    ticket_id: str | None = None,
) -> Result[str, LandError]:
    """Write the ledger splice of `pre_text`/`incoming_text` to `checkout`'s
    tickets.md and `git add` it; overrides whatever git's own textual merge
    produced -- tickets.md is ALWAYS resolved via a splice, never via git's
    line-level algorithm, so a both-sides-append never false-conflicts and a
    same-id divergence always keeps the newest state (T-0176).

    `ticket_id`, when given, scopes the splice to ONLY that ticket's own
    block via `_splice_only_ticket` (T-0479) -- every other id comes from
    `pre_text` untouched, so a worktree's stale sibling-ticket state can
    never overlay main's newer one. `ticket_id=None` (the default) keeps the
    original whole-ledger `splice_ledger` merge, used only where BOTH sides
    are pulling in each other's full set of tickets on purpose (there is no
    "one ticket being landed" to scope to). `archived_ids` excludes anything
    main has already archived from ever re-entering the merged active
    ledger, either way."""
    if ticket_id is not None:
        spliced = _splice_only_ticket(
            pre_text, incoming_text, ticket_id, archived_ids=archived_ids
        )
    else:
        spliced = splice_ledger(pre_text, incoming_text, archived_ids=archived_ids)
    if spliced.is_err:
        _log.error(
            "land: tickets.md splice failed (%s) -- resolve manually in %s",
            spliced.danger_err,
            checkout,
        )
        return Err(LandError.GitFailed)
    ledger_path(checkout).write_text(spliced.danger_ok, encoding="utf-8")
    add = run_argv(["git", "-C", str(checkout), "add", "tickets.md"])
    if add.is_err or add.danger_ok.returncode != 0:
        return Err(LandError.GitFailed)
    return Ok(spliced.danger_ok)


def _read_ledger_text_or_empty(checkout: Path) -> str:
    """`tickets.md`'s text under `checkout`, or `""` if it does not exist."""
    path = ledger_path(checkout)
    return path.read_text(encoding="utf-8") if path.exists() else ""


# frob:ticket T-0959
def _read_archive_text_or_empty(checkout: Path) -> str:
    """`tickets-archive.md`'s text under `checkout`, or `""` if it does not
    exist -- the archive-file twin of `_read_ledger_text_or_empty` (T-0959)."""
    path = archive_path(checkout)
    return path.read_text(encoding="utf-8") if path.exists() else ""


# frob:ticket T-1154
def _read_text_at_ref(worktree: Path, ref: str, relative_path: str) -> str | None:
    """`git show <ref>:<relative_path>` inside `worktree`, or `None` on any
    failure (missing at that ref, non-zero exit) -- used to fetch a ledger/
    archive file's content AT THE TRUE MERGE-BASE commit (T-1154), never a
    hard failure since a merge-base-aware splice is a sharpening of the
    existing `_newer` tiebreak, not a new hard requirement."""
    result = run_argv(["git", "-C", str(worktree), "show", f"{ref}:{relative_path}"])
    if result.is_err or result.danger_ok.returncode != 0:
        return None
    return result.danger_ok.stdout


# frob:ticket T-0959
# frob:tests tests/test_ticket_land.py::TestArchiveSpliceDiscipline.test_splice_and_stage_archive_merges_by_id_never_overwrites  # noqa: E501
# frob:tests tests/test_ticket_land.py::TestArchiveSpliceDiscipline.test_splice_and_stage_archive_refuses_when_authoritative_id_would_vanish  # noqa: E501
def _parse_archive_side(
    text: str, side: str, checkout: Path
) -> Result[dict[str, Ticket], LandError]:
    """Parse one side of the archive splice, refusing loudly (T-0959) rather
    than letting an unparseable copy silently fall out of the union merge."""
    parsed = _parse_ledger(text)
    if parsed.is_err:
        _log.error(
            "land: tickets-archive.md splice refused -- %s copy "
            "unparseable (%s), resolve manually in %s",
            side,
            parsed.danger_err,
            checkout,
        )
        return Err(LandError.GitFailed)
    return Ok(parsed.danger_ok)


def _verify_archive_merge(
    authoritative: dict[str, Ticket], merged: dict[str, Ticket], checkout: Path
) -> Result[str, LandError]:
    """Render the merged archive after the T-0959 guards: every id in the
    authoritative (root/main pre-land) archive must survive the merge, and
    the rendered text must round-trip (`_check_ledger_id_integrity`,
    extending the T-0740 pattern to this file)."""
    missing = set(authoritative) - set(merged)
    if missing:
        _log.error(
            "land: tickets-archive.md splice refused -- id(s) %s present in "
            "the archive's pre-land authoritative state vanished from the "
            "merged result (T-0959 archive id-integrity guard); this must "
            "never happen by construction of a union merge -- inspect %s "
            "by hand before retrying",
            sorted(missing),
            checkout,
        )
        return Err(LandError.GitFailed)
    rendered = _render_ledger(merged)
    integrity = _check_ledger_id_integrity(merged, rendered)
    if integrity.is_err:
        _log.error(
            "land: tickets-archive.md splice failed its id-integrity "
            "round-trip check (%s) -- resolve manually in %s",
            integrity.danger_err,
            checkout,
        )
        return Err(LandError.GitFailed)
    return Ok(rendered)


def _splice_and_stage_archive(
    checkout: Path,
    authoritative_text: str,
    other_text: str,
    *,
    base_text: str | None = None,
) -> Result[str, LandError]:
    """Ledger-level splice of `tickets-archive.md` (T-0959): union both
    sides by id via `_merge_ledger_tickets` (never git's raw text merge --
    the T-0703 wholesale-stale-copy incident), verify no authoritative id
    vanishes, then write and `git add` the merged result.

    `authoritative_text` is always root/main's CURRENT copy (only main
    sweeps archives; a worktree copy is equal or stale). T-1154:
    `base_text` (true 3-way merge-base, optional, degrades to `_newer`-only
    when absent/unparseable) sharpens the per-id tiebreak -- see
    `_merge_ledger_tickets`/`_resolve_divergence` for the wrong-side-merge
    class this closes (the T-1145/T-1143 incident)."""
    authoritative_parsed = _parse_archive_side(
        authoritative_text, "authoritative", checkout
    )
    if authoritative_parsed.is_err:
        return Err(authoritative_parsed.danger_err)
    other_parsed = _parse_archive_side(other_text, "worktree", checkout)
    if other_parsed.is_err:
        return Err(other_parsed.danger_err)
    authoritative, other = authoritative_parsed.danger_ok, other_parsed.danger_ok
    base = None
    if base_text is not None:
        base_parsed = _parse_ledger(base_text)
        base = base_parsed.danger_ok if base_parsed.is_ok else None
    merged = _merge_ledger_tickets(authoritative, other, base=base)
    rendered_result = _verify_archive_merge(authoritative, merged, checkout)
    if rendered_result.is_err:
        return Err(rendered_result.danger_err)
    rendered = rendered_result.danger_ok
    archive_path(checkout).write_text(rendered, encoding="utf-8")
    add = run_argv(["git", "-C", str(checkout), "add", "tickets-archive.md"])
    if add.is_err or add.danger_ok.returncode != 0:
        return Err(LandError.GitFailed)
    return Ok(rendered)


def _merge_main_into_worktree(
    root: Path, worktree: Path, ticket: Ticket, main_branch: str
) -> Result[bool, LandError]:
    """Stage (`--no-commit`) main into the worktree, resolving any tickets.md
    conflict via `splice_ledger` and any tickets-archive.md conflict via the
    T-0959 archive splice (`_splice_and_stage_archive`); any OTHER
    conflicted file aborts loudly. Returns whether a merge actually happened
    (False = worktree was already up to date with main, a no-op).

    T-1154: also resolves the true 3-way merge-base's tickets-archive.md
    text (`_true_merge_base` + `_read_text_at_ref`, best-effort -- `None`
    on any failure) and threads it into the archive splice as `base_text`,
    so a same-id divergence prefers whichever side made a REAL edit over
    whichever side is merely stale relative to the branch point -- see
    `_merge_ledger_tickets`/`_resolve_divergence` for the wrong-side-merge
    class this closes. tickets.md's own splice (`_splice_and_stage`) does
    not need this: `ticket_id`-scoping (T-0479) already makes every sibling
    id come from `main_text` untouched, so the archive file -- whose splice
    is NOT scoped to one id -- is the one exposed to this class."""
    pre_text = _read_ledger_text_or_empty(worktree)
    main_text = _read_ledger_text_or_empty(root)
    # frob:ticket T-0959
    pre_archive_text = _read_archive_text_or_empty(worktree)
    main_archive_text = _read_archive_text_or_empty(root)
    # frob:ticket T-1154
    base_sha = _true_merge_base(worktree, main_branch)
    base_archive_text = (
        _read_text_at_ref(worktree, base_sha.danger_ok, "tickets-archive.md")
        if base_sha.is_ok
        else None
    )

    merged = run_argv(
        ["git", "-C", str(worktree), "merge", "--no-commit", "--no-ff", main_branch]
    )
    if merged.is_err:
        return Err(LandError.GitFailed)
    if (
        merged.danger_ok.returncode == 0
        and "up to date" in merged.danger_ok.stdout.lower()
    ):
        return Ok(False)

    conflict_check = _check_only_tickets_conflicted(worktree, ticket, main_branch)
    if conflict_check.is_err:
        return Err(conflict_check.danger_err)

    # T-0479/T-0475: base the splice on MAIN's ledger (main_text), not the
    # worktree's, and overlay ONLY the ticket being landed (`ticket.id`)
    # from the worktree's pre-merge copy. This is the exact site of the
    # T-0475 incident: the old whole-ledger merge based the splice on the
    # worktree's stale `pre_text`, so a sibling ticket the worktree still
    # remembered as in-progress (from before it was later requeued back to
    # queued on main) beat main's newer queued state on `_newer`'s state-
    # rank comparison and resurrected it. Scoping to `ticket.id` makes every
    # sibling ticket's state come from main untouched, unconditionally --
    # only the ticket actually being landed is ever taken from the
    # worktree.
    spliced = _splice_and_stage(
        worktree,
        main_text,
        pre_text,
        archived_ids=_archived_ids(root),
        ticket_id=ticket.id,
    )
    if spliced.is_err:
        _abort_merge(worktree)
        return Err(spliced.danger_err)

    # frob:ticket T-0959
    # T-0959: tickets-archive.md used to ride along on whatever git's raw
    # merge produced for it here, unguarded -- splice it the same way, with
    # root/main's copy (freshest, since only main ever archives) as the
    # authoritative side.
    archive_spliced = _splice_and_stage_archive(
        worktree, main_archive_text, pre_archive_text, base_text=base_archive_text
    )
    if archive_spliced.is_err:
        _abort_merge(worktree)
        return Err(archive_spliced.danger_err)
    return Ok(True)


# frob:ticket T-0479
def _auto_resolve_out_of_scope_conflicts(
    cwd: Path, ticket: Ticket, *, keep: str
) -> Result[frozenset[str], LandError]:
    """After a merge/squash leaves paths conflicted in `cwd`, auto-resolve
    every conflicted path OUTSIDE `ticket.scope` by `git checkout --<keep>`
    (`keep` is "ours" or "theirs", matching git's own vocabulary for the
    merge direction in play) and staging it, then return whatever is STILL
    conflicted (i.e. paths inside `ticket.scope`, plus any out-of-scope path
    the checkout itself failed on) for the caller to treat as a real
    conflict (T-0479).

    `ticket.scope` genuinely never authorized the worktree to change a file
    outside it -- a conflict there is definitionally noise from an
    unrelated concurrent main change, not an editorial decision belonging
    to this ticket, so taking `keep`'s side is always correct rather than a
    guess. `tickets.md` and `tickets-archive.md` are excluded unconditionally
    (T-0959 extended this exclusion to the archive file); both are always
    resolved via a ledger splice (`_splice_and_stage`/`_splice_and_stage_
    archive`), never via `git checkout`.

    T-1002: a registered union zone (`_UNION_ZONES`) is resolved via its own
    union-merge strategy FIRST, regardless of whether it is in or out of
    `ticket.scope` -- a zone file is very often IN scope for the ticket that
    is landing (e.g. a ticket editing `frob.toml`'s `[gates.severity]`
    block), so the ordinary in-scope-stays-conflicted rule below would never
    even get a chance to auto-resolve it otherwise."""
    conflicted = _conflicted_files(cwd) - {"tickets.md", "tickets-archive.md"}
    if not conflicted:
        return Ok(frozenset())
    zone_resolved = _resolve_union_zone_conflicts(
        cwd, {f for f in conflicted if _zone_for_path(f) is not None}
    )
    if zone_resolved.is_err:
        return zone_resolved
    non_zone = {f for f in conflicted if _zone_for_path(f) is None}
    conflicted = non_zone | zone_resolved.danger_ok
    if not conflicted:
        return Ok(frozenset())
    still_conflicted = {f for f in conflicted if scope_matches(f, ticket.scope)}
    for path in sorted(conflicted - still_conflicted):
        # T-1434: frob-coverage.lock.json is a coverage-ratchet artifact,
        # not an ordinary source file -- blindly keeping one side of a
        # real conflict here silently discards the other side's freshly
        # stamped data (confirmed root cause of the "reverted to an
        # older committed value" incident T-1270's agent observed). Try
        # the elementwise-max merge FIRST; only fall through to the
        # ordinary blind-checkout behavior if that merge itself declines
        # (a malformed side, a git failure) -- never worse than before
        # T-1434, only better when it succeeds.
        if path == _COVERAGE_LOCK_PATH and _merge_coverage_lock_conflict(cwd, path):
            _log.info(
                "land: %s auto-resolved out-of-scope conflict in %s via "
                "the T-1434 coverage-lock merge (not in scope %s)",
                ticket.id,
                path,
                list(ticket.scope),
            )
            continue
        resolved = _checkout_and_stage(cwd, keep, path)
        if resolved.is_err:
            _log.warning(
                "land: %s auto-resolve of out-of-scope conflict %s (keep=%s) "
                "failed -- leaving it conflicted for manual resolution",
                ticket.id,
                path,
                keep,
            )
            still_conflicted.add(path)
            continue
        _log.info(
            "land: %s auto-resolved out-of-scope conflict in %s by keeping "
            "%s's side (not in scope %s)",
            ticket.id,
            path,
            keep,
            list(ticket.scope),
        )
    return Ok(frozenset(still_conflicted))


def _checkout_and_stage(cwd: Path, keep: str, path: str) -> Result[None, LandError]:
    """`git checkout --<keep> -- <path> && git add <path>` in `cwd`."""
    checkout = run_argv(["git", "-C", str(cwd), "checkout", f"--{keep}", "--", path])
    if checkout.is_err or checkout.danger_ok.returncode != 0:
        return Err(LandError.GitFailed)
    add = run_argv(["git", "-C", str(cwd), "add", "--", path])
    if add.is_err or add.danger_ok.returncode != 0:
        return Err(LandError.GitFailed)
    return Ok(None)


def _check_only_tickets_conflicted(
    worktree: Path, ticket: Ticket, main_branch: str
) -> Result[None, LandError]:
    """`Err(MergeConflict)` (aborting the merge) if any IN-SCOPE file besides
    tickets.md/tickets-archive.md is still conflicted after
    `_merge_main_into_worktree`'s merge; any OUT-OF-SCOPE conflict is
    auto-resolved by taking main's side
    first (T-0479), since main is `theirs` in this merge direction (main
    merged into the worktree)."""
    resolved = _auto_resolve_out_of_scope_conflicts(worktree, ticket, keep="theirs")
    if resolved.is_err:
        _abort_merge(worktree)
        return Err(resolved.danger_err)
    remaining = resolved.danger_ok
    if remaining:
        _abort_merge(worktree)
        _log.error(
            "land: %s merging %s into %s conflicts in scoped file(s): %s -- "
            "resolve manually (cd %s && git merge %s), commit, then retry "
            "`frob ticket land %s --worktree %s`",
            ticket.id,
            main_branch,
            worktree,
            sorted(remaining),
            worktree,
            main_branch,
            ticket.id,
            worktree,
        )
        return Err(LandError.MergeConflict)
    return Ok(None)


def _unowned_deletions(
    root: Path, worktree: Path, scope: tuple[str, ...], main_branch: str
) -> Result[tuple[str, ...], LandError]:
    """Files main has that the worktree (post-merge) deletes, outside `scope`
    -- the stale-base guard: a worktree branched from an old main can end up
    silently deleting a feature main already landed, and this is the check
    that catches it before it reaches main (T-0176)."""
    diff = run_argv(
        [
            "git",
            "-C",
            str(worktree),
            "diff",
            main_branch,
            "--diff-filter=D",
            "--name-only",
        ]
    )
    if diff.is_err or diff.danger_ok.returncode != 0:
        return Err(LandError.GitFailed)
    deleted = [
        line.strip() for line in diff.danger_ok.stdout.splitlines() if line.strip()
    ]
    unowned = tuple(f for f in deleted if not _deletion_owned(f, scope))
    return Ok(unowned)


#: A single-physical-line `# frob:waive RULE ...` (or `//` for non-Python
#: sources) comment -- mirrors `frob.gates._fix_engine._WAIVE_SINGLE_LINE_
#: RE` exactly (same shape, independently defined here since importing
#: `frob.gates` from `frob.tickets` would cycle: `frob.gates` already
#: imports `frob.tickets.TicketQueue`).
_LAND_WAIVE_LINE_RE = re.compile(r"^\s*(#|//)\s*frob:waive\s+(\S+)\b")


def _waive_deletions_in_diff(
    worktree: Path, diff_args: Sequence[str]
) -> Result[tuple[tuple[str, str], ...], LandError]:
    """`(file, rule)` pairs for every `frob:waive` comment line a `git
    diff <diff_args> --no-color -U0` invocation in `worktree` reports as
    DELETED -- the shared diff-parsing core both `_uncommitted_waive_
    deletions` (T-1323, `diff_args=("HEAD",)`, the worktree's uncommitted
    edits) and `_committed_waive_deletions` (T-1326, `diff_args=
    (f"{merge_base}..HEAD",)`, the branch's already-committed history)
    build on -- the same laundering shape, single-line `frob:waive`
    deletion riding a merge unattributed, differs only in WHICH git rev
    range is being inspected, not in how a deletion is recognized inside
    it.

    Parses 0-context unified-diff hunks (deterministic header shape)
    rather than the porcelain-name-only forms `_unowned_deletions` uses --
    a `frob:waive` line disappearing from an otherwise-modified (not
    wholly deleted) file never shows up in a `--diff-filter=D --name-only`
    listing, only inside the hunk body.

    SCOPED OUT (T-1326 reviewer-flagged MINOR at T-1323's own approval,
    left unclosed here deliberately): `_LAND_WAIVE_LINE_RE` only matches a
    SINGLE physical `# frob:waive ...`/`// frob:waive ...` line, mirroring
    `frob.gates._fix_engine`'s own `_WAIVE_SINGLE_LINE_RE` scope exactly
    (see that module for the authoritative waiver-comment grammar). A
    multi-line/continuation waiver -- one whose `reason="..."` text wraps
    onto a following physical line via a trailing backslash or a block
    comment -- is invisible to this scan on EITHER side (uncommitted or
    committed): only the FIRST physical line matches `_LAND_WAIVE_LINE_RE`
    at all, so a deletion that removes just a continuation line (leaving
    the `frob:waive RULE` line itself intact) is not detected as a waiver
    deletion by this function, on top of and separate from `_deletion_
    owned`'s down-stream scope-ownership question. Closing this requires
    teaching the scan the SAME multi-line grammar `_fix_engine` parses
    (a real continuation-aware state machine, not a regex tweak) -- out of
    this ticket's scope (`_land.py`/`_land_merge.py`/`tests/
    test_ticket_land.py` only); tracked as a follow-up rather than
    silently left unnoted."""
    diff = run_argv(
        ["git", "-C", str(worktree), "diff", *diff_args, "--no-color", "-U0"]
    )
    if diff.is_err or diff.danger_ok.returncode not in (0, 1):
        return Err(LandError.GitFailed)
    deletions: list[tuple[str, str]] = []
    current_file: str | None = None
    for line in diff.danger_ok.stdout.splitlines():
        if line.startswith("--- a/"):
            current_file = line.removeprefix("--- a/")
        elif line.startswith("--- /dev/null"):
            current_file = None
        elif line.startswith("-") and not line.startswith("---"):
            if current_file is None:
                continue
            match = _LAND_WAIVE_LINE_RE.match(line[1:])
            if match is not None:
                deletions.append((current_file, match.group(2)))
    return Ok(tuple(deletions))


def _uncommitted_waive_deletions(
    worktree: Path,
) -> Result[tuple[tuple[str, str], ...], LandError]:
    """`(file, rule)` pairs for every `frob:waive` comment line the
    worktree's UNCOMMITTED changes (against `HEAD`, i.e. before any
    wip-commit) delete -- the T-1323 incident's own laundering path: a
    dirty worktree's edits get wip-snapshot-committed and ride the merge
    onto main, unattributed. Reading this straight off the working tree,
    BEFORE `_wip_commit` runs, is what makes the refusal below fire
    before the deletion is folded into a commit at all. Thin wrapper
    around `_waive_deletions_in_diff` with `diff_args=("HEAD",)`."""
    return _waive_deletions_in_diff(worktree, ("HEAD",))


def _committed_waive_deletions(
    worktree: Path, merge_base: str
) -> Result[tuple[tuple[str, str], ...], LandError]:
    """`(file, rule)` pairs for every `frob:waive` comment line the
    branch's own COMMITTED history (`merge_base..HEAD`) deletes -- the
    T-1326 extension of T-1323's guard: `_uncommitted_waive_deletions`
    only ever inspected the dirty worktree state at land time, so a
    `frob:waive` deletion an agent or tool COMMITTED mid-ticket (rather
    than leaving uncommitted) was invisible to it and rode the merge in
    unattributed -- the reviewer-flagged laundering vector T-1323's own
    approval left open. Thin wrapper around `_waive_deletions_in_diff`
    with `diff_args=(f"{merge_base}..HEAD",)`; a deletion that happened
    on `merge_base..HEAD` and was then RE-ADDED by a later commit in the
    same range does not appear here, since a two-endpoint diff (like a
    single uncommitted diff) only ever reports the NET change across the
    whole range, never per-intermediate-commit churn -- exactly mirroring
    how the uncommitted-state check already treats an add-then-remove
    inside a single dirty worktree."""
    return _waive_deletions_in_diff(worktree, (f"{merge_base}..HEAD",))


def _waive_deletion_declared_in_done_report(body: str, file: str, rule: str) -> bool:
    """Whether `body`'s `## Done report` section (`_done_report_section_
    lines`, the same section-boundary parser `_evidence.py`'s claim-
    replay already trusts) declares THIS `(file, rule)` pair TOGETHER, on
    one line -- the acceptance criterion's "declared by the Done report"
    half of the out-of-scope test.

    T-1323 review fix: the original shape (`file in body or rule in
    body`) searched the ENTIRE ticket body, not just the Done report, and
    accepted either name alone -- in an append-only ledger, a bare rule
    id like `PERF004` can appear incidentally in old Description/Plan
    prose (or a PRIOR Done report entry about an unrelated file) and
    silently satisfy an OR check with no real disclosure ever written.
    Restricting to the Done report section closes the append-only-ledger
    leak; requiring both names on the SAME line closes the OR-vs-AND gap
    -- a line has to actually name the file the deletion happened in
    alongside the rule it removed, not merely mention each somewhere."""
    section_lines = _done_report_section_lines(body)
    if section_lines is None:
        return False
    return any(file in line and rule in line for line in section_lines)


def _uncommitted_out_of_scope_waive_deletions(
    worktree: Path, ticket: Ticket
) -> Result[tuple[tuple[str, str], ...], LandError]:
    """`(file, rule)` pairs from `_uncommitted_waive_deletions` that are
    NEITHER covered by `ticket.scope` (`_deletion_owned`, the same D-12
    deletion-filter precedent `_unowned_deletions` already uses) NOR
    declared by `ticket.body`'s Done report
    (`_waive_deletion_declared_in_done_report`) -- what `_land_precheck`
    refuses on, before any merge, per the T-1323 incident guard."""
    found = _uncommitted_waive_deletions(worktree)
    if found.is_err:
        return Err(found.danger_err)
    out_of_scope = tuple(
        (file, rule)
        for file, rule in found.danger_ok
        if not _deletion_owned(file, ticket.scope)
        and not _waive_deletion_declared_in_done_report(ticket.body, file, rule)
    )
    return Ok(out_of_scope)


# frob:ticket T-1326
def _committed_out_of_scope_waive_deletions(
    worktree: Path, ticket: Ticket, merge_base: str
) -> Result[tuple[tuple[str, str], ...], LandError]:
    """`(file, rule)` pairs from `_committed_waive_deletions` that are
    NEITHER covered by `ticket.scope` (`_deletion_owned`, same D-12
    precedent) NOR declared by `ticket.body`'s Done report (`_waive_
    deletion_declared_in_done_report`) -- the committed-history mirror of
    `_uncommitted_out_of_scope_waive_deletions` (T-1323), extended (T-1326)
    to cover a `frob:waive` deletion the branch already COMMITTED before
    land ran, not only one still sitting uncommitted in the worktree.
    Identical ownership/declaration logic, applied against `merge_base..
    HEAD` instead of `HEAD` vs. the working tree -- a deletion on MAIN's
    side of `merge_base` (i.e. main deleted the waiver on its own branch,
    not this ticket's branch) never appears in this range at all, so a
    merge-base drift never counts against a landing ticket that did not
    touch it."""
    found = _committed_waive_deletions(worktree, merge_base)
    if found.is_err:
        return Err(found.danger_err)
    out_of_scope = tuple(
        (file, rule)
        for file, rule in found.danger_ok
        if not _deletion_owned(file, ticket.scope)
        and not _waive_deletion_declared_in_done_report(ticket.body, file, rule)
    )
    return Ok(out_of_scope)


# frob:ticket T-1003
# frob:tests tests/test_ticket_land.py::TestUvLockSync.test_worktree_side_lock_flap_auto_restored_before_wip_commit kind="integration"  # noqa: E501
def _wip_commit(
    worktree: Path, ticket_id: str, *, dry_run: bool
) -> Result[bool, LandError]:
    """Commit any uncommitted worktree changes as a WIP snapshot before
    landing -- the manual "wip-commit in the worktree" step folded into
    `land` so nothing an agent forgot to commit is silently dropped by the
    merge that follows.

    T-1003: `worktree`'s own `uv.lock` frob-version-only flap (T-0793's
    shape, from a prior `uv run`/`uv lock` invocation against a pyproject a
    sibling land already bumped on main) is auto-restored HERE, before the
    dirty check, exactly mirroring `_refuse_if_main_dirty`'s ROOT-side
    restore -- without this, the flap would otherwise get silently
    wip-committed as noise in the worktree and squash-applied into the
    landing commit, instead of the ritual `git checkout -- uv.lock` on
    BOTH sides land's own callers used to have to remember."""
    if _restore_lock_version_only_drift(worktree):
        _log.info(
            "land: %s auto-restored a uv.lock frob-version-only drift in "
            "%s before the wip-commit dirty check (T-1003)",
            ticket_id,
            worktree,
        )
    dirty = _porcelain_dirty(worktree)
    if dirty.is_err:
        return Err(dirty.danger_err)
    if not dirty.danger_ok:
        return Ok(False)
    if dry_run:
        _log.info(
            "land: %s would wip-commit uncommitted changes in %s", ticket_id, worktree
        )
        return Ok(True)
    return _do_wip_commit(worktree, ticket_id)


# frob:ticket T-1006
# frob:ticket T-1184
def _wip_add_excluding_frob(worktree: Path, ticket_id: str) -> Result[None, LandError]:
    """`_do_wip_commit`'s own `git add -A` excluding `.frob/`, split out to
    keep both under the ARCH001 line budget: A repo that has not
    gitignored `.frob/` (e.g. a bare test fixture, T-1006) would otherwise
    let frob's own bookkeeping writes made while computing the dirty check
    get swept into `add -A` as if they were real ticket content, defeating
    the CRLF-normalization-only no-op detection in `_do_wip_commit`.

    T-1184: the negated pathspec below (`"--", ".", ":!.frob"`)
    trips a hard refusal on git 2.34.1 the moment `.frob` IS actually
    gitignored (the normal real-repo case, reproduced against a clean
    checkout with no ticket diff at all: git treats a NEGATED pathspec
    that names an ignored path as if the path had been named directly, and
    aborts the ENTIRE add, not just skipping `.frob`). A bare test fixture
    with no `.gitignore` at all (T-1006's original case) never hits that
    refusal -- `.frob` isn't ignored there, so the pathspec exclusion
    behaves as ordinary path filtering. Try the exclusion pathspec first
    (preserves the exact original behavior/staging semantics for that
    fixture case); only on the specific ignored-path refusal, retry by
    staging everything and then unstaging `.frob` as a separate step,
    which reaches the same end state without ever naming an ignored path
    in a pathspec."""
    add_argv = ["git", "-C", str(worktree), "add", "-A", "--", ".", ":!.frob"]
    fallback_add_argv = ["git", "-C", str(worktree), "add", "-A", "--", "."]
    unstage_frob_argv = ["git", "-C", str(worktree), "reset", "-q", "--", ".frob"]
    add = run_argv(add_argv)
    if (
        add.is_ok
        and add.danger_ok.returncode != 0
        and _is_ignored_path_refusal(add.danger_ok.stderr)
    ):
        _log.warning(
            "land: %s wip add's :!.frob pathspec hit the ignored-path "
            "refusal (T-1184) -- falling back to add-then-unstage",
            ticket_id,
        )
        add = run_argv(fallback_add_argv)
        if add.is_ok and add.danger_ok.returncode == 0:
            unstage_frob = run_argv(unstage_frob_argv)
            if unstage_frob.is_err or unstage_frob.danger_ok.returncode != 0:
                _log.error(
                    "land: %s wip unstage .frob failed: %s",
                    ticket_id,
                    _describe_git_failure(unstage_frob_argv, unstage_frob),
                )
                return Err(LandError.GitFailed)
    if add.is_err or add.danger_ok.returncode != 0:
        _log.error(
            "land: %s wip add failed: %s",
            ticket_id,
            _describe_git_failure(add_argv, add),
        )
        return Err(LandError.GitFailed)
    return Ok(None)


# frob:ticket T-0847
# frob:tests tests/test_ticket_land.py::TestWipCommitNormalizationOnlyDirty.test_normalization_only_dirty_worktree_treated_as_no_op_not_git_failed  # noqa: E501
def _do_wip_commit(worktree: Path, ticket_id: str) -> Result[bool, LandError]:
    """`git add -A && git commit` a WIP snapshot in `worktree`, under
    `FROB_LAND_INTERNAL=1` (T-0828) so the T-0731 land-owned-files
    `pre-commit` hook does not refuse this land-internal commit if the
    worktree happens to carry an uncommitted land-owned-file edit.

    `_porcelain_dirty` can see a worktree as dirty purely from a line-ending
    normalization status line (WSL/autocrlf phantom-modified) -- `add -A`
    renormalizes to the identical blob, leaving nothing actually staged, and
    a plain `git commit` in that state exits 1 "nothing to commit" with no
    stderr, which used to bubble up as a spurious `GitFailed` (T-0847). After
    staging, re-check with `git diff --cached --quiet`: an empty stage means
    there was nothing real to snapshot, so we treat it as a no-op success
    instead of a land failure."""
    with _land_internal_git_env():
        added = _wip_add_excluding_frob(worktree, ticket_id)
        if added.is_err:
            return Err(added.danger_err)
        staged_argv = ["git", "-C", str(worktree), "diff", "--cached", "--quiet"]
        staged = run_argv(staged_argv)
        if staged.is_ok and staged.danger_ok.returncode == 0:
            _log.info(
                "land: %s wip add staged nothing real (normalization-only"
                " dirty status) -- treating as no-op, not GitFailed",
                ticket_id,
            )
            return Ok(False)
        commit_argv = [
            "git",
            "-C",
            str(worktree),
            "commit",
            "-m",
            f"wip: pre-land snapshot for {ticket_id}",
        ]
        commit = run_argv(commit_argv)
    if commit.is_err or commit.danger_ok.returncode != 0:
        _log.error(
            "land: %s wip commit failed: %s",
            ticket_id,
            _describe_git_failure(commit_argv, commit),
        )
        return Err(LandError.GitFailed)
    _log.info("land: %s wip-committed uncommitted worktree changes", ticket_id)
    return Ok(True)


# frob:ticket T-0761
def _rev_parse(worktree: Path, rev: str) -> Result[str, LandError]:
    """The full commit sha `rev` resolves to inside `worktree` (e.g. `HEAD`
    or a branch name) -- a thin `git rev-parse` wrapper shared by
    `_worktree_full_changeset`'s explicit merge-base computation (T-0761)."""
    result = run_argv(["git", "-C", str(worktree), "rev-parse", rev])
    if result.is_err or result.danger_ok.returncode != 0:
        _log.error("land: git rev-parse %s failed in %s", rev, worktree)
        return Err(LandError.GitFailed)
    return Ok(result.danger_ok.stdout.strip())


# frob:ticket T-0761
def _true_merge_base(worktree: Path, main_branch_name: str) -> Result[str, LandError]:
    """The commit sha `git merge-base main_branch_name HEAD` resolves to
    inside `worktree` -- the TRUE common ancestor `_worktree_full_changeset`
    diffs from, computed as its own explicit step (T-0761) rather than left
    implicit inside a triple-dot diff invocation. This is the root-cause fix
    for the T-0640 false-green: when `land()` was invoked with `worktree`
    pointing at the SAME checkout/branch `root` had checked out (no distinct
    feature branch was ever created), `main_branch_name` and `worktree`'s
    `HEAD` were literally the same ref, so a triple-dot diff against itself
    silently resolved to an empty changeset -- the T-0463 completeness
    assertion had nothing to check against and passed vacuously, while the
    squash-apply step degenerated to a no-op the exact same way (`git merge
    --squash` of a branch into itself is a no-op), leaving only the version
    bump and ledger splice to land. Computing the merge-base explicitly here
    lets `_worktree_full_changeset` detect and refuse that exact condition
    (merge-base == HEAD, i.e. zero commits unique to the worktree branch)
    instead of silently reporting nothing to check."""
    result = run_argv(
        ["git", "-C", str(worktree), "merge-base", main_branch_name, "HEAD"]
    )
    if result.is_err or result.danger_ok.returncode != 0:
        _log.error(
            "land: git merge-base %s HEAD failed in %s", main_branch_name, worktree
        )
        return Err(LandError.GitFailed)
    return Ok(result.danger_ok.stdout.strip())
