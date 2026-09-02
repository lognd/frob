"""Shared fixtures and test helpers for the tests/ticket_land_suite/
package (T-1201 split of tests/test_ticket_land.py): fixture-repo
plumbing (`repo`/`v2_repo`, `_git_init`/`_commit_all`), autouse git/frob
isolation fixtures, and the git-subprocess-failure-injection helper used
across the land-family test modules."""

from __future__ import annotations

import json
import os
import subprocess
import time
from collections.abc import Callable, Sequence
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from typani.result import Err, Ok, Result

import frob.tickets._land as _land_mod
import frob.tickets._land_compose as _land_compose_mod
import frob.tickets._land_finalize as _land_finalize_mod
import frob.tickets._land_git_ops as _land_git_ops_mod
import frob.tickets._land_release as _land_release_mod
import frob.tickets._land_squash as _land_squash_mod
from frob.gitio import GitError, ProcResult, run_argv
from frob.tickets import (
    Origin,
    TicketKind,
    TicketSpec,
    TicketState,
    transition,
)
from frob.tickets._models import Ticket
from frob.tickets._new_renumber import _ticket_from_spec
from frob.tickets._store import (
    _serialize_ticket,
    atomic_write,
    ledger_path,
    load_all,
    v2_ticket_path,
    write_ticket,
)


def _failing_run_argv(
    monkeypatch: pytest.MonkeyPatch,
    should_fail: Callable[[Sequence[str]], bool],
    *,
    hard_err: bool = False,
) -> None:
    """Patch `run_argv` (the single import point every helper calls
    through) so any invocation matching `should_fail` returns a git
    failure -- either a bad returncode (`hard_err=False`) or an
    `Err(GitError...)` result (`hard_err=True`) -- while everything else
    delegates to the real `run_argv`. This is how a real, hard-to-reproduce
    git subprocess failure (permission denial, disk full, a corrupted ref)
    gets exercised deterministically.

    T-1186 split `frob.tickets._land` into `_land`/`_land_merge`/
    `_land_finalize` (each importing its own top-level `run_argv` name);
    T-1334 further split `_land_finalize` into `_land_finalize`/
    `_land_squash`/`_land_release` (same pattern) -- so this patches all
    six -- a patch of `_land_mod.run_argv` alone no longer reaches call
    sites that moved into `_land_merge`/`_land_finalize`/`_land_squash`/
    `_land_release`. T-3144 (T-3121 fallout): `_land_compose` added to
    this list -- the disposable-stage flip (T-3121) moved the actual
    `git merge --squash --no-commit` AND the final `commit-tree` call
    into `_land_compose`'s own module-level `run_argv`, called directly
    from `_land.py`'s `compose_squash_in_disposable_worktree`, never
    passing through `_land_squash`'s copy at all -- a patch of the other
    five alone silently never fires for either of those two calls."""

    def _fake(argv: Sequence[str], **kwargs: Any) -> Any:
        if should_fail(argv):
            if hard_err:
                return Err(GitError.GitFailed)
            return Ok(
                ProcResult(
                    argv=tuple(argv),
                    returncode=1,
                    stdout="",
                    stderr="simulated failure",
                )
            )
        return run_argv(argv, **kwargs)

    monkeypatch.setattr(_land_mod, "run_argv", _fake)
    monkeypatch.setattr(_land_git_ops_mod, "run_argv", _fake)
    monkeypatch.setattr(_land_finalize_mod, "run_argv", _fake)
    monkeypatch.setattr(_land_squash_mod, "run_argv", _fake)
    monkeypatch.setattr(_land_compose_mod, "run_argv", _fake)
    monkeypatch.setattr(_land_release_mod, "run_argv", _fake)


def _run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        argv, cwd=str(cwd), check=True, capture_output=True, text=True
    )


def _git_init(root: Path, *, branch: str = "main") -> None:
    """Init a fixture repo AND gitignore `.frob/` from the very first
    commit (T-1258 chain-review fix, connects to T-1331):
    without this, every fixture's blanket `git add -A` helper
    (`_commit_all`) commits frob's own scratch state (per-ticket locks,
    the T-1257 v2 index/archive cache) as TRACKED files -- two branches
    that each write a DIFFERENT `.frob/tickets-index.json` (a real,
    reproduced add/add conflict: `TestArchiveV2::test_archive_v2_
    regression_two_sided_divergence_no_clobber`) then collide at merge,
    an artifact of an un-gitignored fixture, not of the product. Written
    into the working tree here so it lands in whichever commit each test
    makes first -- every worktree branched off that commit (or a later
    one) inherits the ignore rule automatically, same as a real repo's."""
    root.mkdir(parents=True, exist_ok=True)
    _run(["git", "init", "-q", "-b", branch], root)
    _run(["git", "config", "user.email", "test@example.com"], root)
    _run(["git", "config", "user.name", "Test"], root)
    (root / ".gitignore").write_text(".frob/\n")


def _commit_all(root: Path, message: str) -> None:
    _run(["git", "add", "-A"], root)
    _run(["git", "commit", "-q", "-m", message], root)


def _status_ignoring_frob(root: Path) -> str:
    """`git status --porcelain` output for `root`, with any `.frob/` entry
    (T-0577: `land()`'s own `.frob/land.lock` serialization lock, created
    lazily and left in place like every other `.frob/` scratch artifact --
    frob-local state a real repo is expected to `.gitignore`, never a
    genuine leftover a "leaves no trace" assertion should fail on)
    filtered out."""
    raw = _run(["git", "status", "--porcelain"], root).stdout.strip()
    lines = [line for line in raw.splitlines() if ".frob/" not in line]
    return "\n".join(lines)


def _spec(title: str, *, scope: tuple[str, ...] = ()) -> TicketSpec:
    return TicketSpec(
        title=title, kind=TicketKind.FEATURE, origin=Origin.AGENT, scope=scope
    )


def _make_closeable(root: Path, ticket_id: str) -> None:
    """Drive `ticket_id` to a state `transition(..., DONE)` will accept:
    planned -> in-progress, evidence + Done report attached."""
    assert transition(root, ticket_id, TicketState.PLANNED).is_ok
    assert transition(root, ticket_id, TicketState.IN_PROGRESS).is_ok
    loaded = load_all(root)
    ticket = loaded.danger_ok[ticket_id]
    ticket = ticket.model_copy(
        update={
            "evidence": ("tests/test_x.py::test_ok",),
            "body": ticket.body + "\n## Done report\n\nevidence attached\n",
        }
    )
    assert write_ticket(root, ticket).is_ok


# frob:ticket T-1258
def _seed_v2_ticket(
    root: Path, ticket_id: str, *, scope: tuple[str, ...] = ()
) -> Ticket:
    """Write a fresh QUEUED ticket directly into v2-mode storage
    (`tickets/<ticket_id>/ticket.md`) -- flips `_store_mode(root)`
    detection to 'v2' for every subsequent ticket op against `root`.
    Fixture-only seeding for T-1258's land tests; the real v1->v2
    migrator is T-1259 (reserved, not built here)."""
    ticket = _ticket_from_spec(ticket_id, _spec("Seed", scope=scope), ())
    path = v2_ticket_path(root, ticket_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    assert atomic_write(path, _serialize_ticket(ticket)).is_ok
    return ticket


@pytest.fixture
def v2_repo(tmp_path: Path) -> Path:
    """A main checkout in v2-mode storage (`tickets/T-####/ticket.md`,
    ledger-v2 design section 1) -- the v2-mode analog of the `repo`
    fixture above, seeded with one ticket (T-3000) and one committed
    source file so `_store_mode` reads 'v2' from the very first commit."""
    main_repo = tmp_path / "v2main"
    _git_init(main_repo)  # gitignores .frob/ already (see _git_init's docstring)
    _seed_v2_ticket(main_repo, "T-3000", scope=("src/seed.py",))
    (main_repo / "src").mkdir()
    (main_repo / "src" / "feature.py").write_text("# landed feature\n")
    _commit_all(main_repo, "init v2")
    return main_repo


# frob:ticket T-1393
# frob:ticket T-1534
# T-1534: this frob:waive WIRE001 was removed here -- T-1510 (landed after the
# waiver was written) added the autouse-pytest-fixture exemption to
# frob.gates._dead_symbols._new_callable_records via _is_autouse_pytest_fixture,
# so WIRE001 no longer flags this symbol at all; verified directly against a
# fresh graph snapshot.
@pytest.fixture(autouse=True)
def _isolate_from_host_git_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """T-1393: every fixture repo in this module sets its own LOCAL
    `user.name`/`user.email`, but a bare `git` subprocess spawned from
    here (this module's own `_run` helper, or production `land()` via
    `gitio.run_argv`, which inherits `os.environ` -- neither passes an
    explicit `env=`) still falls through to the HOST machine's real
    `--global`/`--system` git config for anything neither fixture nor
    production code sets explicitly. That real config is genuinely
    shared, mutable, contended state across every `pytest-xdist` worker
    process on this machine (unlike `tmp_path`, which xdist already
    gives each worker its own tree under) -- diagnosed for T-1393's
    `test_disjoint_v2_tickets_land_with_no_custom_merge` flake, which
    reproduced only embedded in a full, `-n 4` unscoped suite run, never
    standalone or as this file alone: a config value the host happens to
    carry (e.g. `credential.helper`, `core.autocrlf`, a `commit.gpgsign`
    or `core.hooksPath` override) can slow or alter one worker's git
    spawns unpredictably under real parallel load in a way no single-file
    rerun can trigger. `GIT_CONFIG_GLOBAL`/`GIT_CONFIG_SYSTEM` pointed at
    `os.devnull` (git >=2.32) make every git spawn in this test session
    see an empty global/system config regardless of what is actually
    installed on the host, closing that gap for every test in this
    module, not just the one that flaked."""
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_SYSTEM", os.devnull)


# frob:ticket T-1553
@pytest.fixture(autouse=True)
def _pin_v1_mode_on_bare_tmp_path(
    request: pytest.FixtureRequest, tmp_path: Path
) -> None:
    """T-1553: the fresh-repo default flipped to v2 -- pin `tmp_path`
    itself to v1/'single' mode for the classes named in
    `_V1_PINNED_CLASSES` below, all of which exercise
    `splice_ledger`/monofile-specific land-regression logic directly via
    a bare `tmp_path` (never through this file's own `repo`/`v2_repo`
    fixtures, which seed a SUBDIRECTORY of `tmp_path` explicitly and are
    unaffected either way). Scoped to just those classes -- not every
    class in this module uses `tmp_path` as a v1 ledger root; some (e.g.
    `TestCloseSkipMutationEvidenceBypass`) deliberately seed a legacy
    dir-mode fixture directly under `tmp_path` and must NOT get a
    pre-existing `tickets.md` in their way."""
    cls = request.cls
    if cls is not None and cls.__name__ in _V1_PINNED_CLASSES:
        atomic_write(ledger_path(tmp_path), "# Tickets\n\n")


# frob:ticket T-1721
_V1_PINNED_CLASSES = frozenset(
    {
        "TestSpliceLedger",
        "TestSpliceOnlyTicket",
        "TestCarryForwardOrRefuseSiblingEdits",
        "TestSiblingDoneReportPreserved",
        "TestSpliceLedgerRicherStatePreference",
        "TestSpliceLedgerPrefersEvidenceRichSideOnRankTie",
        "TestSpliceLedgerIdDropGuard",
        "TestTick005LandRegressions",
    }
)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A main checkout with an initialized ledger and one committed file."""
    main_repo = tmp_path / "main"
    _git_init(main_repo)
    atomic_write(ledger_path(main_repo), "# Tickets\n\n")
    (main_repo / "src").mkdir()
    (main_repo / "src" / "feature.py").write_text("# landed feature\n")
    _commit_all(main_repo, "init")
    return main_repo


def _t2114_concurrent_new_ticket(repo: Path, result_path: Path) -> None:
    """Multiprocessing target (module-level so the `spawn` context, T-3174,
    can pickle/import it -- mirrors `_t0907_child_land`'s own pattern
    below): calls `new_ticket`
    against `repo` from a genuinely SEPARATE process, not an in-process
    monkeypatch hook. This is the fix for a self-referential deadlock a
    prior version of this test had: calling `new_ticket` synchronously
    IN-PROCESS from inside a hook `land()` itself invokes meant the
    concurrent write's own `refuse_if_land_in_progress` wait could never
    observe the outer land as finished, because the outer land was
    blocked waiting for that very call to return (T-2114 traced this and
    confirmed no PRODUCTION code path ever does this -- only this test's
    old construction did). A genuinely separate process has no such
    problem: it waits on `repo`'s real land lock exactly the way a real
    concurrent writer would, and proceeds once `land()` actually finishes
    and releases it -- which is the real-world shape T-1036 exercises.

    T-3144: this child inherits a snapshot of the PARENT test process's
    `os.environ` taken at spawn time (still true under `spawn`, T-3174 --
    a fresh interpreter still inherits the launching process's env
    unless explicitly cleared) -- and by then `land()`'s own in-process
    evidence re-verify (`apply_agent_env`, T-3094, a real, deliberate,
    no-restore mutation correct for its actual production callers,
    short-lived CLI processes) has already set `FROB_WORKTREE` to
    `worktree` for the rest of the parent process's lifetime. A
    genuinely independent concurrent writer -- a real `frob ticket new`
    invocation in its own shell, the scenario this test simulates --
    would never inherit that: it gets a fresh env from ITS OWN shell,
    not the land-running process's runtime-mutated one. Popping both
    keys here (mirroring `tests/conftest.py`'s own
    `_isolate_worktree_lease_env_before_test`, T-3123/T-3145) keeps this
    simulation honest to the real-world case instead of failing on an
    artifact of sharing state with `land()`."""
    import os

    from frob.tickets import new_ticket as _new_ticket_fn

    os.environ.pop("FROB_WORKTREE", None)
    os.environ.pop("FROB_AGENT", None)
    result = _new_ticket_fn(repo, _spec("Concurrent sibling"))
    if result.is_ok:
        result_path.write_text(json.dumps({"ok": True, "id": result.danger_ok.id}))
    else:
        result_path.write_text(
            json.dumps({"ok": False, "error": str(result.danger_err)})
        )


# T-0828: the T-0731 `pre-commit` hook shape (`_FORBID_LAND_OWNED_FILES_
# SCRIPT` in `frob.scaffold.project`) refuses any commit that stages
# CHANGELOG.md unless `FROB_LAND_INTERNAL` is set in the child's env.
# Copied here (not imported) so the regression test exercises the same
# guard SHAPE a real scaffolded repo would install, without coupling this
# test to `frob.scaffold.project`'s internals -- scope is `_land.py`/this
# test file only.
_CHANGELOG_GUARD_HOOK = """#!/bin/sh
if [ -z "$FROB_LAND_INTERNAL" ]; then
    staged=$(git diff --cached --name-only)
    case "$staged" in
        *CHANGELOG.md*)
            echo "frob: refusing commit -- CHANGELOG.md is land-owned (T-0731)" >&2
            exit 1
            ;;
    esac
fi
exit 0
"""


def _install_changelog_guard_hook(repo: Path) -> None:
    """Install the T-0731-shaped `pre-commit` hook (real hooks dir, shared
    across every linked worktree of `repo`) that refuses a commit staging
    CHANGELOG.md unless `FROB_LAND_INTERNAL` is set -- the regression
    fixture for T-0828."""
    hooks_dir = Path(
        _run(["git", "rev-parse", "--git-common-dir"], repo).stdout.strip()
    )
    if not hooks_dir.is_absolute():
        hooks_dir = repo / hooks_dir
    hooks_dir = hooks_dir / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    hook_path = hooks_dir / "pre-commit"
    hook_path.write_text(_CHANGELOG_GUARD_HOOK)
    hook_path.chmod(0o755)


def _t0907_child_land(
    root: Path, ticket_id: str, worktree: Path, ready_path: Path
) -> None:
    """Multiprocessing target (module-level so `fork` can spawn it, T-0907):
    monkeypatches `frob.tickets._land_compose.run_argv` (this CHILD
    process's own copy of the module, `fork` gives every child an
    independent copy-on-write memory image) so that once `land()`'s
    squash-apply merge onto the disposable stage actually runs, it
    signals readiness (`ready_path`) and then sleeps well past however
    long the parent needs to `SIGKILL` this process -- reproducing
    "killed mid-staging" deterministically instead of relying on timing
    luck against a real 580s coordinator timeout.

    T-3144 (T-3121 fallout): T-1334's own comment here ("the squash-merge
    runs inside `_land_squash._squash_and_splice_ledger`") went stale
    when T-3121's disposable-stage flip moved the actual `git merge
    --squash --no-commit` into `_land_compose.compose_squash_in_
    disposable_worktree` -- called directly from `_land.py`, never
    through `_land_squash`'s own copy of `run_argv` at all. Patching the
    wrong module meant this hook never fired post T-3121: `ready_path`
    was never written, so the parent's own 20s wait for it timed out and
    failed on `assert ready_path.exists()` before ever reaching the
    intended SIGKILL. `land_mod.land` (the entry point actually invoked)
    still lives in `_land.py`."""

    import frob.tickets._land as land_mod
    import frob.tickets._land_compose as land_compose_mod

    real_run_argv = land_compose_mod.run_argv

    def _patched(
        argv: Sequence[str], *, cwd: Path | None = None, timeout_s: int | float = 30.0
    ) -> Result[ProcResult, GitError]:
        result = real_run_argv(argv, cwd=cwd, timeout_s=timeout_s)
        if "merge" in argv and "--squash" in argv:
            ready_path.write_text("ready\n")
            time.sleep(30)
        return result

    setattr(land_compose_mod, "run_argv", _patched)  # noqa: B010
    land_mod.land(root, ticket_id, worktree, dry_run=False)


# frob:ticket T-2679
def _t2679_child_land(
    root: Path, ticket_id: str, worktree: Path, ready_path: Path
) -> None:
    """`_t0907_child_land`'s own T-2679 twin: pauses one step EARLIER --
    right before `_land_finalize_and_close`'s terminal-state commit
    (`_commit_finalize_writes`'s `git commit -m "finalize and close ..."`)
    ever runs -- instead of after the squash-apply merge. This is the
    exact window `_write_finalize_repair_marker` brackets: the worktree's
    ticket.md has already been rewritten to `state: done` on disk
    (`transition(..., DONE)`, called just before this commit) but that
    write is NOT YET committed anywhere, and `root` has not been touched
    at all -- squash-apply never even starts."""

    import frob.tickets._land as land_mod
    import frob.tickets._land_finalize as land_finalize_mod

    real_run_argv = land_finalize_mod.run_argv

    def _patched(
        argv: Sequence[str], *, cwd: Path | None = None, timeout_s: int | float = 30.0
    ) -> Result[ProcResult, GitError]:
        if "commit" in argv and any("finalize and close" in str(a) for a in argv):
            ready_path.write_text("ready\n")
            time.sleep(30)
        return real_run_argv(argv, cwd=cwd, timeout_s=timeout_s)

    setattr(land_finalize_mod, "run_argv", _patched)  # noqa: B010
    land_mod.land(root, ticket_id, worktree, dry_run=False)


# frob:ticket T-2679
def _t2679b_child_land(
    root: Path, ticket_id: str, worktree: Path, ready_path: Path
) -> None:
    """A third sibling of `_t0907_child_land`, later still: pauses inside
    `land()`'s own `pre_commit_sweep` hook (T-1514) -- the post-squash,
    pre-commit RE-VERIFICATION phase the coordinator's live T-2696
    reproduction was actually killed during. By the time this callable
    runs, `root`'s index already holds the complete staged squash-apply
    (T-1514's own contract) -- this reproduces "killed mid-reverification"
    at the exact point a real `frob check`-shaped `pre_commit_sweep` spawn
    can run long enough to exceed a wrapper's timeout on its own."""

    import frob.tickets._land as land_mod

    def _pausing_sweep(sweep_root: Path, final_id: str) -> bool | None:
        ready_path.write_text("ready\n")
        time.sleep(30)
        return True

    land_mod.land(
        root, ticket_id, worktree, dry_run=False, pre_commit_sweep=_pausing_sweep
    )


# frob:ticket T-0757
_RANKS = (0, 1, 2, 2, 3, 3)  # queued, planned, in-progress, blocked, dropped, done
_STATE_BY_RANK: dict[int, tuple[TicketState, ...]] = {
    0: (TicketState.QUEUED,),
    1: (TicketState.PLANNED,),
    2: (TicketState.IN_PROGRESS, TicketState.BLOCKED),
    3: (TicketState.DROPPED, TicketState.DONE),
}


def _synthetic_ticket(
    tid: str, state: TicketState, *, has_report: bool, evidence_count: int
) -> "_land_mod.Ticket":
    """A minimal, directly-constructed `Ticket` (no filesystem/git
    round-trip) carrying exactly the richness signal `_richness`
    (`frob.tickets._land`) reads: Done-report presence and evidence count
    -- `TestNewerWinnerQualifiedPreferenceProperty` needs many synthetic
    combinations, cheap to build, not the full `new_ticket`/`transition`
    lifecycle `TestSpliceLedgerRicherStatePreference` above already covers
    with hand-picked real-repo cases."""
    body = "## Done report\n\nChanged: x\nEvidence: y\n" if has_report else ""
    return _land_mod.Ticket(
        id=tid,
        title="synthetic",
        state=state,
        kind=TicketKind.FEATURE,
        origin=Origin.HUMAN,
        created=date(2026, 1, 1),
        evidence=tuple(f"e{i}" for i in range(evidence_count)),
        body=body,
    )


# frob:ticket T-1269
# frob:waive WIRE001 reason="test-only fixture helper used by TestLandPlan's own five \
# test methods below, in this same file -- no production caller to wire it to by \
# design" permanent="true"
def _make_design_worktree(
    main_repo: Path, tmp_path: Path, *, branch: str = "design"
) -> Path:
    """A worktree branched off `main_repo` carrying only docs/ledger
    changes and a fresh draft ticket -- the T-1269 "design-phase, no
    closeable worked ticket" shape `land_plan` targets. Real `git
    worktree add`, matching this file's own established fixture idiom."""
    worktree = tmp_path / "design-wt"
    _run(["git", "worktree", "add", str(worktree), "-b", branch, "main"], main_repo)
    return worktree
