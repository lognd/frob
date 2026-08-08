"""T-0176: `frob ticket land` -- one-command landing.

Fixture-repo tests reproducing the real incident classes the ticket body
names: a stale-base worktree silently deleting a feature main already
landed, a `tickets.md` both-sides-append textual conflict, and provisional
(draft) id finalization at land time. Uses real git subprocesses (matching
tests/test_tickets_collision.py's style) -- not mocks -- because the whole
point of `land` is real merge/conflict/deletion behavior.
"""

from __future__ import annotations

import json
import multiprocessing
import os
import re
import signal
import subprocess
import time
from collections.abc import Callable, Sequence
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st
from typani.result import Err, Ok, Result

import frob.tickets._land as _land_mod
import frob.tickets._land_finalize as _land_finalize_mod
import frob.tickets._land_git_ops as _land_git_ops_mod
import frob.tickets._land_ledger_merge as _land_ledger_merge_mod
import frob.tickets._land_merge_zones as _land_merge_zones_mod
import frob.tickets._land_release as _land_release_mod
import frob.tickets._land_squash as _land_squash_mod
from frob.gates import PreworkSweep, load_prework, record_prework, scope_digest
from frob.gitio import GitError, ProcResult, run_argv
from frob.graph import build_graph
from frob.tickets import (
    Origin,
    TicketKind,
    TicketSpec,
    TicketState,
    new_ticket,
    set_done_report,
    transition,
)
from frob.tickets._land import land, splice_ledger
from frob.tickets._land_git_ops import _splice_and_stage_archive
from frob.tickets._models import (
    AcceptanceCriterion,
    DoneReportClaims,
    LandError,
    Ticket,
    render_claims_block,
)
from frob.tickets._new_renumber import _ticket_from_spec
from frob.tickets._store import (
    _serialize_ticket,
    archive_path,
    atomic_write,
    ledger_path,
    load_all,
    load_archive,
    v2_ticket_path,
    write_archive,
    write_ticket,
)
from tests._write_unchecked import _write_ticket_unchecked  # noqa: E402


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
    five -- a patch of `_land_mod.run_argv` alone no longer reaches call
    sites that moved into `_land_merge`/`_land_finalize`/`_land_squash`/
    `_land_release`."""

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


# frob:ticket T-1258
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


# frob:ticket T-1331
class TestFrobDirNeverLeaksIntoGitAdd:
    """T-1331: `.frob/` scratch state (per-ticket locks, the T-1257 v2
    index/archive cache files) must never become a TRACKED file via any
    fixture's blanket `git add -A` (`_commit_all`) -- an un-gitignored
    fixture repo previously let two branches each commit a DIFFERENT
    `.frob/tickets-index.json` as a real tracked file, colliding as a raw
    git add/add conflict at merge (`TestArchiveV2::
    test_archive_v2_regression_two_sided_divergence_no_clobber`) or
    tripping land's T-0463 completeness assertion (`LandError.
    IncompleteLand`) once the squash-apply's target checkout came up
    missing files the source checkout had committed. `_git_init` (T-1258)
    fixed this by writing a `.gitignore` with `.frob/` into every fixture
    repo from its very first commit; this locks that in as a regression
    test tied to T-1331 specifically, independent of `_git_init`'s own
    docstring."""

    # frob:ticket T-1331
    # frob:tests tests/test_ticket_land.py::TestFrobDirNeverLeaksIntoGitAdd.test_frob_scratch_files_are_gitignored_not_tracked kind="unit"  # noqa: E501
    def test_frob_scratch_files_are_gitignored_not_tracked(
        self, tmp_path: Path
    ) -> None:
        main_repo = tmp_path / "main"
        _git_init(main_repo)
        atomic_write(ledger_path(main_repo), "# Tickets\n\n")

        # Simulate real frob scratch state a ticket operation would leave
        # behind before any commit happens (T-1257's v2 index/archive
        # cache files, a per-ticket lock file).
        frob_dir = main_repo / ".frob"
        frob_dir.mkdir()
        (frob_dir / "tickets-index.json").write_text("{}")
        (frob_dir / "tickets-archive-cache.json").write_text("{}")
        (frob_dir / "some.lock").write_text("")

        _commit_all(main_repo, "init")

        tracked = _run(["git", "ls-files"], main_repo).stdout.splitlines()
        assert not any(path.startswith(".frob/") for path in tracked), tracked

        status = _run(["git", "status", "--porcelain"], main_repo).stdout
        assert ".frob/" not in status

    # frob:ticket T-1331
    # frob:tests tests/test_ticket_land.py::TestFrobDirNeverLeaksIntoGitAdd.test_two_branches_with_divergent_frob_scratch_never_add_add_conflict  # noqa: E501
    def test_two_branches_with_divergent_frob_scratch_never_add_add_conflict(
        self, tmp_path: Path
    ) -> None:
        """The exact T-1331 incident shape: two independent checkouts each
        write a DIFFERENT `.frob/tickets-index.json` before committing --
        gitignoring `.frob/` means neither ever tracks the file, so
        merging one into the other can never hit a real git add/add
        conflict over it."""
        main_repo = tmp_path / "main"
        _git_init(main_repo)
        atomic_write(ledger_path(main_repo), "# Tickets\n\n")
        _commit_all(main_repo, "init")

        clone = tmp_path / "clone"
        _run(["git", "clone", "-q", str(main_repo), str(clone)], tmp_path)
        _run(["git", "config", "user.email", "test@example.com"], clone)
        _run(["git", "config", "user.name", "Test"], clone)

        (main_repo / ".frob").mkdir()
        (main_repo / ".frob" / "tickets-index.json").write_text('{"side": "main"}')
        (main_repo / "src_a.py").write_text("# a\n")
        _commit_all(main_repo, "main side")

        (clone / ".frob").mkdir()
        (clone / ".frob" / "tickets-index.json").write_text('{"side": "clone"}')
        (clone / "src_b.py").write_text("# b\n")
        _commit_all(clone, "clone side")

        _run(["git", "fetch", "-q", str(main_repo), "main"], clone)
        merge = subprocess.run(
            ["git", "merge", "-q", "FETCH_HEAD", "-m", "merge"],
            cwd=str(clone),
            capture_output=True,
            text=True,
        )
        assert merge.returncode == 0, merge.stdout + merge.stderr
        assert "add/add" not in (merge.stdout + merge.stderr)


# frob:ticket T-1194
class TestSpliceLedger:
    """`splice_ledger` -- the id-level merge tickets.md conflicts always go
    through, never git's line-level textual algorithm."""

    def test_disjoint_ids_both_kept(self, tmp_path: Path) -> None:
        ours = new_ticket(tmp_path, _spec("Ours"))
        assert ours.is_ok
        ours_text = ledger_path(tmp_path).read_text()

        # A second, DISJOINT id on "their" side -- write it directly rather
        # than via new_ticket (two non-git tmp dirs would both allocate
        # T-0001, which is not the scenario under test: two SIDES of an
        # already-diverged ledger, one entry each).
        theirs_path = tmp_path / "theirs"
        theirs_path.mkdir()
        theirs_ticket = ours.danger_ok.model_copy(
            update={"id": "T-0002", "title": "Theirs"}
        )
        atomic_write(ledger_path(theirs_path), "# Tickets\n\n")
        assert write_ticket(theirs_path, theirs_ticket).is_ok
        theirs_text = ledger_path(theirs_path).read_text()

        spliced = splice_ledger(ours_text, theirs_text)
        assert spliced.is_ok
        assert "Ours" in spliced.danger_ok
        assert "Theirs" in spliced.danger_ok

    # frob:ticket T-1194
    def test_same_id_newer_state_wins(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_land_ledger_merge.py::splice_ledger kind="unit"
        created = new_ticket(tmp_path, _spec("Shared"))
        assert created.is_ok
        tid = created.danger_ok.id
        ours_text = ledger_path(tmp_path).read_text()

        assert transition(tmp_path, tid, TicketState.PLANNED).is_ok
        theirs_text = ledger_path(tmp_path).read_text()

        spliced = splice_ledger(ours_text, theirs_text)
        assert spliced.is_ok
        assert "state: planned" in spliced.danger_ok
        assert "state: queued" not in spliced.danger_ok

    # frob:tests src/frob/tickets/_land_ledger_merge.py::splice_ledger kind="unit"
    def test_malformed_ours_propagates_as_err(self, tmp_path: Path) -> None:
        """A malformed `ours_text` (a ticket marker with no ```yaml
        frontmatter) must surface `_parse_ledger`'s error unchanged --
        `splice_ledger` never silently drops the ours side."""
        malformed_ours = "# Tickets\n\n<!-- ticket:T-0001 -->\nno frontmatter here\n"

        valid = new_ticket(tmp_path, _spec("Theirs"))
        assert valid.is_ok
        theirs_text = ledger_path(tmp_path).read_text()

        spliced = splice_ledger(malformed_ours, theirs_text)
        assert spliced.is_err

    # frob:tests src/frob/tickets/_land_ledger_merge.py::splice_ledger kind="unit"
    def test_malformed_theirs_propagates_as_err(self, tmp_path: Path) -> None:
        """A malformed `theirs_text` must ALSO surface as `Err` -- the
        second `_parse_ledger` call's error path is exercised
        independently of the first (both sides are fallible)."""
        valid = new_ticket(tmp_path, _spec("Ours"))
        assert valid.is_ok
        ours_text = ledger_path(tmp_path).read_text()

        malformed_theirs = "# Tickets\n\n<!-- ticket:T-0002 -->\nno frontmatter here\n"

        spliced = splice_ledger(ours_text, malformed_theirs)
        assert spliced.is_err


# frob:ticket T-1194
class TestSpliceOnlyTicket:
    """`_splice_only_ticket` (T-0479) -- the ledger splice scoped to ONE
    ticket id, the fix for the T-0475 sibling-resurrection incident."""

    # frob:tests src/frob/tickets/_land_ledger_merge.py::_splice_only_ticket kind="unit"
    def test_sibling_state_never_taken_from_worktree(self, tmp_path: Path) -> None:
        """Main has T-A queued (already requeued back from in-progress) and
        T-B queued. The worktree's stale copy still remembers T-A as
        in-progress. Landing T-B must not resurrect T-A's stale
        in-progress state -- only T-B's own block may come from the
        worktree."""
        created_a = new_ticket(tmp_path, _spec("Sibling A"))
        assert created_a.is_ok
        tid_a = created_a.danger_ok.id
        created_b = new_ticket(tmp_path, _spec("Sibling B"))
        assert created_b.is_ok
        tid_b = created_b.danger_ok.id

        # Worktree's stale snapshot: T-A in-progress.
        assert transition(tmp_path, tid_a, TicketState.PLANNED).is_ok
        assert transition(tmp_path, tid_a, TicketState.IN_PROGRESS).is_ok
        worktree_text = ledger_path(tmp_path).read_text()

        # Main has since requeued T-A back to queued, and separately
        # progressed T-B to planned.
        assert transition(tmp_path, tid_a, TicketState.QUEUED).is_ok
        assert transition(tmp_path, tid_b, TicketState.PLANNED).is_ok
        main_text = ledger_path(tmp_path).read_text()

        spliced = _land_git_ops_mod._splice_only_ticket(main_text, worktree_text, tid_b)
        assert spliced.is_ok
        from frob.tickets._store import _parse_ledger

        parsed = _parse_ledger(spliced.danger_ok)
        assert parsed.is_ok
        merged = parsed.danger_ok
        assert merged[tid_a].state == TicketState.QUEUED  # sibling untouched
        assert merged[tid_b].state == TicketState.PLANNED  # landed ticket's own block

    # frob:tests src/frob/tickets/_land_ledger_merge.py::_splice_only_ticket kind="unit"
    def test_landed_tickets_own_divergence_still_resolved(self, tmp_path: Path) -> None:
        """If the SAME ticket id genuinely diverges between main and the
        worktree, `_newer` still resolves it (via the scoped splice) --
        only sibling ids are excluded from consideration."""
        created = new_ticket(tmp_path, _spec("Landing"))
        assert created.is_ok
        tid = created.danger_ok.id
        main_text = ledger_path(tmp_path).read_text()

        assert transition(tmp_path, tid, TicketState.PLANNED).is_ok
        worktree_text = ledger_path(tmp_path).read_text()

        spliced = _land_git_ops_mod._splice_only_ticket(main_text, worktree_text, tid)
        assert spliced.is_ok
        assert "state: planned" in spliced.danger_ok

    # frob:ticket T-0740
    # frob:ticket T-1194
    # frob:tests tests/test_ticket_land.py::TestSpliceOnlyTicket.test_render_that_would_drop_an_id_is_refused  # noqa: E501
    def test_render_that_would_drop_an_id_is_refused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-0740: `_splice_only_ticket` (the T-0479 per-ticket `frob ticket
        land` path) was the one wholesale-ledger-commit site missing the
        T-0764 `_check_ledger_id_integrity` backstop that `splice_ledger`
        and `write_all`/`write_archive` all already ran. Pin the fix the
        same way `TestSpliceLedgerIdDropGuard` pins `splice_ledger`: patch
        the render step to simulate a future rendering regression that
        drops every section, and assert the scoped splice refuses rather
        than silently committing the truncated text."""
        created = new_ticket(tmp_path, _spec("A ticket"))
        assert created.is_ok
        tid = created.danger_ok.id
        main_text = ledger_path(tmp_path).read_text()

        assert transition(tmp_path, tid, TicketState.PLANNED).is_ok
        worktree_text = ledger_path(tmp_path).read_text()

        def _dropping_render(tickets: dict) -> str:
            # Simulate a render bug: silently omit every ticket's section.
            return "# Tickets\n\nCentral ledger managed by `frob ticket`.\n"

        monkeypatch.setattr(_land_ledger_merge_mod, "_render_ledger", _dropping_render)
        spliced = _land_git_ops_mod._splice_only_ticket(main_text, worktree_text, tid)
        assert spliced.is_err
        assert spliced.danger_err.name == "LedgerIntegrityViolation"

    # frob:tests src/frob/tickets/_land_ledger_merge.py::splice_ledger kind="unit"
    def test_whole_ledger_splice_never_regresses_a_sibling_from_done(
        self, tmp_path: Path
    ) -> None:
        """T-0537: `splice_ledger` (the whole-ledger merge used by `frob
        ticket merge-driver`) must never let a stale non-terminal copy of
        an already-DONE ticket win, regardless of which side
        (`ours`/`theirs`) carries it -- `_newer`'s state-rank tiebreak
        (terminal ranks highest) already makes this structurally
        impossible whenever a divergence goes THROUGH the splice; this is
        the regression-lock proving it, the exact incident class a
        hand-resolved `tickets.md` conflict (bypassing the splice
        entirely) produced instead (7 closed tickets resurrected to
        queued)."""
        created = new_ticket(tmp_path, _spec("Closed elsewhere"))
        assert created.is_ok
        tid = created.danger_ok.id
        loaded = load_all(tmp_path).danger_ok[tid]
        done_ticket = loaded.model_copy(update={"state": TicketState.DONE})
        assert write_ticket(tmp_path, done_ticket).is_ok
        ours_text = ledger_path(tmp_path).read_text()

        # theirs (a stale branch) still remembers it as queued.
        stale = done_ticket.model_copy(update={"state": TicketState.QUEUED})
        assert write_ticket(tmp_path, stale).is_ok
        theirs_text = ledger_path(tmp_path).read_text()

        spliced = splice_ledger(ours_text, theirs_text)
        assert spliced.is_ok
        from frob.tickets._store import _parse_ledger

        parsed = _parse_ledger(spliced.danger_ok)
        assert parsed.is_ok
        assert parsed.danger_ok[tid].state == TicketState.DONE


# frob:ticket T-1721
class TestCarryForwardOrRefuseSiblingEdits:
    """`_carry_forward_or_refuse_sibling_edits` / `_splice_only_ticket`'s
    `base_text` parameter (T-1721): the fix for the T-1637 field incident
    -- a legitimate sibling-ticket ledger edit made in the same worktree
    while landing a DIFFERENT ticket, silently and permanently dropped by
    T-0479's blanket main-wins sibling default, three separate times,
    before the pattern was diagnosed as structural rather than a one-off.

    All four tests share the same shape: two sibling tickets A (landing)
    and B (edited or not, on one or both sides); `base_text` is B's ledger
    state at the fork point, `main_text` is root's current state, and
    `worktree_text` is the worktree's finalized state."""

    # frob:ticket T-1721
    def _evidence_only(self, ticket, ids: tuple[str, ...]):  # noqa: ANN001, ANN202
        return ticket.model_copy(update={"evidence": ids})

    # frob:ticket T-1721
    # frob:tests tests/test_ticket_land.py::TestCarryForwardOrRefuseSiblingEdits.test_worktree_only_edit_is_carried_forward  # noqa: E501
    def test_worktree_only_edit_is_carried_forward(self, tmp_path: Path) -> None:
        """The T-1637 shape exactly: B is DONE on both main and the
        worktree at the fork point; the worktree rebinds B's evidence
        (main never touches B again); landing A must carry B's rebind
        forward instead of reverting it to the base/main value."""
        created_a = new_ticket(tmp_path, _spec("Landing A"))
        assert created_a.is_ok
        tid_a = created_a.danger_ok.id
        created_b = new_ticket(tmp_path, _spec("Sibling B"))
        assert created_b.is_ok
        tid_b = created_b.danger_ok.id
        loaded_b = load_all(tmp_path).danger_ok[tid_b]
        done_b = loaded_b.model_copy(
            update={
                "state": TicketState.DONE,
                "evidence": ("tests/test_x.py::test_old",),
                "body": loaded_b.body + "\n## Done report\n\nshipped\n",
            }
        )
        assert write_ticket(tmp_path, done_b).is_ok
        base_text = ledger_path(tmp_path).read_text()

        # Worktree: rebinds B's evidence (a legitimate correction, no
        # state change) while separately landing A.
        rebound_b = done_b.model_copy(
            update={"evidence": ("tests/test_x.py::test_new",)}
        )
        assert write_ticket(tmp_path, rebound_b).is_ok
        assert transition(tmp_path, tid_a, TicketState.PLANNED).is_ok
        worktree_text = ledger_path(tmp_path).read_text()

        # Main: only ever saw B's original (base) state -- never touched
        # it again. main_text == base_text for B's own section.
        main_text = base_text

        spliced = _land_git_ops_mod._splice_only_ticket(
            main_text, worktree_text, tid_a, base_text=base_text
        )
        assert spliced.is_ok, spliced.err
        from frob.tickets._store import _parse_ledger

        merged = _parse_ledger(spliced.danger_ok).danger_ok
        assert merged[tid_b].evidence == ("tests/test_x.py::test_new",)

    # frob:ticket T-1721
    # frob:tests tests/test_ticket_land.py::TestCarryForwardOrRefuseSiblingEdits.test_main_only_edit_is_left_alone  # noqa: E501
    def test_main_only_edit_is_left_alone(self, tmp_path: Path) -> None:
        """Inverse of the above: main independently edited B since the
        base, the worktree never touched B at all -- main's edit must
        survive untouched (the ordinary, already-correct T-0479 case)."""
        created_a = new_ticket(tmp_path, _spec("Landing A"))
        assert created_a.is_ok
        tid_a = created_a.danger_ok.id
        created_b = new_ticket(tmp_path, _spec("Sibling B"))
        assert created_b.is_ok
        tid_b = created_b.danger_ok.id
        base_text = ledger_path(tmp_path).read_text()

        # Worktree: never touches B again after the base snapshot.
        assert transition(tmp_path, tid_a, TicketState.PLANNED).is_ok
        worktree_text = ledger_path(tmp_path).read_text()

        # Main: independently progresses B.
        assert transition(tmp_path, tid_b, TicketState.PLANNED).is_ok
        assert transition(tmp_path, tid_b, TicketState.IN_PROGRESS).is_ok
        main_text = ledger_path(tmp_path).read_text()

        spliced = _land_git_ops_mod._splice_only_ticket(
            main_text, worktree_text, tid_a, base_text=base_text
        )
        assert spliced.is_ok, spliced.err
        from frob.tickets._store import _parse_ledger

        merged = _parse_ledger(spliced.danger_ok).danger_ok
        assert merged[tid_b].state == TicketState.IN_PROGRESS

    # frob:ticket T-1721
    # frob:tests tests/test_ticket_land.py::TestCarryForwardOrRefuseSiblingEdits.test_both_sides_edit_the_same_way_converges_silently  # noqa: E501
    def test_both_sides_edit_the_same_way_converges_silently(
        self, tmp_path: Path
    ) -> None:
        """Both main and the worktree independently make the SAME edit to
        B (e.g. two agents both correctly rebind the same evidence id) --
        no conflict, both sides already agree, splice succeeds quietly."""
        created_a = new_ticket(tmp_path, _spec("Landing A"))
        assert created_a.is_ok
        tid_a = created_a.danger_ok.id
        created_b = new_ticket(tmp_path, _spec("Sibling B"))
        assert created_b.is_ok
        tid_b = created_b.danger_ok.id
        base_text = ledger_path(tmp_path).read_text()

        loaded_b = load_all(tmp_path).danger_ok[tid_b]
        agreed_b = self._evidence_only(loaded_b, ("tests/test_x.py::test_shared",))
        assert write_ticket(tmp_path, agreed_b).is_ok
        assert transition(tmp_path, tid_a, TicketState.PLANNED).is_ok
        worktree_text = ledger_path(tmp_path).read_text()
        # main independently converges to the identical evidence value.
        main_text = (
            ledger_path(tmp_path)
            .read_text()
            .replace("state: planned", "state: queued", 1)
        )

        spliced = _land_git_ops_mod._splice_only_ticket(
            main_text, worktree_text, tid_a, base_text=base_text
        )
        assert spliced.is_ok, spliced.err

    # frob:ticket T-1721
    # frob:tests tests/test_ticket_land.py::TestCarryForwardOrRefuseSiblingEdits.test_both_sides_edit_differently_refuses  # noqa: E501
    def test_both_sides_edit_differently_refuses(self, tmp_path: Path) -> None:
        """The genuine conflict this ticket exists to stop silently
        resolving: main and the worktree each independently rebind B's
        evidence to a DIFFERENT new id since the same base. Neither side
        is stale -- both made a real, independent edit. Must refuse
        (`SiblingLedgerEditConflict`), not silently pick one."""
        created_a = new_ticket(tmp_path, _spec("Landing A"))
        assert created_a.is_ok
        tid_a = created_a.danger_ok.id
        created_b = new_ticket(tmp_path, _spec("Sibling B"))
        assert created_b.is_ok
        tid_b = created_b.danger_ok.id
        base_text = ledger_path(tmp_path).read_text()

        loaded_b = load_all(tmp_path).danger_ok[tid_b]
        worktree_b = self._evidence_only(loaded_b, ("tests/test_x.py::test_worktree",))
        assert write_ticket(tmp_path, worktree_b).is_ok
        assert transition(tmp_path, tid_a, TicketState.PLANNED).is_ok
        worktree_text = ledger_path(tmp_path).read_text()

        main_b = self._evidence_only(loaded_b, ("tests/test_x.py::test_main",))
        assert _write_ticket_unchecked(tmp_path, main_b).is_ok
        main_text = ledger_path(tmp_path).read_text()

        spliced = _land_git_ops_mod._splice_only_ticket(
            main_text, worktree_text, tid_a, base_text=base_text
        )
        assert spliced.is_err
        assert spliced.danger_err.name == "SiblingLedgerEditConflict"

    # frob:ticket T-1721
    # frob:tests tests/test_ticket_land.py::TestCarryForwardOrRefuseSiblingEdits.test_no_base_available_falls_back_to_done_report_heuristic  # noqa: E501
    def test_no_base_available_falls_back_to_done_report_heuristic(
        self, tmp_path: Path
    ) -> None:
        """`base_text=None` (git could not resolve a merge-base) must
        degrade to the pre-T-1721 `_preserve_sibling_done_reports`
        heuristic, never a hard failure -- same shape
        `TestSiblingDoneReportPreserved` already pins for the no-base
        code path."""
        created_a = new_ticket(tmp_path, _spec("Landing A"))
        assert created_a.is_ok
        tid_a = created_a.danger_ok.id
        created_b = new_ticket(tmp_path, _spec("Sibling B"))
        assert created_b.is_ok
        tid_b = created_b.danger_ok.id
        main_text = ledger_path(tmp_path).read_text()

        loaded_b = load_all(tmp_path).danger_ok[tid_b]
        worktree_b = loaded_b.model_copy(
            update={"body": loaded_b.body + "\n## Done report\n\nshipped\n"}
        )
        assert write_ticket(tmp_path, worktree_b).is_ok
        assert transition(tmp_path, tid_a, TicketState.PLANNED).is_ok
        worktree_text = ledger_path(tmp_path).read_text()

        spliced = _land_git_ops_mod._splice_only_ticket(
            main_text, worktree_text, tid_a, base_text=None
        )
        assert spliced.is_ok, spliced.err
        from frob.tickets._store import _parse_ledger

        merged = _parse_ledger(spliced.danger_ok).danger_ok
        assert "## Done report" in merged[tid_b].body


# frob:ticket T-1194
class TestSiblingDoneReportPreserved:
    """T-0577: a real multi-ticket-worktree incident -- landing T-0386 in a
    worktree that ALSO carried sibling tickets T-0387/T-0388 (in-progress,
    review-gated, each with its own substantive Done report already
    written) spliced main's bare `queued` blocks for those siblings over
    the worktree's richer copies, erasing their Done reports and
    regressing their state. `_splice_only_ticket` must keep whichever side
    carries a substantive Done report when the OTHER side has none, even
    for a sibling id it does not otherwise touch."""

    # frob:tests src/frob/tickets/_land_ledger_merge.py::_splice_only_ticket kind="unit"
    def test_sibling_done_report_survives_landing_another_ticket(
        self, tmp_path: Path
    ) -> None:
        created_landed = new_ticket(tmp_path, _spec("Landed ticket"))
        assert created_landed.is_ok
        tid_landed = created_landed.danger_ok.id
        created_sibling = new_ticket(tmp_path, _spec("Sibling with done report"))
        assert created_sibling.is_ok
        tid_sibling = created_sibling.danger_ok.id

        # Worktree: sibling driven to in-progress with a substantive Done
        # report already written (review-gated, awaiting its OWN land).
        _make_closeable(tmp_path, tid_sibling)
        worktree_text = ledger_path(tmp_path).read_text()

        # Main: sibling is still a bare queued block (never advanced there
        # -- this worktree is the only place it has been worked).
        loaded = load_all(tmp_path).danger_ok
        bare_sibling = loaded[tid_sibling].model_copy(
            update={
                "state": TicketState.QUEUED,
                "evidence": (),
                "body": loaded[tid_sibling].body.split("## Done report")[0],
            }
        )
        merged = dict(loaded)
        merged[tid_sibling] = bare_sibling
        from frob.tickets._store import _render_ledger

        main_text = _render_ledger(merged)

        spliced = _land_git_ops_mod._splice_only_ticket(
            main_text, worktree_text, tid_landed
        )
        assert spliced.is_ok
        from frob.tickets._store import _parse_ledger

        parsed = _parse_ledger(spliced.danger_ok).danger_ok
        assert parsed[tid_sibling].state == TicketState.IN_PROGRESS
        assert "## Done report" in parsed[tid_sibling].body
        assert parsed[tid_sibling].evidence == ("tests/test_x.py::test_ok",)

    # frob:tests src/frob/tickets/_land_ledger_merge.py::_splice_only_ticket kind="unit"
    def test_sibling_requeue_on_main_still_wins_when_neither_side_has_a_done_report(
        self, tmp_path: Path
    ) -> None:
        """The T-0479/T-0475 case must stay fixed: a sibling with NO Done
        report on either side, stale in-progress in the worktree and
        requeued on main, still resolves to main's requeued state -- the
        T-0577 preservation rule only fires when the worktree side actually
        carries a Done report main lacks, never as a blanket "worktree
        wins" rule."""
        created_landed = new_ticket(tmp_path, _spec("Landed ticket"))
        assert created_landed.is_ok
        tid_landed = created_landed.danger_ok.id
        created_sibling = new_ticket(tmp_path, _spec("Sibling requeued"))
        assert created_sibling.is_ok
        tid_sibling = created_sibling.danger_ok.id

        assert transition(tmp_path, tid_sibling, TicketState.PLANNED).is_ok
        assert transition(tmp_path, tid_sibling, TicketState.IN_PROGRESS).is_ok
        worktree_text = ledger_path(tmp_path).read_text()

        assert transition(tmp_path, tid_sibling, TicketState.QUEUED).is_ok
        main_text = ledger_path(tmp_path).read_text()

        spliced = _land_git_ops_mod._splice_only_ticket(
            main_text, worktree_text, tid_landed
        )
        assert spliced.is_ok
        from frob.tickets._store import _parse_ledger

        parsed = _parse_ledger(spliced.danger_ok).danger_ok
        assert parsed[tid_sibling].state == TicketState.QUEUED


# frob:ticket T-0682
class TestSpliceLedgerRicherStatePreference:
    """T-0682: the git-merge-driver path (`splice_ledger`, invoked by the
    registered `tickets.md` merge driver for ANY `git merge`/`pull`/`rebase`
    -- not just `frob ticket land`'s own already-ticket-scoped internal
    splice) previously ranked a same-id divergence by state-rank alone,
    so a divergence where the Done-report side happened to sit at a LOWER
    state-rank than the reportless side still lost -- observed twice in the
    field landing T-0633/T-0637, where each land's merge-main-into-worktree
    stage regressed the landing ticket's own block back toward main's bare
    state (the Done report text itself survived only because it lives in
    the body, not the frontmatter `state:` field the rank comparison acted
    on).

    `_newer`'s fix is a QUALIFIED preference, not a blanket "report always
    wins": a first pass at this ticket made Done-report presence an
    unconditional override, which a reviewer caught as the INVERSE bug --
    a STALE report on a lower-rank block (e.g. a ticket requeued back down
    without its old report body ever getting stripped) would then beat a
    genuinely more-advanced, reportless side. The reported side now wins
    over a reportless one ONLY IF the reportless side does not STRICTLY
    outrank it; a strictly-higher-rank reportless side still wins. These
    tests mirror T-0577's two-direction shape, but against `splice_ledger`
    (the whole-ledger merge) directly rather than the ticket-scoped
    `_splice_only_ticket`."""

    # frob:tests tests/test_ticket_land.py::TestSpliceLedgerRicherStatePreference.test_report_side_still_wins_when_it_also_outranks_the_reportless_side  # noqa: E501
    def test_report_side_still_wins_when_it_also_outranks_the_reportless_side(
        self, tmp_path: Path
    ) -> None:
        """The original T-0682 field incident: `ours` (the worktree side,
        in a `merge main into worktree`) is `in-progress` (rank 2) with a
        substantive Done report; `theirs` (main) is a bare `queued` (rank
        0). The reported side is ALSO the higher-rank side here, so it
        wins under both the old (buggy) and new (qualified) rule -- this
        pins the incident that motivated the fix in the first place."""
        created = new_ticket(tmp_path, _spec("Landing ticket"))
        assert created.is_ok
        tid = created.danger_ok.id
        assert transition(tmp_path, tid, TicketState.PLANNED).is_ok
        assert transition(tmp_path, tid, TicketState.IN_PROGRESS).is_ok
        loaded = load_all(tmp_path).danger_ok[tid]
        with_report = loaded.model_copy(
            update={
                "body": loaded.body
                + "\n## Done report\n\nSubstantive report text here.\n"
            }
        )
        assert write_ticket(tmp_path, with_report).is_ok
        ours_text = ledger_path(tmp_path).read_text()

        theirs = with_report.model_copy(
            update={
                "state": TicketState.QUEUED,
                "body": with_report.body.split("## Done report")[0],
            }
        )
        assert _write_ticket_unchecked(tmp_path, theirs).is_ok
        theirs_text = ledger_path(tmp_path).read_text()

        spliced = splice_ledger(ours_text, theirs_text)
        assert spliced.is_ok
        from frob.tickets._store import _parse_ledger

        parsed = _parse_ledger(spliced.danger_ok).danger_ok
        assert parsed[tid].state == TicketState.IN_PROGRESS
        assert "## Done report" in parsed[tid].body

    # frob:tests tests/test_ticket_land.py::TestSpliceLedgerRicherStatePreference.test_stale_report_on_lower_rank_still_loses_to_a_strictly_outranking_reportless_side  # noqa: E501
    def test_stale_report_on_lower_rank_still_loses_to_a_strictly_outranking_reportless_side(  # noqa: E501
        self, tmp_path: Path
    ) -> None:
        """The reviewer-caught inverse case: `ours` is a bare `queued`
        (rank 0) that still carries a STALE Done report (e.g. requeued
        back down without the report ever being stripped); `theirs` is
        `in-progress` (rank 2, strictly higher) with no report at all --
        genuine further rework since. An unqualified "report always wins"
        rule would resurrect the stale queued+report block here; the
        qualification must let the strictly-outranking reportless side
        win instead."""
        created = new_ticket(tmp_path, _spec("Landing ticket"))
        assert created.is_ok
        tid = created.danger_ok.id
        loaded = load_all(tmp_path).danger_ok[tid]
        stale_with_report = loaded.model_copy(
            update={
                "body": loaded.body
                + "\n## Done report\n\nSubstantive report text here.\n"
            }
        )
        assert write_ticket(tmp_path, stale_with_report).is_ok
        ours_text = ledger_path(tmp_path).read_text()

        theirs = stale_with_report.model_copy(
            update={
                "state": TicketState.IN_PROGRESS,
                "body": stale_with_report.body.split("## Done report")[0],
            }
        )
        assert _write_ticket_unchecked(tmp_path, theirs).is_ok
        theirs_text = ledger_path(tmp_path).read_text()

        spliced = splice_ledger(ours_text, theirs_text)
        assert spliced.is_ok
        from frob.tickets._store import _parse_ledger

        parsed = _parse_ledger(spliced.danger_ok).danger_ok
        assert parsed[tid].state == TicketState.IN_PROGRESS
        assert "## Done report" not in parsed[tid].body

    # frob:tests tests/test_ticket_land.py::TestSpliceLedgerRicherStatePreference.test_stale_report_on_lower_rank_still_loses_regardless_of_which_side_it_is_on  # noqa: E501
    def test_stale_report_on_lower_rank_still_loses_regardless_of_which_side_it_is_on(
        self, tmp_path: Path
    ) -> None:
        """Same divergence as the previous test, but with the stale report
        on `theirs` instead of `ours` -- the qualification is symmetric,
        not an accidental artifact of argument order."""
        created = new_ticket(tmp_path, _spec("Landing ticket"))
        assert created.is_ok
        tid = created.danger_ok.id
        loaded = load_all(tmp_path).danger_ok[tid]
        stale_with_report = loaded.model_copy(
            update={
                "body": loaded.body
                + "\n## Done report\n\nSubstantive report text here.\n"
            }
        )
        assert write_ticket(tmp_path, stale_with_report).is_ok
        theirs_text = ledger_path(tmp_path).read_text()

        ours = stale_with_report.model_copy(
            update={
                "state": TicketState.IN_PROGRESS,
                "body": stale_with_report.body.split("## Done report")[0],
            }
        )
        assert _write_ticket_unchecked(tmp_path, ours).is_ok
        ours_text = ledger_path(tmp_path).read_text()

        spliced = splice_ledger(ours_text, theirs_text)
        assert spliced.is_ok
        from frob.tickets._store import _parse_ledger

        parsed = _parse_ledger(spliced.danger_ok).danger_ok
        assert parsed[tid].state == TicketState.IN_PROGRESS
        assert "## Done report" not in parsed[tid].body

    # frob:tests tests/test_ticket_land.py::TestSpliceLedgerRicherStatePreference.test_neither_side_reporting_still_falls_back_to_state_rank  # noqa: E501
    def test_neither_side_reporting_still_falls_back_to_state_rank(
        self, tmp_path: Path
    ) -> None:
        """The T-0577/T-0537 non-regression guard stays intact: when
        NEITHER side carries a substantive Done report, the comparison
        falls back to plain state-rank exactly as before -- this is not a
        blanket "richer body always wins" rule."""
        created = new_ticket(tmp_path, _spec("Closed elsewhere"))
        assert created.is_ok
        tid = created.danger_ok.id
        loaded = load_all(tmp_path).danger_ok[tid]
        done_ticket = loaded.model_copy(update={"state": TicketState.DONE})
        assert write_ticket(tmp_path, done_ticket).is_ok
        ours_text = ledger_path(tmp_path).read_text()

        stale = done_ticket.model_copy(update={"state": TicketState.QUEUED})
        assert write_ticket(tmp_path, stale).is_ok
        theirs_text = ledger_path(tmp_path).read_text()

        spliced = splice_ledger(ours_text, theirs_text)
        assert spliced.is_ok
        from frob.tickets._store import _parse_ledger

        parsed = _parse_ledger(spliced.danger_ok).danger_ok
        assert parsed[tid].state == TicketState.DONE


# frob:ticket T-0764
class TestSpliceLedgerPrefersEvidenceRichSideOnRankTie:
    """T-0764: the T-0753 field incident -- an in-flight worktree ticket
    with `start` + recorded evidence + a bound acceptance criterion but NO
    Done report yet, tied in state-rank (`in-progress`) with main's bare,
    reportless `in-progress` copy of the same id (e.g. after an
    archive/concurrent-ledger-rewrite reset the worktree's own view).
    Before T-0764 this fell straight to the old arbitrary `b`-wins
    tiebreak; now the evidence/acceptance-richer side must win."""

    # frob:ticket T-0764
    # frob:tests tests/test_ticket_land.py::TestSpliceLedgerPrefersEvidenceRichSideOnRankTie.test_evidence_and_acceptance_rich_side_wins_a_same_rank_reportless_tie  # noqa: E501
    def test_evidence_and_acceptance_rich_side_wins_a_same_rank_reportless_tie(
        self, tmp_path: Path
    ) -> None:
        created = new_ticket(
            tmp_path,
            TicketSpec(
                title="Landing ticket",
                kind=TicketKind.BUG,
                origin=Origin.AGENT,
                acceptance=(AcceptanceCriterion(text="GIVEN..WHEN..THEN.."),),
            ),
        )
        assert created.is_ok
        tid = created.danger_ok.id
        assert transition(tmp_path, tid, TicketState.PLANNED).is_ok
        assert transition(tmp_path, tid, TicketState.IN_PROGRESS).is_ok
        loaded = load_all(tmp_path).danger_ok[tid]

        rich = loaded.model_copy(
            update={
                "evidence": ("tests/test_widget.py::test_x",),
                "acceptance": (
                    AcceptanceCriterion(
                        text="GIVEN..WHEN..THEN..",
                        evidence=("tests/test_widget.py::test_x",),
                    ),
                ),
            }
        )
        assert write_ticket(tmp_path, rich).is_ok
        ours_text = ledger_path(tmp_path).read_text()

        # `theirs`: same id, same rank, no Done report on EITHER side, but
        # bare -- no evidence, no bound acceptance -- exactly the
        # archive/concurrent-rewrite reset shape from the T-0753 incident.
        bare = loaded.model_copy(update={"evidence": (), "acceptance": ()})
        assert _write_ticket_unchecked(tmp_path, bare).is_ok
        theirs_text = ledger_path(tmp_path).read_text()

        spliced = splice_ledger(ours_text, theirs_text)
        assert spliced.is_ok
        from frob.tickets._store import _parse_ledger

        parsed = _parse_ledger(spliced.danger_ok).danger_ok
        assert parsed[tid].evidence == ("tests/test_widget.py::test_x",)
        assert parsed[tid].acceptance[0].evidence == ("tests/test_widget.py::test_x",)

    # frob:ticket T-0764
    # frob:tests tests/test_ticket_land.py::TestSpliceLedgerPrefersEvidenceRichSideOnRankTie.test_acceptance_binding_unioned_even_when_the_reportless_higher_rank_side_wins  # noqa: E501
    def test_acceptance_binding_unioned_even_when_the_reportless_higher_rank_side_wins(
        self, tmp_path: Path
    ) -> None:
        """The `_union_acceptance` twin of D-09's `_union_evidence`: even
        when the WINNING side is picked for some other reason (here, a
        strictly higher rank), a criterion binding the LOSING side already
        had must not be silently dropped."""
        created = new_ticket(
            tmp_path,
            TicketSpec(
                title="Landing ticket",
                kind=TicketKind.BUG,
                origin=Origin.AGENT,
                acceptance=(AcceptanceCriterion(text="GIVEN..WHEN..THEN.."),),
            ),
        )
        assert created.is_ok
        tid = created.danger_ok.id
        loaded = load_all(tmp_path).danger_ok[tid]

        # `ours`: bare queued (rank 0) but with the criterion already bound.
        bound_but_low_rank = loaded.model_copy(
            update={
                "evidence": ("tests/test_widget.py::test_x",),
                "acceptance": (
                    AcceptanceCriterion(
                        text="GIVEN..WHEN..THEN..",
                        evidence=("tests/test_widget.py::test_x",),
                    ),
                ),
            }
        )
        assert write_ticket(tmp_path, bound_but_low_rank).is_ok
        ours_text = ledger_path(tmp_path).read_text()

        # `theirs`: strictly higher rank (in-progress), unbound criterion,
        # no Done report -- this side wins on rank, but must inherit the
        # OTHER side's binding rather than dropping it.
        assert transition(tmp_path, tid, TicketState.PLANNED).is_ok
        assert transition(tmp_path, tid, TicketState.IN_PROGRESS).is_ok
        theirs_text = ledger_path(tmp_path).read_text()

        spliced = splice_ledger(ours_text, theirs_text)
        assert spliced.is_ok
        from frob.tickets._store import _parse_ledger

        parsed = _parse_ledger(spliced.danger_ok).danger_ok
        assert parsed[tid].state == TicketState.IN_PROGRESS
        assert "tests/test_widget.py::test_x" in parsed[tid].evidence
        assert parsed[tid].acceptance[0].evidence == ("tests/test_widget.py::test_x",)


# frob:ticket T-1194
class TestSpliceLedgerIdDropGuard:
    """The structural guard the T-0367 incident demands: `splice_ledger`
    refuses loudly rather than silently committing a merge that drops an
    id (markerless-block class) or produces unparseable output."""

    # frob:ticket T-0764
    # frob:tests tests/test_ticket_land.py::TestSpliceLedgerIdDropGuard.test_a_side_only_id_missing_from_theirs_survives_the_splice  # noqa: E501
    def test_a_side_only_id_missing_from_theirs_survives_the_splice(
        self, tmp_path: Path
    ) -> None:
        """Sanity: an id present on only ONE side (never archived) is not
        itself an integrity violation -- the normal union-by-id case."""
        created = new_ticket(tmp_path, _spec("Ours-only ticket"))
        assert created.is_ok
        tid = created.danger_ok.id
        ours_text = ledger_path(tmp_path).read_text()
        theirs_text = "# Tickets\n\nCentral ledger managed by `frob ticket`.\n"

        spliced = splice_ledger(ours_text, theirs_text)
        assert spliced.is_ok
        from frob.tickets._store import _parse_ledger

        parsed = _parse_ledger(spliced.danger_ok).danger_ok
        assert tid in parsed

    # frob:ticket T-0764
    # frob:tests tests/test_ticket_land.py::TestSpliceLedgerIdDropGuard.test_malformed_side_is_refused_not_silently_treated_as_empty  # noqa: E501
    def test_malformed_side_is_refused_not_silently_treated_as_empty(
        self, tmp_path: Path
    ) -> None:
        """A hand-corrupted input ledger (a marker present but its yaml
        frontmatter fence broken) fails `_parse_ledger` up front --
        `splice_ledger` must propagate that `Err`, never silently treat the
        unparseable side as if it carried zero tickets (which would make
        every id on the OTHER, well-formed side look like a one-sided
        addition instead of a real divergence needing a human's eyes)."""
        created = new_ticket(tmp_path, _spec("A ticket"))
        assert created.is_ok
        ours_text = ledger_path(tmp_path).read_text()

        # Marker present, but no ```yaml fence follows it at all.
        theirs_text = "# Tickets\n\n<!-- ticket:T-9999 -->\nno yaml fence here\n"

        spliced = splice_ledger(ours_text, theirs_text)
        assert spliced.is_err

    # frob:ticket T-0764
    # frob:ticket T-1194
    # frob:tests tests/test_ticket_land.py::TestSpliceLedgerIdDropGuard.test_render_that_would_drop_an_id_is_refused  # noqa: E501
    def test_render_that_would_drop_an_id_is_refused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Direct unit-level pin on the guard itself: if the render step
        (patched here to simulate a future rendering regression) drops an
        id `_merge_ledger_tickets` produced, `splice_ledger` must refuse
        rather than commit the truncated text."""
        created = new_ticket(tmp_path, _spec("A ticket"))
        assert created.is_ok
        ours_text = ledger_path(tmp_path).read_text()
        theirs_text = "# Tickets\n\nCentral ledger managed by `frob ticket`.\n"

        def _dropping_render(tickets: dict) -> str:
            # Simulate a render bug: silently omit every ticket's section.
            return "# Tickets\n\nCentral ledger managed by `frob ticket`.\n"

        monkeypatch.setattr(_land_ledger_merge_mod, "_render_ledger", _dropping_render)
        spliced = splice_ledger(ours_text, theirs_text)
        assert spliced.is_err
        assert spliced.danger_err.name == "LedgerIntegrityViolation"


# frob:ticket T-1721
class TestLand:
    """`frob.tickets.land` against real fixture repos."""

    def test_dry_run_lands_cleanly_and_leaves_no_trace(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-a", str(wt)], repo)
        created = new_ticket(wt, _spec("Add widget", scope=("src/widget.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "widget.py").write_text("# new widget\n")
        _commit_all(wt, "add widget")

        # Main gains a commit AFTER the worktree branched, so merging main
        # into the worktree is a real merge, not a no-op.
        (repo / "src" / "unrelated.py").write_text("# unrelated main commit\n")
        _commit_all(repo, "unrelated main-side commit")

        before_main_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        before_wt_sha = _run(["git", "rev-parse", "HEAD"], wt).stdout.strip()

        result = land(repo, tid, wt, dry_run=True)
        assert result.is_ok, result.err
        report = result.danger_ok
        assert report.dry_run is True
        assert report.merged_main_into_worktree is True

        # Dry run must leave both checkouts exactly as found.
        assert (
            _run(["git", "rev-parse", "HEAD"], repo).stdout.strip() == before_main_sha
        )
        assert _run(["git", "rev-parse", "HEAD"], wt).stdout.strip() == before_wt_sha
        assert _status_ignoring_frob(repo) == ""
        assert _status_ignoring_frob(wt) == ""

    def test_real_land_lands(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-b", str(wt)], repo)
        created = new_ticket(wt, _spec("Add gadget", scope=("src/gadget.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "gadget.py").write_text("# new gadget\n")
        _commit_all(wt, "add gadget")

        result = land(repo, tid, wt, dry_run=False)
        assert result.is_ok, result.err
        report = result.danger_ok
        assert report.dry_run is False
        assert report.commit_sha is not None
        assert (repo / "src" / "gadget.py").exists()

        landed = load_all(repo)
        assert landed.is_ok
        assert landed.danger_ok[report.final_id].state == TicketState.DONE

    # frob:ticket T-1805
    def test_non_version_pyproject_edit_survives_land(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestLand.test_non_version_pyproject_edit_survives_land  # noqa: E501
        """T-1805 regression, end to end through the real `land()` entry
        point: a ticket whose ONLY change is a non-version
        `pyproject.toml` field (an optional-dependencies pin -- the exact
        shape T-1508's real, four-times-dropped z3-solver pin took) must
        still be on main after landing. Before the fix,
        `_reset_release_artifacts_to_pre_land`'s whole-file `git checkout`
        discarded this edit unconditionally, and `land()` still reported
        `Ok`/`verified=True` -- silent data loss with a green result."""
        (repo / "pyproject.toml").write_text(
            '[project]\nname = "x"\nversion = "0.1.0"\n\n'
            "[project.optional-dependencies]\n"
            'smt = ["z3-solver>=4.13"]\n',
            encoding="utf-8",
        )
        _commit_all(repo, "seed pyproject.toml")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-pin", str(wt)], repo)
        created = new_ticket(wt, _spec("Pin z3-solver", scope=("pyproject.toml",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "pyproject.toml").write_text(
            '[project]\nname = "x"\nversion = "0.1.0"\n\n'
            "[project.optional-dependencies]\n"
            'smt = ["z3-solver>=4.13,<4.15.5"]\n',
            encoding="utf-8",
        )
        _commit_all(wt, "pin z3-solver upper bound")

        # `bump_version` supplied (Ok(None): no new version needed) so the
        # reset path actually runs, same as a real `frob ticket land`
        # invocation always supplying its REL001 callback.
        def _no_bump_needed(
            _root: Path, _ticket: Any, _final_id: str
        ) -> Result[str | None, LandError]:
            return Ok(None)

        result = land(repo, tid, wt, dry_run=False, bump_version=_no_bump_needed)
        assert result.is_ok, result.err

        landed_pyproject = (repo / "pyproject.toml").read_text(encoding="utf-8")
        assert "z3-solver>=4.13,<4.15.5" in landed_pyproject
        # the version field itself is untouched -- this is a field-scoped
        # reset, not a bypass of T-1760's own reset entirely.
        assert 'version = "0.1.0"' in landed_pyproject

    # frob:ticket T-1721
    def test_sibling_evidence_rebind_carried_forward_end_to_end(
        self, repo: Path
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestLand.test_sibling_evidence_rebind_carried_forward_end_to_end  # noqa: E501
        """The real T-1637 field incident, reproduced end to end through
        the actual `land()` entry point (not just the splice primitive):
        a sibling ticket B is already DONE on main; in the SAME worktree
        that is landing ticket A, an agent rebinds B's evidence (a
        legitimate correction, e.g. after a rename -- no state change).
        Before T-1721, `land(repo, A, wt)` silently dropped B's rebind
        because `_splice_only_ticket`'s T-0479 sibling-scoping had no way
        to tell "B is merely stale" from "B was genuinely, deliberately
        edited". After T-1721, main's copy of B must carry the rebind."""
        created_b = new_ticket(repo, _spec("Sibling B, already done"))
        assert created_b.is_ok
        tid_b = created_b.danger_ok.id
        _make_closeable(repo, tid_b)
        assert transition(repo, tid_b, TicketState.DONE, covers_scope=True).is_ok
        _commit_all(repo, f"close {tid_b}")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-sibling-rebind", str(wt)], repo)

        created_a = new_ticket(wt, _spec("Landing A", scope=("src/a.py",)))
        assert created_a.is_ok
        tid_a = created_a.danger_ok.id
        _make_closeable(wt, tid_a)
        (wt / "src" / "a.py").write_text("# a\n")

        # The T-1637 shape: in the SAME worktree, rebind B's evidence to a
        # renamed test -- main never touches B again after this point.
        loaded_b = load_all(wt).danger_ok[tid_b]
        rebound_b = loaded_b.model_copy(
            update={"evidence": ("tests/test_x.py::TestFoo::test_renamed",)}
        )
        assert write_ticket(wt, rebound_b).is_ok
        _commit_all(wt, f"rebind {tid_b} evidence")

        result = land(repo, tid_a, wt, dry_run=False)
        assert result.is_ok, result.err

        landed = load_all(repo)
        assert landed.is_ok
        assert landed.danger_ok[tid_b].evidence == (
            "tests/test_x.py::TestFoo::test_renamed",
        )

    def test_refuses_on_dirty_main(self, repo: Path) -> None:
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-c", str(wt)], repo)
        created = new_ticket(wt, _spec("Whatever"))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        _commit_all(wt, "wip")

        (repo / "dirty.txt").write_text("uncommitted\n")

        result = land(repo, tid, wt, dry_run=True)
        assert result.is_err
        assert result.danger_err == LandError.DirtyMain

    def test_refuses_without_evidence_or_done_report(self, repo: Path) -> None:
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-d", str(wt)], repo)
        created = new_ticket(wt, _spec("Not ready"))
        assert created.is_ok
        tid = created.danger_ok.id
        _commit_all(wt, "wip")

        result = land(repo, tid, wt, dry_run=True)
        assert result.is_err
        assert result.danger_err == LandError.NotCloseable

        # Nothing must have been touched -- close validation runs BEFORE any
        # git mutation, so main and the worktree are exactly as found.
        assert _status_ignoring_frob(repo) == ""
        assert _run(["git", "status", "--porcelain"], wt).stdout.strip() == ""


# frob:ticket T-1036
class TestSquashSpliceLedgerChurn:
    """T-1036 regression: a concurrent single-ticket write against `root`
    landing in the window between `land`'s squash-merge and its own
    ledger splice must survive, never be silently overwritten by the
    splice's (previously stale) base-text snapshot."""

    # frob:tests tests/test_ticket_land.py::TestSquashSpliceLedgerChurn.test_concurrent_write_between_squash_and_splice_survives_land  # noqa: E501
    def test_concurrent_write_between_squash_and_splice_survives_land(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-race", str(wt)], repo)
        created = new_ticket(wt, _spec("Race widget", scope=("src/widget.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "widget.py").write_text("# race widget\n")
        _commit_all(wt, "add race widget")

        # T-1334: `git merge --squash` now runs inside
        # `_land_squash._squash_and_splice_ledger`, not `_land.py`.
        real_run_argv = _land_squash_mod.run_argv
        injected: dict[str, Any] = {"done": False, "sibling_id": None}

        def _fake_run_argv(argv: Sequence[str], **kwargs: Any) -> Any:
            result = real_run_argv(argv, **kwargs)
            # Fire exactly once, right after the squash-merge -- the
            # earliest possible moment `root`'s working tree has the
            # worktree's finalized branch content, and (before this
            # ticket's fix) exactly the window `_squash_and_splice_ledger`
            # used to build its splice from a snapshot taken BEFORE this
            # point, silently discarding anything written here.
            if (
                not injected["done"]
                and "merge" in argv
                and "--squash" in argv
                and result.is_ok
                and result.danger_ok.returncode == 0
            ):
                sibling = new_ticket(repo, _spec("Concurrent sibling"))
                assert sibling.is_ok
                injected["sibling_id"] = sibling.danger_ok.id
                injected["done"] = True
            return result

        monkeypatch.setattr(_land_squash_mod, "run_argv", _fake_run_argv)

        result = land(repo, tid, wt, dry_run=False)
        assert result.is_ok, result.err
        assert injected["done"] is True

        landed = load_all(repo)
        assert landed.is_ok
        assert injected["sibling_id"] in landed.danger_ok
        assert landed.danger_ok[result.danger_ok.final_id].state == TicketState.DONE


class TestPlannedStateAutoAdvanceOnLand:
    """T-0821: a ticket left in PLANNED (never run through `frob ticket
    start`, or reverted there by a section-10b ledger restore) but
    otherwise closeable (evidence + Done report) must land straight to
    DONE, not die `InvalidTransition` after main already merged."""

    # frob:ticket T-0821
    # frob:tests tests/test_ticket_land.py::TestPlannedStateAutoAdvanceOnLand.test_planned_ticket_with_full_evidence_lands_to_done  # noqa: E501
    def test_planned_ticket_with_full_evidence_lands_to_done(self, repo: Path) -> None:
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-planned", str(wt)], repo)
        created = new_ticket(wt, _spec("Add sprocket", scope=("src/sprocket.py",)))
        assert created.is_ok
        tid = created.danger_ok.id

        # Left in PLANNED (`frob ticket start`'s first transition), never
        # advanced to IN_PROGRESS -- but evidence and a Done report are
        # both present, exactly the T-0799/T-0752/T-0815 incident shape.
        assert transition(wt, tid, TicketState.PLANNED).is_ok
        loaded = load_all(wt)
        ticket = loaded.danger_ok[tid]
        ticket = ticket.model_copy(
            update={
                "evidence": ("tests/test_x.py::test_ok",),
                "body": ticket.body + "\n## Done report\n\nevidence attached\n",
            }
        )
        assert write_ticket(wt, ticket).is_ok
        assert load_all(wt).danger_ok[tid].state == TicketState.PLANNED

        (wt / "src" / "sprocket.py").write_text("# new sprocket\n")
        _commit_all(wt, "add sprocket")

        result = land(repo, tid, wt, dry_run=False)
        assert result.is_ok, result.err
        report = result.danger_ok

        landed = load_all(repo)
        assert landed.is_ok
        assert landed.danger_ok[report.final_id].state == TicketState.DONE


class TestWarnIfNativeStale:
    """T-0248: `land` warns loudly (without blocking) when the just-landed
    tree's native source outpaces its own built extension -- the T-0166
    review incident class."""

    def test_real_land_logs_stale_native_warning(
        self,
        repo: Path,
        caplog: pytest.LogCaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # frob:tests src/frob/tickets/_land_release.py::_warn_if_native_stale \
        # kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-native", str(wt)], repo)
        created = new_ticket(wt, _spec("Grammar change", scope=("src/grammar.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "grammar.py").write_text("# grammar change\n")
        _commit_all(wt, "grammar change")

        monkeypatch.setattr(
            "frob.strata._native_staleness.stale_native_warning",
            lambda root: "STALE NATIVE: fake grammar-ahead-of-native fixture",
        )

        with caplog.at_level("WARNING", logger="frob.tickets._land"):
            result = land(repo, tid, wt, dry_run=False)

        assert result.is_ok, result.err
        assert any("STALE NATIVE" in record.message for record in caplog.records)

    def test_real_land_no_warning_when_native_fresh(
        self, repo: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests src/frob/tickets/_land_release.py::_warn_if_native_stale \
        # kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-native-fresh", str(wt)], repo)
        created = new_ticket(wt, _spec("Non-native change", scope=("src/other.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "other.py").write_text("# unrelated change\n")
        _commit_all(wt, "unrelated change")

        result = land(repo, tid, wt, dry_run=False)
        assert result.is_ok, result.err
        assert not any("STALE NATIVE" in r.message for r in caplog.records)


class TestCloseFailAfterMerge:
    """`_transition_guard` can still refuse `DONE` even after `_validate_
    closeable`'s precheck passed on the worktree's OWN snapshot -- the
    splice can overwrite the worktree's in-memory ticket with a further-
    along same-id entry from main (e.g. DROPPED, a terminal state with no
    outgoing transitions) between the precheck and the close call. `land`
    must surface `LandError.CloseFailed` and name the manual remedy rather
    than silently landing a ticket main considers dropped."""

    def test_close_fails_after_merge_when_main_dropped_same_id(
        self, repo: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-k", str(wt)], repo)

        created = new_ticket(wt, _spec("Race with main", scope=("src/raced.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "raced.py").write_text("# raced feature\n")
        _commit_all(wt, "add raced feature")

        # Main independently ends up with the SAME ticket id, further along
        # the state machine (DROPPED, terminal) -- simulating a race where
        # main dropped this exact ticket after the worktree branched.
        atomic_write(ledger_path(repo), "# Tickets\n\n")
        dropped = created.danger_ok.model_copy(update={"state": TicketState.DROPPED})
        assert write_ticket(repo, dropped).is_ok
        _commit_all(repo, "main independently drops the same ticket id")

        result = land(repo, tid, wt, dry_run=False)
        assert result.is_err
        assert result.danger_err == LandError.CloseFailed

        # The merge into the worktree landed (that happens before close),
        # but main itself must be untouched -- the failure surfaces before
        # any squash-apply onto main.
        landed_main = load_all(repo)
        assert landed_main.is_ok
        assert landed_main.danger_ok[tid].state == TicketState.DROPPED


class TestStaleBaseDeletion:
    """Incident class 1: a worktree branched from an old main base ends up,
    relative to main's CURRENT tip, deleting a file main already landed --
    the deletion-filter check must abort loudly rather than let that
    deletion reach main."""

    def test_unowned_deletion_aborts_loudly(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-e", str(wt)], repo)

        # The worktree's own (out-of-scope) change deletes a file main has
        # -- simulating a stale-base agent that clobbered an unrelated file
        # it never should have touched.
        (wt / "src" / "feature.py").unlink()
        created = new_ticket(wt, _spec("Unrelated ticket", scope=("src/other.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        _commit_all(wt, "accidentally delete feature.py")

        result = land(repo, tid, wt, dry_run=True)
        assert result.is_err
        assert result.danger_err == LandError.UnownedDeletions

        # Worktree must be left clean (merge --abort ran) -- no half-applied
        # merge state left behind by the aborted dry run.
        assert _run(["git", "status", "--porcelain"], wt).stdout.strip() == ""
        assert (repo / "src" / "feature.py").exists()

    def test_scoped_deletion_is_allowed(self, repo: Path) -> None:
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-f", str(wt)], repo)

        (wt / "src" / "feature.py").unlink()
        created = new_ticket(wt, _spec("Retire feature", scope=("src/feature.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        _commit_all(wt, "retire feature.py, in scope")

        result = land(repo, tid, wt, dry_run=True)
        assert result.is_ok, result.err


# frob:ticket T-1323
class TestUncommittedWaiveDeletionRefusal:
    """T-1323 incident guard: the 2026-07-29 land that wip-snapshotted an
    uncommitted, out-of-scope `frob:waive` DELETION and squash-applied it
    onto main. `land` must refuse BEFORE any git mutation (no wip-commit,
    no merge) when the worktree's dirty state removes a `frob:waive`
    directive whose file is neither in the landing ticket's scope nor
    named in its Done report."""

    def test_out_of_scope_undeclared_waive_deletion_refuses_before_merge(
        self, repo: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        (repo / "src" / "other.py").write_text(
            '# frob:waive PERF001 reason="genuinely needed, not this ticket"\n'
            "def g():\n    pass\n"
        )
        _commit_all(repo, "add other.py with a live PERF001 waiver")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-waive-1", str(wt)], repo)

        created = new_ticket(wt, _spec("Unrelated ticket", scope=("src/feature.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        # Uncommitted deletion of the waiver comment -- out of ticket
        # scope, never mentioned in its Done report. Deliberately left
        # UNCOMMITTED: this is the exact laundering shape (dirty worktree
        # state that a wip-commit would otherwise fold into the merge
        # unattributed).
        (wt / "src" / "other.py").write_text("def g():\n    pass\n")

        result = land(repo, tid, wt, dry_run=True)

        assert result.is_err
        assert result.danger_err == LandError.OutOfScopeWaiveDeletion
        # Refused before any mutation: no wip-commit, no merge attempt --
        # the worktree's dirty state is untouched.
        status = _run(["git", "status", "--porcelain"], wt).stdout
        assert "src/other.py" in status
        assert (repo / "src" / "other.py").read_text().count("frob:waive") == 1

    def test_in_scope_waive_deletion_is_allowed(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        (repo / "src" / "other.py").write_text(
            '# frob:waive PERF001 reason="stale, being removed by this ticket"\n'
            "def g():\n    pass\n"
        )
        _commit_all(repo, "add other.py with a stale PERF001 waiver")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-waive-2", str(wt)], repo)

        created = new_ticket(wt, _spec("Retire stale waiver", scope=("src/other.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "other.py").write_text("def g():\n    pass\n")

        result = land(repo, tid, wt, dry_run=True)

        assert result.is_ok, result.err

    def test_declared_in_done_report_waive_deletion_is_allowed(
        self, repo: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        (repo / "src" / "other.py").write_text(
            '# frob:waive PERF001 reason="stale, being removed by this ticket"\n'
            "def g():\n    pass\n"
        )
        _commit_all(repo, "add other.py with a stale PERF001 waiver")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-waive-3", str(wt)], repo)

        created = new_ticket(wt, _spec("Unrelated ticket", scope=("src/feature.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        assert transition(wt, tid, TicketState.PLANNED).is_ok
        assert transition(wt, tid, TicketState.IN_PROGRESS).is_ok
        loaded = load_all(wt)
        ticket = loaded.danger_ok[tid]
        ticket = ticket.model_copy(
            update={
                "evidence": ("tests/test_x.py::test_ok",),
                "body": (
                    ticket.body
                    + "\n## Done report\n\nAlso removed the stale "
                    + "frob:waive PERF001 in src/other.py (found while "
                    + "working this ticket).\n"
                ),
            }
        )
        assert write_ticket(wt, ticket).is_ok
        (wt / "src" / "other.py").write_text("def g():\n    pass\n")

        result = land(repo, tid, wt, dry_run=True)

        assert result.is_ok, result.err

    def test_prose_mention_outside_done_report_is_not_a_declaration(
        self, repo: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        # T-1323 review fix: a rule id appearing in ordinary body prose
        # (not the Done report section) must NOT satisfy the declaration
        # escape hatch -- the append-only ledger accumulates incidental
        # mentions, and substring-anywhere matching laundered exactly the
        # incident this guard exists to refuse.
        (repo / "src" / "other.py").write_text(
            '# frob:waive PERF001 reason="load-bearing, must not vanish"\n'
            "def g():\n    pass\n"
        )
        _commit_all(repo, "add other.py with a live PERF001 waiver")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-waive-4", str(wt)], repo)

        created = new_ticket(wt, _spec("Unrelated ticket", scope=("src/feature.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        assert transition(wt, tid, TicketState.PLANNED).is_ok
        assert transition(wt, tid, TicketState.IN_PROGRESS).is_ok
        loaded = load_all(wt)
        ticket = loaded.danger_ok[tid]
        ticket = ticket.model_copy(
            update={
                "evidence": ("tests/test_x.py::test_ok",),
                "body": (
                    ticket.body
                    + "\nEarlier discussion mentioned PERF001 and "
                    + "src/other.py in passing, long before any work "
                    + "happened.\n"
                    + "\n## Done report\n\nImplemented the feature in "
                    + "src/feature.py; no waivers were touched.\n"
                ),
            }
        )
        assert write_ticket(wt, ticket).is_ok
        (wt / "src" / "other.py").write_text("def g():\n    pass\n")

        result = land(repo, tid, wt, dry_run=True)

        assert result.is_err
        assert result.danger_err == LandError.OutOfScopeWaiveDeletion


# frob:ticket T-1468
# frob:ticket T-1332
# frob:ticket T-1636
class TestWaiveRewrapNotDeletion:
    """T-1468: a `frob fmt` re-wrap of a multi-line `frob:waive` comment's
    `reason="..."` continuation (changing how many physical lines it spans
    without changing its actual content) must NOT trip the T-1323/T-1326
    out-of-scope waive-deletion refusal -- only a genuine content removal
    should."""

    # frob:ticket T-1468
    # frob:ticket T-1636
    def test_rewrap_only_diff_is_not_flagged_as_a_deletion(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land_git_ops.py::_uncommitted_waive_deletions \
        # kind="integration"
        # T-1636: exercised only through the full `land(..., dry_run=True)`
        # pipeline several call-hops deep, not a direct call a static call-graph can
        # see -- COV006's own kind="integration" trust-at-face-value convention.
        (repo / "src" / "other.py").write_text(
            '# frob:waive PERF001 reason="some very long reason that used to fit on \\\n'
            '# two lines like this"\n'
            "def g():\n    pass\n"
        )
        _commit_all(repo, "add other.py with a wrapped PERF001 waiver")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-waive-rewrap", str(wt)], repo)

        created = new_ticket(wt, _spec("Unrelated ticket", scope=("src/feature.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        # Re-wrap the SAME reason text across three physical lines instead
        # of two -- a `frob fmt` line-length absorption, not a content
        # change. Out of this ticket's scope, uncommitted (the exact T-1323
        # laundering shape), but it must not refuse: the normalized content
        # is byte-identical to what it replaces.
        (wt / "src" / "other.py").write_text(
            '# frob:waive PERF001 reason="some very long reason that used \\\n'
            "# to fit \\\n"
            '# on two lines like this"\n'
            "def g():\n    pass\n"
        )

        result = land(repo, tid, wt, dry_run=True)

        assert result.is_ok, result.err

    # frob:ticket T-1468
    # frob:ticket T-1636
    def test_rewrap_that_also_changes_content_still_refuses(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land_git_ops.py::_uncommitted_waive_deletions \
        # kind="integration"
        # T-1636: exercised only through the full `land(..., dry_run=True)`
        # pipeline several call-hops deep, not a direct call a static call-graph can
        # see -- COV006's own kind="integration" trust-at-face-value convention.
        (repo / "src" / "other.py").write_text(
            '# frob:waive PERF001 reason="some very long reason that used to fit on \\\n'
            '# two lines like this"\n'
            "def g():\n    pass\n"
        )
        _commit_all(repo, "add other.py with a wrapped PERF001 waiver")

        wt = repo.parent / "wt"
        _run(
            ["git", "worktree", "add", "-b", "feature-waive-rewrap-changed", str(wt)],
            repo,
        )

        created = new_ticket(wt, _spec("Unrelated ticket", scope=("src/feature.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        # Re-wrapped AND the reason text itself genuinely changed -- this
        # must still refuse, since the normalized content differs.
        (wt / "src" / "other.py").write_text(
            '# frob:waive PERF001 reason="a completely different reason \\\n'
            '# spanning two lines now"\n'
            "def g():\n    pass\n"
        )

        result = land(repo, tid, wt, dry_run=True)

        assert result.is_err
        assert result.danger_err == LandError.OutOfScopeWaiveDeletion

    # frob:ticket T-1388
    def test_real_fmt001_fixer_rewrap_does_not_trip_the_guard(self, repo: Path) -> None:
        """T-1388: the incident this ticket reports is land's OWN pre-land
        Tier-A auto-fix pass (FMT001, `frob.gates._fmt_directives.
        format_paths`) rewrapping an out-of-scope file's `frob:waive`
        comment and then self-refusing on the very edit it just made.
        `TestWaiveRewrapNotDeletion`'s other tests prove the underlying
        `_uncommitted_out_of_scope_waive_deletions` mechanism (T-1468) is
        rewrap-insensitive against a HAND-WRITTEN rewrap; this test drives
        the same guard against the REAL fixer's OWN output instead, to
        pin the exact mechanism the ticket names rather than a synthetic
        stand-in for it."""
        # frob:tests \
        # tests/test_ticket_land.py::TestWaiveRewrapNotDeletion.test_real_fmt001_fixer_\
        # rewrap_does_not_trip_the_guard
        from frob.gates._fmt_directives import format_paths

        (repo / "src" / "other.py").write_text(
            '# frob:waive PERF001 reason="some very long reason that used to fit on '
            'a single physical line under the default 88-col limit ok"\n'
            "def g():\n    pass\n"
        )
        _commit_all(repo, "add other.py with an over-long single-line PERF001 waiver")

        wt = repo.parent / "wt"
        _run(
            ["git", "worktree", "add", "-b", "feature-fmt001-real-rewrap", str(wt)],
            repo,
        )

        created = new_ticket(wt, _spec("Unrelated ticket", scope=("src/feature.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)

        # This is what land's own pre-land Tier-A/FMT001 pass does: run
        # the real fixer against the whole tree (the pre-T-1404 unscoped
        # shape, still the fallback path when a touched-set cannot be
        # computed), rewrapping `other.py`'s over-long waiver line even
        # though `other.py` is entirely outside this ticket's scope.
        report = format_paths(wt, check_only=False, limit=88)
        assert any(c.path == "src/other.py" for c in report.changes)

        result = land(repo, tid, wt, dry_run=True)

        assert result.is_ok, result.err


# frob:ticket T-1326
# frob:ticket T-1332
class TestCommittedWaiveDeletionRefusal:
    """T-1326: extends the T-1323 guard from the worktree's UNCOMMITTED
    state to its COMMITTED branch history (`merge-base..HEAD`) -- the
    reviewer-flagged laundering gap left open at T-1323's own approval,
    where a `frob:waive` deletion COMMITTED mid-ticket (rather than left
    uncommitted) rode the merge unattributed."""

    def test_committed_out_of_scope_undeclared_waive_deletion_refuses_before_merge(
        self, repo: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        (repo / "src" / "other.py").write_text(
            '# frob:waive PERF001 reason="genuinely needed, not this ticket"\n'
            "def g():\n    pass\n"
        )
        _commit_all(repo, "add other.py with a live PERF001 waiver")

        wt = repo.parent / "wt"
        _run(
            ["git", "worktree", "add", "-b", "feature-waive-committed-1", str(wt)], repo
        )

        created = new_ticket(wt, _spec("Unrelated ticket", scope=("src/feature.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        # Deletion of the waiver comment is COMMITTED to the branch, not
        # left dirty -- the exact laundering shape T-1323's own guard
        # could not see (it only ever inspected `git diff HEAD`).
        (wt / "src" / "other.py").write_text("def g():\n    pass\n")
        _commit_all(wt, "unrelated cleanup that happens to drop a waiver")

        result = land(repo, tid, wt, dry_run=True)

        assert result.is_err
        assert result.danger_err == LandError.OutOfScopeWaiveDeletion
        # Refused before any mutation: no merge attempt against main.
        assert (repo / "src" / "other.py").read_text().count("frob:waive") == 1

    def test_committed_in_scope_waive_deletion_is_allowed(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        (repo / "src" / "other.py").write_text(
            '# frob:waive PERF001 reason="stale, being removed by this ticket"\n'
            "def g():\n    pass\n"
        )
        _commit_all(repo, "add other.py with a stale PERF001 waiver")

        wt = repo.parent / "wt"
        _run(
            ["git", "worktree", "add", "-b", "feature-waive-committed-2", str(wt)], repo
        )

        created = new_ticket(wt, _spec("Retire stale waiver", scope=("src/other.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "other.py").write_text("def g():\n    pass\n")
        _commit_all(wt, "retire the stale PERF001 waiver, in scope")

        result = land(repo, tid, wt, dry_run=True)

        assert result.is_ok, result.err

    def test_committed_declared_in_done_report_waive_deletion_is_allowed(
        self, repo: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        (repo / "src" / "other.py").write_text(
            '# frob:waive PERF001 reason="stale, being removed by this ticket"\n'
            "def g():\n    pass\n"
        )
        _commit_all(repo, "add other.py with a stale PERF001 waiver")

        wt = repo.parent / "wt"
        _run(
            ["git", "worktree", "add", "-b", "feature-waive-committed-3", str(wt)], repo
        )

        created = new_ticket(wt, _spec("Unrelated ticket", scope=("src/feature.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        assert transition(wt, tid, TicketState.PLANNED).is_ok
        assert transition(wt, tid, TicketState.IN_PROGRESS).is_ok
        loaded = load_all(wt)
        ticket = loaded.danger_ok[tid]
        ticket = ticket.model_copy(
            update={
                "evidence": ("tests/test_x.py::test_ok",),
                "body": (
                    ticket.body
                    + "\n## Done report\n\nAlso removed the stale "
                    + "frob:waive PERF001 in src/other.py (found while "
                    + "working this ticket).\n"
                ),
            }
        )
        assert write_ticket(wt, ticket).is_ok
        (wt / "src" / "other.py").write_text("def g():\n    pass\n")
        _commit_all(wt, "remove the stale waiver, declared in the Done report")

        result = land(repo, tid, wt, dry_run=True)

        assert result.is_ok, result.err

    def test_merge_base_drift_deletion_on_main_side_not_counted(
        self, repo: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        # The waiver is deleted on MAIN's own side of the merge-base --
        # never touched by the landing ticket's branch at all -- so it
        # must NOT appear in the branch's `merge-base..HEAD` range and
        # must NOT be counted against this land.
        (repo / "src" / "other.py").write_text(
            '# frob:waive PERF001 reason="genuinely needed, unrelated"\n'
            "def g():\n    pass\n"
        )
        _commit_all(repo, "add other.py with a live PERF001 waiver")

        wt = repo.parent / "wt"
        _run(
            ["git", "worktree", "add", "-b", "feature-waive-committed-4", str(wt)], repo
        )

        created = new_ticket(wt, _spec("Unrelated ticket", scope=("src/feature.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)

        # main deletes the waiver AFTER the branch point -- not part of
        # the branch's own committed history.
        (repo / "src" / "other.py").write_text("def g():\n    pass\n")
        _commit_all(repo, "main-side: drop the PERF001 waiver, unrelated to the ticket")

        result = land(repo, tid, wt, dry_run=True)

        assert result.is_ok, result.err

    # frob:ticket T-1332
    def test_branch_merges_main_after_main_deletes_a_waiver_still_allowed(
        self, repo: Path
    ) -> None:
        """T-1332 acceptance [0]: unlike `test_merge_base_drift_deletion_
        on_main_side_not_counted` above (main deletes the waiver but the
        branch never re-syncs with main at all), this scenario has the
        landing branch run a real `git merge main` AFTER main's deletion
        commit -- the shape every agent worktree actually goes through
        (playbook section 1's mandatory warm-up merge, and any mid-ticket
        `git merge main`). The merge commit's own diff against the branch's
        PRE-merge tip textually contains the deletion (that is what a merge
        commit IS), so a naive `merge_base..HEAD` computed against a STALE
        merge-base would wrongly see it as the branch's own doing. `_true_
        merge_base` is computed FRESH at land time, so after the merge the
        true common ancestor advances to (at least) main's deletion commit
        itself, and the deletion drops out of `merge_base..HEAD` entirely --
        this test locks that in with a REAL `git merge main`, not just an
        unmerged branch-point scenario."""
        # frob:tests \
        # tests/test_ticket_land.py::TestCommittedWaiveDeletionRefusal.test_branch_merg\
        # es_main_after_main_deletes_a_waiver_still_allowed
        (repo / "src" / "other.py").write_text(
            '# frob:waive PERF001 reason="genuinely needed, unrelated"\n'
            "def g():\n    pass\n"
        )
        _commit_all(repo, "add other.py with a live PERF001 waiver")

        wt = repo.parent / "wt"
        _run(
            ["git", "worktree", "add", "-b", "feature-waive-merge-main", str(wt)], repo
        )

        created = new_ticket(wt, _spec("Unrelated ticket", scope=("src/feature.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)

        # main legitimately deletes the waiver AFTER the branch point.
        (repo / "src" / "other.py").write_text("def g():\n    pass\n")
        _commit_all(repo, "main-side: drop the PERF001 waiver, unrelated to the ticket")

        # The branch pulls that deletion in via a real merge -- the exact
        # mid-flight sync every worktree agent performs.
        _run(["git", "fetch", str(repo), "main:refs/remotes/origin/main"], wt)
        _run(["git", "merge", "refs/remotes/origin/main", "--no-edit"], wt)

        result = land(repo, tid, wt, dry_run=True)

        assert result.is_ok, result.err

    # frob:ticket T-1550
    def test_already_landed_sibling_deletion_on_shared_worktree_not_recounted(
        self, repo: Path
    ) -> None:
        """T-1550: the exact multi-ticket-worktree shape T-1225/T-1444 hit
        for real. Ticket A declares its own out-of-scope waiver deletion in
        its Done report, lands (a REAL, non-dry-run land, so the deletion
        is now genuinely reflected on `main`) -- then ticket B, continuing
        on the SAME worktree branch (never re-merging main, exactly the
        shape a multi-ticket worktree agent runs per the playbook), lands
        with no waiver deletion of its own. Before T-1550, B's committed-
        history scan diffed from the STALE `merge_base` captured before A
        ever landed, so A's now-landed deletion still showed up in
        `merge_base..HEAD` and B's land was wrongly refused with
        `OutOfScopeWaiveDeletion` even though B never touched it and A's
        deletion is already legitimately on `main`."""
        (repo / "src" / "other.py").write_text(
            '# frob:waive PERF001 reason="stale, ticket A retires this"\n'
            "def g():\n    pass\n"
        )
        _commit_all(repo, "add other.py with a stale PERF001 waiver")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-shared-1550", str(wt)], repo)

        # Ticket A: declares and commits the waiver deletion, then lands
        # for real -- `other.py`'s waiver is now genuinely gone on main.
        created_a = new_ticket(wt, _spec("Ticket A", scope=("src/feature.py",)))
        assert created_a.is_ok
        tid_a = created_a.danger_ok.id
        assert transition(wt, tid_a, TicketState.PLANNED).is_ok
        assert transition(wt, tid_a, TicketState.IN_PROGRESS).is_ok
        loaded = load_all(wt)
        ticket_a = loaded.danger_ok[tid_a]
        ticket_a = ticket_a.model_copy(
            update={
                "evidence": ("tests/test_x.py::test_ok",),
                "body": (
                    ticket_a.body
                    + "\n## Done report\n\nAlso removed the stale "
                    + "frob:waive PERF001 in src/other.py (found while "
                    + "working this ticket).\n"
                ),
            }
        )
        assert write_ticket(wt, ticket_a).is_ok
        (wt / "src" / "other.py").write_text("def g():\n    pass\n")
        _commit_all(wt, "ticket A: retire the stale waiver, declared in Done report")

        land_a = land(repo, tid_a, wt, dry_run=False)
        assert land_a.is_ok, land_a.err
        assert "frob:waive" not in (repo / "src" / "other.py").read_text()

        # Ticket B: same worktree, same branch, no re-merge of main -- the
        # multi-ticket-worktree shape this ticket fixes. B never touches
        # other.py at all.
        created_b = new_ticket(wt, _spec("Ticket B", scope=("src/feature.py",)))
        assert created_b.is_ok
        tid_b = created_b.danger_ok.id
        _make_closeable(wt, tid_b)

        result_b = land(repo, tid_b, wt, dry_run=True)

        assert result_b.is_ok, result_b.err


# frob:ticket T-1332
class TestRenameAwareWaiveDeletionAttribution:
    """T-1332 acceptance [1]: `_waive_deletions_in_diff` reads the
    pre-image path off the hunk's file header (`--- a/<path>`), which for
    a pure rename+edit is the file's OLD name, not the new one a scope
    glob would actually match -- untested on both the uncommitted (T-1323)
    and committed (T-1326) checks before this ticket."""

    # frob:ticket T-1332
    def test_committed_waiver_deleted_inside_a_rename_attributes_to_old_path(
        self, repo: Path
    ) -> None:
        """A `frob:waive` deleted in the SAME commit that renames its file
        (`git mv old new` + edit) must be attributed to a real path this
        guard can evaluate scope-ownership against -- proving WHICH path
        (old or new) `_committed_out_of_scope_waive_deletions` actually
        uses, per the ticket's own "test proves which" acceptance wording.
        Declaring the OLD path in scope must suffice to allow the land
        (this is the behavior as implemented: the hunk's pre-image path is
        what `git diff --no-color -U0` reports as the file the `-` line
        belongs to)."""
        # frob:tests \
        # tests/test_ticket_land.py::TestRenameAwareWaiveDeletionAttribution.test_commi\
        # tted_waiver_deleted_inside_a_rename_attributes_to_old_path
        (repo / "src" / "old.py").write_text(
            '# frob:waive PERF001 reason="stale, being removed by this ticket"\n'
            "def g():\n    pass\n"
        )
        _commit_all(repo, "add old.py with a stale PERF001 waiver")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-waive-rename-1", str(wt)], repo)

        created = new_ticket(
            wt, _spec("Retire stale waiver via rename", scope=("src/old.py",))
        )
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)

        _run(["git", "mv", "src/old.py", "src/new.py"], wt)
        (wt / "src" / "new.py").write_text("def g():\n    pass\n")
        _commit_all(wt, "rename old.py to new.py, dropping the stale waiver")

        result = land(repo, tid, wt, dry_run=True)

        assert result.is_ok, result.err

    # frob:ticket T-1332
    def test_committed_waiver_deleted_inside_a_rename_out_of_scope_still_refuses(
        self, repo: Path
    ) -> None:
        """The mirror of the test above: when NEITHER the old nor the new
        path is in the landing ticket's scope, a waiver dropped inside a
        rename must still refuse -- proving the rename does not
        accidentally become a laundering vector (a rename any agent could
        perform to dodge the guard) on top of proving which path is
        checked."""
        # frob:tests \
        # tests/test_ticket_land.py::TestRenameAwareWaiveDeletionAttribution.test_commi\
        # tted_waiver_deleted_inside_a_rename_out_of_scope_still_refuses
        (repo / "src" / "old.py").write_text(
            '# frob:waive PERF001 reason="genuinely needed, not this ticket"\n'
            "def g():\n    pass\n"
        )
        _commit_all(repo, "add old.py with a live PERF001 waiver")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-waive-rename-2", str(wt)], repo)

        created = new_ticket(wt, _spec("Unrelated ticket", scope=("src/feature.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)

        _run(["git", "mv", "src/old.py", "src/new.py"], wt)
        (wt / "src" / "new.py").write_text("def g():\n    pass\n")
        _commit_all(wt, "unrelated rename that happens to drop a waiver")

        result = land(repo, tid, wt, dry_run=True)

        assert result.is_err
        assert result.danger_err == LandError.OutOfScopeWaiveDeletion

    # frob:ticket T-1332
    def test_uncommitted_waiver_deleted_inside_a_rename_attributes_to_old_path(
        self, repo: Path
    ) -> None:
        """The UNCOMMITTED (T-1323) mirror of the committed-history rename
        test above: `git mv` + edit left dirty (not yet committed) must
        still be attributed correctly when the OLD path is in scope."""
        # frob:tests \
        # tests/test_ticket_land.py::TestRenameAwareWaiveDeletionAttribution.test_uncom\
        # mitted_waiver_deleted_inside_a_rename_attributes_to_old_path
        (repo / "src" / "old.py").write_text(
            '# frob:waive PERF001 reason="stale, being removed by this ticket"\n'
            "def g():\n    pass\n"
        )
        _commit_all(repo, "add old.py with a stale PERF001 waiver")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-waive-rename-3", str(wt)], repo)

        created = new_ticket(
            wt, _spec("Retire stale waiver via rename", scope=("src/old.py",))
        )
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)

        _run(["git", "mv", "src/old.py", "src/new.py"], wt)
        (wt / "src" / "new.py").write_text("def g():\n    pass\n")
        # Left uncommitted, unlike the committed-history test above.

        result = land(repo, tid, wt, dry_run=True)

        assert result.is_ok, result.err


class TestLedgerBothSidesAppend:
    """Incident class 2: main gets a new ticket appended AFTER the worktree
    branched, and the worktree independently appends its own new ticket --
    a textual same-region conflict in tickets.md that must resolve as
    "keep both", not as a real conflict requiring a human."""

    def test_both_sides_append_merges_cleanly(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-g", str(wt)], repo)

        created_wt = new_ticket(
            wt, _spec("Worktree ticket", scope=("src/wt_thing.py",))
        )
        assert created_wt.is_ok
        wt_tid = created_wt.danger_ok.id
        _make_closeable(wt, wt_tid)
        (wt / "src" / "wt_thing.py").write_text("# from worktree\n")
        _commit_all(wt, "worktree ticket + feature")

        # Main independently gains a new ticket AFTER the worktree branched.
        created_main = new_ticket(repo, _spec("Main-side ticket"))
        assert created_main.is_ok
        main_tid = created_main.danger_ok.id
        _commit_all(repo, "main-side ticket")

        result = land(repo, wt_tid, wt, dry_run=False)
        assert result.is_ok, result.err
        final_id = result.danger_ok.final_id

        landed = load_all(repo)
        assert landed.is_ok
        assert final_id in landed.danger_ok
        assert main_tid in landed.danger_ok
        assert landed.danger_ok[final_id].state == TicketState.DONE


class TestDraftFinalizeRewritesCodeAndLeavesWorktreeClean:
    """Reviewer bug 1: `finalize_draft` rewrites tickets.md AND every code
    file carrying a `frob:ticket <draft-id>` directive, uncommitted, in the
    worktree -- but the old `land` squashed from the branch's last commit,
    which predated those rewrites. A landed source file kept the dangling
    draft id, and the worktree was left dirty after a "successful" land.
    `land` must commit finalize/close's changes in the worktree BEFORE the
    squash so both the ledger AND the rewritten code reach main, and the
    worktree ends up clean."""

    def test_code_directive_rewritten_and_worktree_clean_after_land(
        self, repo: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-i", str(wt)], repo)

        created = new_ticket(wt, _spec("Filed off-branch", scope=("src/thing2.py",)))
        assert created.is_ok
        draft_id = created.danger_ok.id
        assert draft_id.startswith("T-draft-")
        _make_closeable(wt, draft_id)
        # A code file carrying a frob:ticket directive naming the DRAFT id --
        # renumber_one (finalize_draft's rename primitive) must rewrite this
        # reference, and that rewrite must actually reach main.
        (wt / "src" / "thing2.py").write_text(
            f"# frob:ticket {draft_id}\ndef f():\n    pass\n"
        )
        _commit_all(wt, "off-branch ticket with a code directive")

        result = land(repo, draft_id, wt, dry_run=False)
        assert result.is_ok, result.err
        report = result.danger_ok
        final_id = report.final_id
        assert final_id != draft_id

        # The landed file on MAIN must carry the FINAL id, never the draft.
        landed_src = (repo / "src" / "thing2.py").read_text()
        assert draft_id not in landed_src
        assert f"frob:ticket {final_id}" in landed_src

        # The worktree must be left completely clean -- finalize/close's
        # writes were committed before the squash, not left dangling.
        wt_status = _run(["git", "status", "--porcelain"], wt).stdout.strip()
        assert wt_status == "", f"worktree left dirty: {wt_status!r}"

        # And the worktree's own copy of the file must ALSO carry the final
        # id (the commit-before-squash fix touches the worktree itself).
        wt_src = (wt / "src" / "thing2.py").read_text()
        assert draft_id not in wt_src
        assert f"frob:ticket {final_id}" in wt_src


class TestDraftFinalizeRewritesRegistryYamlRefs:
    """T-0577: draft finalize at land time (`renumber_one`) used to rewrite
    only `frob:` directive lines -- a registry yaml's `disposition:
    "deferred:<draft-id>"` value (docs/design/registry/*.yaml's grammar,
    `frob.registry._models.parse_disposition`) was left pointing at the
    now-dead draft id, breaking REG003 until a human hand-swapped it (the
    real T-0388/compliance.yaml incident). `_rewrite_registry_references`
    must rewrite these too."""

    def test_registry_yaml_deferred_ref_rewritten_to_final_id(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-yaml", str(wt)], repo)

        # T-0854: the ticket's own scope must cover the registry row it
        # defers to itself -- otherwise T-0854's live-tracker-citation
        # preflight (correctly) refuses to land a ticket while a registry
        # disposition still names it as the reason a compliance gap is
        # open, unless the ticket's own change is what resolves that row.
        created = new_ticket(
            wt,
            _spec(
                "Filed off-branch",
                scope=("src/thing3.py", "docs/design/registry/compliance.yaml"),
            ),
        )
        assert created.is_ok
        draft_id = created.danger_ok.id
        assert draft_id.startswith("T-draft-")
        _make_closeable(wt, draft_id)

        registry_dir = wt / "docs" / "design" / "registry"
        registry_dir.mkdir(parents=True)
        (registry_dir / "compliance.yaml").write_text(
            f'entries:\n  - id: some-check\n    disposition: "deferred:{draft_id}"\n'
        )
        (wt / "src" / "thing3.py").write_text("def f():\n    pass\n")
        _commit_all(wt, "off-branch ticket deferred in a registry yaml")

        result = land(repo, draft_id, wt, dry_run=False)
        assert result.is_ok, result.err
        final_id = result.danger_ok.final_id
        assert final_id != draft_id

        landed_yaml = (
            repo / "docs" / "design" / "registry" / "compliance.yaml"
        ).read_text()
        assert draft_id not in landed_yaml
        assert f'"deferred:{final_id}"' in landed_yaml


# frob:ticket T-1194
# frob:ticket T-1750
class TestArchiveResurrection:
    """Reviewer bug 2: `splice_ledger` only read active tickets.md, never
    tickets-archive.md -- an id archived on main after the branch point
    would survive the ours-union and land back into main's active ledger,
    resurrecting a duplicate-id class a human previously had to resolve by
    hand at merge time (T-0176's own 0bb02cf merge). `land` must never
    reintroduce an already-archived id."""

    # frob:ticket T-1194
    # frob:ticket T-1750
    def test_archived_id_never_resurrected(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land_ledger_merge.py::splice_ledger kind="unit"
        # Seed a ticket that exists (stale, still active) in the worktree's
        # ledger view, then archive it on MAIN after the branch point --
        # simulating a branch whose base predates the archive.
        stale = new_ticket(repo, _spec("Will be archived"))
        assert stale.is_ok
        stale_id = stale.danger_ok.id
        _commit_all(repo, "file the soon-to-be-archived ticket")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-j", str(wt)], repo)

        # Main independently closes and archives it AFTER the worktree
        # branched -- the worktree's tickets.md still has it as active.
        assert transition(repo, stale_id, TicketState.PLANNED).is_ok
        assert transition(repo, stale_id, TicketState.IN_PROGRESS).is_ok
        loaded = load_all(repo)
        stale_ticket = loaded.danger_ok[stale_id]
        stale_ticket = stale_ticket.model_copy(
            update={
                "evidence": ("tests/test_x.py::test_ok",),
                "body": stale_ticket.body + "\n## Done report\n\ndone\n",
            }
        )
        assert write_ticket(repo, stale_ticket).is_ok
        assert transition(repo, stale_id, TicketState.DONE).is_ok
        from frob.tickets import archive

        # T-1750: `wt` is live at this point (deliberately, the scenario
        # this test proves splice safety for) -- force past the new
        # in-flight-worktree refusal to keep exercising splice
        # correctness, the property this test actually checks.
        archived_count = archive(repo, force=True)
        assert archived_count.is_ok and archived_count.danger_ok == 1
        _commit_all(repo, "archive the stale ticket")

        # Now land unrelated worktree work; the worktree's own tickets.md
        # STILL carries stale_id as active (it branched before the archive).
        created = new_ticket(wt, _spec("Unrelated land", scope=("src/unrelated2.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "unrelated2.py").write_text("# unrelated\n")
        _commit_all(wt, "unrelated worktree work")

        result = land(repo, tid, wt, dry_run=False)
        assert result.is_ok, result.err

        active = load_all(repo)
        assert active.is_ok
        assert stale_id not in active.danger_ok, (
            f"{stale_id} resurrected into the active ledger by land"
        )

        archived = load_archive(repo)
        assert archived.is_ok
        assert stale_id in archived.danger_ok
        # Exactly once -- not duplicated across active+archive.
        assert list(load_all(repo).danger_ok).count(stale_id) == 0


# frob:ticket T-0959
# frob:ticket T-1194
# frob:ticket T-1636
# frob:ticket T-1750
class TestArchiveSpliceDiscipline:
    """T-0959: `tickets-archive.md` used to ride along on whatever git's raw
    merge/checkout produced at land time, with no per-id splice discipline
    at all (unlike tickets.md's `_splice_and_stage`) -- a real incident
    (T-0703's land) staged a worktree's STALE tickets-archive.md wholesale,
    wiping 62 blocks a TICK003 sweep had added to main's archive after the
    worktree's own warmup merge. This regression-locks the acceptance
    criterion directly: a worktree whose archive predates a later archive
    sweep on main must never cause `land` to lose main's newly-archived
    blocks."""

    def test_splice_and_stage_archive_merges_by_id_never_overwrites(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land_git_ops.py::_splice_and_stage_archive \
        # kind="unit"
        # `authoritative_text` carries one id, `other_text` carries a
        # DISJOINT second id -- a wholesale overwrite (the pre-T-0959 bug)
        # would keep only one side; the splice must keep both.
        checkout = tmp_path / "checkout"
        _git_init(checkout)
        atomic_write(ledger_path(checkout), "# Tickets\n\n")

        created = new_ticket(checkout, _spec("Authoritative side"))
        assert created.is_ok
        authoritative_text = ledger_path(checkout).read_text()
        authoritative_id = created.danger_ok.id

        other_ticket = created.danger_ok.model_copy(
            update={"id": "T-0002", "title": "Other side"}
        )
        other_dir = tmp_path / "other"
        other_dir.mkdir()
        atomic_write(ledger_path(other_dir), "# Tickets\n\n")
        assert write_ticket(other_dir, other_ticket).is_ok
        other_text = ledger_path(other_dir).read_text()

        result = _splice_and_stage_archive(checkout, authoritative_text, other_text)
        assert result.is_ok, result.err
        merged = archive_path(checkout).read_text()
        assert authoritative_id in merged
        assert "T-0002" in merged
        assert "Authoritative side" in merged
        assert "Other side" in merged

    def test_splice_and_stage_archive_refuses_when_authoritative_id_would_vanish(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/tickets/_land_git_ops.py::_splice_and_stage_archive \
        # kind="unit"
        # The T-0959 id-integrity backstop: if the merge somehow produced a
        # result missing an id `authoritative_text` carried, refuse loudly
        # rather than silently staging a lossy result. Forced by making
        # `_merge_ledger_tickets` itself drop the authoritative id, since a
        # real union merge structurally never does this on its own -- this
        # pins the GUARD, not a naturally-reachable input.
        checkout = tmp_path / "checkout"
        _git_init(checkout)
        atomic_write(ledger_path(checkout), "# Tickets\n\n")

        created = new_ticket(checkout, _spec("Must survive"))
        assert created.is_ok
        authoritative_text = ledger_path(checkout).read_text()
        other_text = "# Tickets\n\n"

        def _drop_everything(
            ours: dict[str, Any], theirs: dict[str, Any], **_kwargs: Any
        ) -> dict[str, Any]:
            return {}

        monkeypatch.setattr(
            _land_git_ops_mod, "_merge_ledger_tickets", _drop_everything
        )

        result = _splice_and_stage_archive(checkout, authoritative_text, other_text)
        assert result.is_err
        assert result.danger_err == LandError.GitFailed

    # frob:ticket T-1750
    def test_land_preserves_mains_newly_archived_blocks_over_a_stale_worktree_archive(
        self, repo: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land_git_ops.py::_splice_and_stage_archive \
        # kind="unit"
        # Two tickets that will be archived on MAIN, AFTER the worktree
        # branches off -- the exact T-0703 incident shape: the worktree's
        # warmup merge happens before the archive sweep, so its own
        # tickets-archive.md never sees it.
        first = new_ticket(repo, _spec("First to archive"))
        second = new_ticket(repo, _spec("Second to archive"))
        assert first.is_ok and second.is_ok
        first_id, second_id = first.danger_ok.id, second.danger_ok.id
        _commit_all(repo, "file two tickets that will later be archived")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-archive-splice", str(wt)], repo)

        # The worktree ALSO independently archives its own sibling ticket
        # (a genuine two-sided divergence on tickets-archive.md, the shape
        # that actually exercises a real merge/splice decision rather than
        # a one-sided fast-forward git can resolve on its own).
        from frob.tickets import archive

        sibling = new_ticket(
            wt, _spec("Sibling archived in worktree", scope=("src/sib.py",))
        )
        assert sibling.is_ok
        sibling_id = sibling.danger_ok.id
        _make_closeable(wt, sibling_id)
        assert transition(wt, sibling_id, TicketState.DONE).is_ok
        # T-1750: `repo` is live from `wt`'s point of view -- force past
        # the new in-flight-worktree refusal (the scenario below is
        # exactly what that guard exists to flag in real operation; this
        # test forces past it deliberately to prove splice correctness).
        wt_archived_count = archive(wt, force=True)
        assert wt_archived_count.is_ok and wt_archived_count.danger_ok == 1
        _commit_all(wt, "worktree archives its own sibling ticket")

        # Main independently closes and archives BOTH tickets AFTER the
        # worktree branched.
        for ticket_id in (first_id, second_id):
            _make_closeable(repo, ticket_id)
            assert transition(repo, ticket_id, TicketState.DONE).is_ok
        archived_count = archive(repo, force=True)
        assert archived_count.is_ok and archived_count.danger_ok == 2
        _commit_all(repo, "archive two tickets (sweep happens after worktree branch)")

        # Confirm the worktree's own archive really is stale at this point
        # -- the precondition the incident needs.
        wt_archive_before = load_archive(wt)
        assert wt_archive_before.is_ok
        assert first_id not in wt_archive_before.danger_ok
        assert second_id not in wt_archive_before.danger_ok

        # Land unrelated worktree work.
        created = new_ticket(
            wt, _spec("Unrelated archive-splice land", scope=("src/unrelated3.py",))
        )
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "unrelated3.py").write_text("# unrelated\n")
        _commit_all(wt, "unrelated worktree work")

        result = land(repo, tid, wt, dry_run=False)
        assert result.is_ok, result.err

        archived = load_archive(repo)
        assert archived.is_ok
        assert first_id in archived.danger_ok, (
            f"{first_id} wiped from tickets-archive.md by land (T-0959)"
        )
        assert second_id in archived.danger_ok, (
            f"{second_id} wiped from tickets-archive.md by land (T-0959)"
        )
        # The worktree's own genuinely new archive addition must not be
        # silently dropped either -- a raw git merge/checkout with no
        # per-id splice discarded this side entirely before the fix.
        assert sibling_id in archived.danger_ok, (
            f"worktree's own archived sibling {sibling_id} was dropped by land (T-0959)"
        )

    # frob:ticket T-1194
    # frob:ticket T-1636
    def test_land_takes_mains_content_edit_over_a_worktree_copy_unchanged_since_branch(
        self, repo: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land_ledger_merge.py::_merge_ledger_tickets \
        # kind="unit"
        # frob:tests src/frob/tickets/_land_ledger_merge.py::_resolve_divergence \
        # kind="integration"
        # T-1636: exercised only through the full `land(..., dry_run=True)`
        # pipeline several call-hops deep, not a direct call a static call-graph can
        # see -- COV006's own kind="integration" trust-at-face-value convention.
        # T-1154 (3rd occurrence of the wrong-side-merge class, see this
        # ticket's own Done report): a ticket archived on BOTH main and the
        # worktree, same state (done) and same richness (both carry a Done
        # report, same evidence count) -- so pre-T-1154, `_newer`'s tier-3
        # fallback ties and arbitrarily picks `theirs` (the worktree side).
        # Main then makes a REAL content edit to its own archived copy (the
        # T-1143 shape: an evidence-path text migration inside the Done
        # report) while the worktree's copy sits untouched since branch --
        # unchanged-since-branch means the worktree made no deliberate edit
        # and has no claim, so main's edit must survive the land, not be
        # silently reverted.
        from frob.tickets import archive

        archived_ticket = new_ticket(
            repo, _spec("Migrated evidence path", scope=("src/parse.py",))
        )
        assert archived_ticket.is_ok
        aid = archived_ticket.danger_ok.id
        _make_closeable(repo, aid)
        assert transition(repo, aid, TicketState.DONE).is_ok
        assert archive(repo).is_ok
        _commit_all(repo, "archive the ticket that will later be content-edited")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-content-edit", str(wt)], repo)
        # The worktree's own copy of the archived block is byte-identical
        # to the merge-base at this point -- it never touches it.
        wt_archive_before = archive_path(wt).read_text()

        # Main makes a real, deliberate content edit to the SAME archived
        # block -- same state, same evidence count (richness tied), only
        # the Done-report text itself changes (the T-1143 shape: an
        # evidence-path migration).
        main_archived = load_archive(repo)
        assert main_archived.is_ok
        edited = main_archived.danger_ok[aid].model_copy(
            update={
                "body": main_archived.danger_ok[aid].body.replace(
                    "evidence attached", "evidence attached (src/parse/mod.py)"
                )
            }
        )
        assert write_archive(repo, {**main_archived.danger_ok, aid: edited}).is_ok
        _commit_all(repo, "main migrates the evidence path inside the archived block")
        assert "src/parse/mod.py" in archive_path(repo).read_text()

        # Land unrelated worktree work -- exercises the real land path's
        # archive splice, not a hand-called unit helper.
        created = new_ticket(
            wt, _spec("Unrelated content-edit land", scope=("src/unrelated4.py",))
        )
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "unrelated4.py").write_text("# unrelated\n")
        _commit_all(wt, "unrelated worktree work")

        result = land(repo, tid, wt, dry_run=False)
        assert result.is_ok, result.err

        post_land_archive = archive_path(repo).read_text()
        assert "src/parse/mod.py" in post_land_archive, (
            f"{aid}: main's evidence-path migration reverted by land "
            "(T-1154 wrong-side-merge regression)"
        )
        assert wt_archive_before != post_land_archive


class TestWipCommit:
    """`_wip_commit` -- uncommitted worktree changes at land time must be
    snapshotted before the merge that follows, both in dry-run (staged then
    unwound) and real (actually committed) mode."""

    def test_dry_run_wip_commits_uncommitted_changes(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-wip-dry", str(wt)], repo)
        created = new_ticket(wt, _spec("Wip dry", scope=("src/wip_dry.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        _commit_all(wt, "wip dry ticket bits")

        # An UNCOMMITTED change present when land() is called.
        (wt / "src" / "wip_dry.py").write_text("# uncommitted at land time\n")

        result = land(repo, tid, wt, dry_run=True)
        assert result.is_ok, result.err
        report = result.danger_ok
        assert report.wip_committed is True

        # Dry run unwinds everything -- the uncommitted change is still
        # sitting uncommitted in the worktree afterward.
        assert _run(["git", "status", "--porcelain"], wt).stdout.strip() != ""

    def test_real_land_wip_commits_uncommitted_changes(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-wip-real", str(wt)], repo)
        created = new_ticket(wt, _spec("Wip real", scope=("src/wip_real.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "wip_real.py").write_text("# committed baseline\n")
        _commit_all(wt, "wip real ticket bits")

        # An UNCOMMITTED change present when land() is called, real run.
        (wt / "src" / "wip_real.py").write_text("# uncommitted change to snapshot\n")

        result = land(repo, tid, wt, dry_run=False)
        assert result.is_ok, result.err
        report = result.danger_ok
        assert report.wip_committed is True

        wt_log = _run(["git", "log", "--oneline"], wt).stdout
        assert "wip: pre-land snapshot" in wt_log

        landed_content = (repo / "src" / "wip_real.py").read_text()
        assert landed_content == "# uncommitted change to snapshot\n"


# frob:ticket T-1184
class TestWipAddIgnoredPathFallback:
    """T-1184: `_wip_add_excluding_frob`'s `:!.frob` pathspec trips git
    2.34.1's "explicitly named ignored path" refusal the moment `.frob` IS
    actually gitignored (the normal real-repo case) -- the fallback
    (add-everything, then unstage `.frob` separately) must reach the same
    end state without ever naming an ignored path in a pathspec."""

    def test_gitignored_frob_falls_back_and_still_lands(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land_git_ops.py::_wip_add_excluding_frob \
        # kind="unit"
        wt = repo.parent / "wt"
        _run(
            ["git", "worktree", "add", "-b", "feature-wip-ignored-frob", str(wt)], repo
        )
        created = new_ticket(wt, _spec("Wip ignored frob", scope=("src/wip_ig.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)

        # `.frob/` is gitignored (the normal real-repo case) -- naming it in
        # a negated pathspec is what trips the T-1184 refusal.
        (wt / ".gitignore").write_text(".frob/\n")
        (wt / "src" / "wip_ig.py").write_text("# committed baseline\n")
        _commit_all(wt, "wip ignored-frob ticket bits")

        # Scratch state under `.frob/` (as `land()`'s own lock/bookkeeping
        # writes leave behind) plus a real uncommitted change to snapshot.
        (wt / ".frob").mkdir(exist_ok=True)
        (wt / ".frob" / "scratch.txt").write_text("frob-local state\n")
        (wt / "src" / "wip_ig.py").write_text("# uncommitted change to snapshot\n")

        result = land(repo, tid, wt, dry_run=False)
        assert result.is_ok, result.err
        report = result.danger_ok
        assert report.wip_committed is True

        wt_log = _run(["git", "log", "--oneline"], wt).stdout
        assert "wip: pre-land snapshot" in wt_log

        landed_content = (repo / "src" / "wip_ig.py").read_text()
        assert landed_content == "# uncommitted change to snapshot\n"

    def test_is_ignored_path_refusal_matches_gits_fixed_message(self) -> None:
        # frob:tests src/frob/tickets/_land_git_ops.py::_is_ignored_path_refusal \
        # kind="unit"
        stderr = (
            "The following paths are ignored by one of your .gitignore files:\n"
            ".frob\nhint: Use -f if you really want to add them.\n"
        )
        assert _land_git_ops_mod._is_ignored_path_refusal(stderr) is True
        assert (
            _land_git_ops_mod._is_ignored_path_refusal("some other git error") is False
        )


class TestWipCommitNormalizationOnlyDirty:
    """T-0847: a worktree that is `_porcelain_dirty` purely because of a
    line-ending normalization status line (WSL/autocrlf phantom-modified)
    must not fail land with `GitFailed` -- `add -A` renormalizes back to the
    identical committed blob, so `git commit` has nothing real to commit and
    used to exit 1 with no stderr, wrongly surfaced as a land failure."""

    def test_normalization_only_dirty_worktree_treated_as_no_op_not_git_failed(
        self, repo: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land_git_ops.py::_do_wip_commit kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-wip-crlf", str(wt)], repo)
        created = new_ticket(wt, _spec("Wip crlf", scope=("src/wip_crlf.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)

        # Force text normalization on this worktree and commit an LF file
        # under it -- the committed blob is normalized LF content.
        _run(["git", "config", "core.autocrlf", "true"], wt)
        (wt / "src" / "wip_crlf.py").write_text("line one\nline two\n")
        _commit_all(wt, "wip crlf ticket bits")

        # Simulate the WSL phantom-dirty symptom: the working-tree file now
        # carries CRLF endings, so `git status --porcelain` reports it
        # modified, but `add -A` will renormalize it right back to the
        # identical committed blob (nothing real to snapshot).
        (wt / "src" / "wip_crlf.py").write_bytes(b"line one\r\nline two\r\n")
        assert _run(["git", "status", "--porcelain"], wt).stdout.strip() != ""

        result = land(repo, tid, wt, dry_run=False)
        assert result.is_ok, result.err
        report = result.danger_ok
        assert report.wip_committed is False

        wt_log = _run(["git", "log", "--oneline"], wt).stdout
        assert "wip: pre-land snapshot" not in wt_log


class TestKindEvidenceMismatch:
    """`_validate_closeable`'s T-0215 kind-consistency guard: a non-docs-kind
    ticket carrying a `cmd:`-shaped evidence entry must never land, mirroring
    the write-time gate in `add_cmd_evidence`."""

    def test_non_docs_kind_with_cmd_evidence_refused(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-kind", str(wt)], repo)
        created = new_ticket(wt, _spec("Feature kind with cmd evidence"))
        assert created.is_ok
        tid = created.danger_ok.id

        loaded = load_all(wt)
        assert loaded.is_ok
        ticket = loaded.danger_ok[tid]
        # FEATURE is not in CMD_EVIDENCE_ALLOWED_KINDS ({DOCS}), but the
        # evidence entry has the exact cmd: shape (as if hand-pasted or the
        # kind was changed after the entry was recorded).
        ticket = ticket.model_copy(
            update={
                "evidence": ("cmd:pytest -q exit=0 sha256=abcdef012345",),
                "body": ticket.body + "\n## Done report\n\ndone\n",
            }
        )
        assert write_ticket(wt, ticket).is_ok
        _commit_all(wt, "feature ticket with cmd evidence")

        result = land(repo, tid, wt, dry_run=True)
        assert result.is_err
        assert result.danger_err == LandError.NotCloseable


class TestUnownedDeletionRealRun:
    """The `_unowned_deletions` abort must behave identically in a real
    (non-dry-run) landing -- main untouched, worktree merge state aborted."""

    def test_unowned_deletion_aborts_on_real_run(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-real-del", str(wt)], repo)

        (wt / "src" / "feature.py").unlink()
        created = new_ticket(
            wt, _spec("Unrelated real ticket", scope=("src/other2.py",))
        )
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        _commit_all(wt, "accidentally delete feature.py, real run")

        before_main_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()

        result = land(repo, tid, wt, dry_run=False)
        assert result.is_err
        assert result.danger_err == LandError.UnownedDeletions

        assert (
            _run(["git", "rev-parse", "HEAD"], repo).stdout.strip() == before_main_sha
        )
        assert (repo / "src" / "feature.py").exists()
        assert _run(["git", "status", "--porcelain"], wt).stdout.strip() == ""


class TestMergeConflictOutsideLedger:
    """`_merge_main_into_worktree` must abort loudly (not silently splice)
    on a real textual conflict in a NON-tickets.md file -- only tickets.md
    is resolved via `splice_ledger`; anything else conflicting must surface
    to a human."""

    def test_real_conflict_outside_tickets_md_aborts(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-conflict", str(wt)], repo)

        # Worktree modifies the SAME line of src/feature.py.
        (wt / "src" / "feature.py").write_text("# worktree-side edit\n")
        created = new_ticket(wt, _spec("Conflicting edit", scope=("src/feature.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        _commit_all(wt, "worktree edits feature.py")

        # Main independently modifies the SAME line, AFTER the worktree
        # branched -- a genuine textual conflict on a non-ticket file.
        (repo / "src" / "feature.py").write_text("# main-side edit\n")
        _commit_all(repo, "main edits feature.py")

        result = land(repo, tid, wt, dry_run=True)
        assert result.is_err
        assert result.danger_err == LandError.MergeConflict

        # _abort_merge must have run -- worktree left exactly as found.
        assert _status_ignoring_frob(wt) == ""


class TestOutOfScopeConflictAutoResolved:
    """T-0479(b): a conflict in a file OUTSIDE the landing ticket's scope
    must auto-resolve to main's side instead of aborting the land."""

    def test_conflict_outside_scope_takes_mains_side_and_lands(
        self, repo: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-oos", str(wt)], repo)

        # Worktree ticket is scoped ONLY to src/other.py; it never legitimately
        # touches feature.py.
        (wt / "src" / "other.py").write_text("worktree change\n")
        (wt / "src" / "feature.py").write_text("# worktree-side unrelated edit\n")
        created = new_ticket(
            wt, _spec("Out of scope conflict", scope=("src/other.py",))
        )
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        _commit_all(wt, "worktree edits other.py and (out of scope) feature.py")

        # Main independently changes the SAME line of feature.py.
        (repo / "src" / "feature.py").write_text("# main-side edit\n")
        _commit_all(repo, "main edits feature.py")

        result = land(repo, tid, wt, dry_run=False)
        assert result.is_ok, result.err
        # Main's side of the out-of-scope conflict won.
        assert (repo / "src" / "feature.py").read_text() == "# main-side edit\n"
        assert (repo / "src" / "other.py").read_text() == "worktree change\n"


# frob:ticket T-1434
class TestCoverageLockConflictMerges:
    """T-1434: `frob-coverage.lock.json` is a coverage-ratchet artifact,
    not an ordinary source file -- a genuine conflict on it (both the
    worktree and main independently stamped coverage since diverging)
    must never blindly discard one side's freshly measured data. Confirms
    the root cause (T-1270's "reverted to an older committed value"
    incident) and its fix: the out-of-scope conflict auto-resolver now
    keeps the elementwise MAX of both sides' `module_line` percentages
    instead of picking one side wholesale."""

    # frob:tests tests/test_ticket_land.py::TestCoverageLockConflictMerges.test_conflicting_lock_merges_to_the_higher_of_both_sides  # noqa: E501
    def test_conflicting_lock_merges_to_the_higher_of_both_sides(
        self, repo: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land_git_ops.py::_merge_coverage_lock_conflict
        wt = repo.parent / "wt-covlock"
        base_lock = {
            "source_sha": "base",
            "module_line": {"src/a.py": 50.0, "src/b.py": 50.0},
        }
        (repo / "frob-coverage.lock.json").write_text(
            json.dumps(base_lock, indent=2, sort_keys=True) + "\n"
        )
        _commit_all(repo, "seed base frob-coverage.lock.json")
        _run(["git", "worktree", "add", "-b", "feature-covlock", str(wt)], repo)

        # Worktree ticket is scoped ONLY to src/other.py -- it never
        # legitimately touches frob-coverage.lock.json, but a local
        # `--stamp-coverage` run (e.g. while investigating a fix) leaves
        # it dirty anyway, with a REAL, freshly measured, higher number
        # for src/a.py that main's own stamp does not have yet.
        (wt / "src" / "other.py").write_text("worktree change\n")
        wt_lock = {
            "source_sha": "worktree-fresh",
            "module_line": {"src/a.py": 95.0, "src/b.py": 50.0},
        }
        (wt / "frob-coverage.lock.json").write_text(
            json.dumps(wt_lock, indent=2, sort_keys=True) + "\n"
        )
        created = new_ticket(
            wt, _spec("Coverage lock conflict", scope=("src/other.py",))
        )
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        _commit_all(wt, "worktree edits other.py and stamps coverage locally")

        # Main independently stamps coverage too, with a higher number
        # for src/b.py the worktree's own stamp does not have.
        main_lock = {
            "source_sha": "main-fresh",
            "module_line": {"src/a.py": 50.0, "src/b.py": 90.0},
        }
        (repo / "frob-coverage.lock.json").write_text(
            json.dumps(main_lock, indent=2, sort_keys=True) + "\n"
        )
        _commit_all(repo, "main stamps coverage independently")

        result = land(repo, tid, wt, dry_run=False)
        assert result.is_ok, result.err

        merged = json.loads((repo / "frob-coverage.lock.json").read_text())
        # Neither side's freshly measured number was silently discarded --
        # the higher of the two survives for every module.
        assert merged["module_line"]["src/a.py"] == 95.0
        assert merged["module_line"]["src/b.py"] == 90.0
        assert (repo / "src" / "other.py").read_text() == "worktree change\n"


class TestLedgerV2LandMergeStory:
    """T-1258: ledger v2's native-git merge story for `frob ticket land` --
    disjoint `tickets/T-####/` directories merge with zero custom
    resolution (AC2), and a genuine same-ticket-file conflict surfaces as
    an ordinary git conflict, never a silent splice (AC3)."""

    def test_disjoint_v2_tickets_land_with_no_custom_merge(self, v2_repo: Path) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = v2_repo.parent / "wt-v2-a"
        _run(["git", "worktree", "add", "-b", "feature-v2-a", str(wt)], v2_repo)

        created = new_ticket(wt, _spec("Add widget v2", scope=("src/widget.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "widget.py").write_text("# new widget\n")
        _commit_all(wt, "add widget v2")

        # Main gains a DIFFERENT ticket's own directory after the worktree
        # branched -- a real merge, disjoint ticket dirs on both sides.
        other = _seed_v2_ticket(v2_repo, "T-3005", scope=("src/other.py",))
        assert other.id == "T-3005"
        _commit_all(v2_repo, "main gains sibling v2 ticket T-3005")

        result = land(v2_repo, tid, wt, dry_run=False)
        assert result.is_ok, result.err
        report = result.danger_ok
        # No monofile splice happened -- there is no monofile in v2 mode.
        assert report.ledger_spliced is False

        landed = load_all(v2_repo)
        assert landed.is_ok
        assert landed.danger_ok[report.final_id].state == TicketState.DONE
        assert "T-3005" in landed.danger_ok
        assert (v2_repo / "tickets" / "T-3005" / "ticket.md").exists()
        assert (v2_repo / "src" / "widget.py").exists()
        assert not (v2_repo / "tickets.md").exists()

    def test_same_ticket_conflict_surfaces_loudly_no_splice(
        self, v2_repo: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = v2_repo.parent / "wt-v2-b"
        _run(["git", "worktree", "add", "-b", "feature-v2-b", str(wt)], v2_repo)

        # Worktree finalizes T-3000 AND retitles it as part of the same edit.
        _make_closeable(wt, "T-3000")
        wt_ticket = load_all(wt).danger_ok["T-3000"]
        assert write_ticket(
            wt, wt_ticket.model_copy(update={"title": "Renamed by worktree"})
        ).is_ok
        _commit_all(wt, "worktree finalizes and retitles T-3000")

        # Main independently retitles the SAME ticket's SAME field, after
        # the branch point -- a genuine same-line textual conflict on
        # tickets/T-3000/ticket.md.
        main_ticket = load_all(v2_repo).danger_ok["T-3000"]
        assert write_ticket(
            v2_repo, main_ticket.model_copy(update={"title": "Renamed by main"})
        ).is_ok
        _commit_all(v2_repo, "main retitles T-3000")

        result = land(v2_repo, "T-3000", wt, dry_run=True)
        assert result.is_err
        assert result.danger_err == LandError.MergeConflict

        # Refused loudly, not silently spliced -- the merge attempt is
        # cleanly aborted, worktree left exactly as found.
        assert _status_ignoring_frob(wt) == ""


class TestDraftIdFinalization:
    """Incident class 3: a ticket filed off the default branch got a
    provisional T-draft-<hex> id; landing must finalize it to a real
    sequential id (T-0162's promised mechanism) before closing."""

    def test_draft_id_finalized_on_land(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-h", str(wt)], repo)

        # A worktree is, by definition, off the default branch -- new_ticket
        # mints a draft id here unconditionally.
        created = new_ticket(wt, _spec("Filed off-branch", scope=("src/thing.py",)))
        assert created.is_ok
        draft_id = created.danger_ok.id
        assert draft_id.startswith("T-draft-")
        _make_closeable(wt, draft_id)
        (wt / "src" / "thing.py").write_text("# thing\n")
        _commit_all(wt, "off-branch ticket")

        result = land(repo, draft_id, wt, dry_run=False)
        assert result.is_ok, result.err
        report = result.danger_ok
        assert report.final_id != draft_id
        assert not report.final_id.startswith("T-draft-")

        landed = load_all(repo)
        assert landed.is_ok
        assert draft_id not in landed.danger_ok
        assert report.final_id in landed.danger_ok
        assert landed.danger_ok[report.final_id].state == TicketState.DONE


# frob:ticket T-0637
class TestStandaloneSiblingDraftSurvivesLand:
    """T-0637 field incident: a worktree's ledger held a REAL ticket being
    landed AND a completely separate, standalone draft ticket (filed via
    `frob ticket new` mid-session, `frob:new`'s own scope-cut discovery --
    the T-0575/T-draft-3d5f6965 and T-0576's two-draft shapes). Before this
    fix, the sibling draft block was silently dropped by the land splice
    (never carried forward, since it was neither the ticket being landed
    nor already present on main) -- it must survive and land with a real,
    finalized id."""

    def test_sibling_draft_ticket_finalized_and_lands_alongside(
        self, repo: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-j", str(wt)], repo)

        # The ticket actually being landed.
        primary = new_ticket(wt, _spec("Primary landed work", scope=("src/main3.py",)))
        assert primary.is_ok
        primary_id = primary.danger_ok.id
        assert primary_id.startswith("T-draft-")
        _make_closeable(wt, primary_id)
        (wt / "src" / "main3.py").write_text("# primary work\n")

        # A STANDALONE sibling, filed while working the primary ticket,
        # left QUEUED -- never touched again, never landed on its own.
        sibling = new_ticket(
            wt, _spec("Found while working the primary ticket", scope=("src/sib.py",))
        )
        assert sibling.is_ok
        sibling_draft_id = sibling.danger_ok.id
        assert sibling_draft_id.startswith("T-draft-")
        assert sibling_draft_id != primary_id

        _commit_all(wt, "primary work plus a standalone sibling draft ticket")

        result = land(repo, primary_id, wt, dry_run=False)
        assert result.is_ok, result.err
        report = result.danger_ok

        landed = load_all(repo)
        assert landed.is_ok
        landed_map = landed.danger_ok

        # The sibling draft must NOT have vanished, and must NOT still
        # carry a draft id on main (T-0162: drafts never persist there).
        assert sibling_draft_id not in landed_map, (
            "sibling draft id should have been finalized away, not landed verbatim"
        )
        finalized_siblings = [
            tid
            for tid, t in landed_map.items()
            if t.title == "Found while working the primary ticket"
        ]
        assert finalized_siblings, "standalone sibling draft ticket was dropped at land"
        assert len(finalized_siblings) == 1
        sibling_final_id = finalized_siblings[0]
        assert not sibling_final_id.startswith("T-draft-")
        assert sibling_final_id != report.final_id

        # It survives in whatever state it was left in (QUEUED) -- landing
        # the PRIMARY ticket must not itself close/alter the sibling.
        assert landed_map[sibling_final_id].state == TicketState.QUEUED
        assert landed_map[report.final_id].state == TicketState.DONE


class TestDraftReferenceRewriteOnLand:
    """T-0811: land renumbers a finalized draft's structural id fields, but
    before this fix left Done-report PROSE citing the old draft id
    untouched, so TICK006's phantom-filing-claim gate reds main the
    moment the draft finalizes to a real id (recurred 3x this drive:
    T-0778/T-0797, T-0745/T-0764). A land whose own Done report cites its
    own (pre-finalize) draft id must come out with that reference rewritten
    to the final id, and zero `T-draft-` ids left anywhere in the ledger."""

    def test_land_rewrites_own_draft_id_reference_in_done_report(
        self, repo: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-k", str(wt)], repo)

        primary = new_ticket(
            wt, _spec("Self-citing draft work", scope=("src/self.py",))
        )
        assert primary.is_ok
        primary_id = primary.danger_ok.id
        assert primary_id.startswith("T-draft-")
        (wt / "src" / "self.py").write_text("# self-citing draft work\n")

        assert transition(wt, primary_id, TicketState.PLANNED).is_ok
        assert transition(wt, primary_id, TicketState.IN_PROGRESS).is_ok
        loaded = load_all(wt)
        ticket = loaded.danger_ok[primary_id]
        ticket = ticket.model_copy(
            update={
                "evidence": ("tests/test_x.py::test_ok",),
                "body": (
                    ticket.body
                    + "\n## Done report\n\nevidence attached\n"
                    + f"Filed: {primary_id} (scope-cut note filed against self)\n"
                ),
            }
        )
        assert write_ticket(wt, ticket).is_ok

        _commit_all(wt, "self-citing draft work")

        result = land(repo, primary_id, wt, dry_run=False)
        assert result.is_ok, result.err
        report = result.danger_ok
        final_id = report.final_id
        assert final_id != primary_id

        landed = load_all(repo)
        assert landed.is_ok
        landed_map = landed.danger_ok
        assert primary_id not in landed_map

        final_ticket = landed_map[final_id]
        assert primary_id not in final_ticket.body, (
            "stale draft-id reference survived in the landed Done report"
        )
        assert f"Filed: {final_id}" in final_ticket.body

        ledger_text = ledger_path(repo).read_text(encoding="utf-8")
        assert "T-draft-" not in ledger_text, (
            "a T-draft- id survived somewhere in the landed ledger text"
        )

    # frob:ticket T-1622
    def test_land_rewrites_a_sibling_drafts_citation_in_the_primary_done_report(
        self, repo: Path
    ) -> None:
        """T-1622's exact real-world shape: an agent, mid-work on its
        assigned ticket, discovers follow-up work and files it via `frob
        ticket new` (which mints a draft id off-branch) -- then cites that
        DIFFERENT ticket's draft id in ITS OWN Done report's "Filed: ..."
        line, never editing the sibling's own body at all. `_land_
        rewrite_draft_references_in_bodies` is called with the FULL
        `draft_id_mapping` (primary + every finalized sibling,
        `_land_finalize_and_close`'s `draft_id_mapping.update(siblings_
        finalized...)`), so this citation must be rewritten too -- proving
        the land alone (no draft/finalize round-trip left for a human,
        no hand-edited citation anywhere) satisfies T-1622's acceptance:
        an agent files a follow-up from a worktree, lands its work, and
        nobody touches the ledger by hand for the citation to be correct
        on main."""
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-t1622", str(wt)], repo)

        primary = new_ticket(
            wt, _spec("Primary work citing a sibling", scope=("src/primary622.py",))
        )
        assert primary.is_ok
        primary_id = primary.danger_ok.id
        assert primary_id.startswith("T-draft-")
        (wt / "src" / "primary622.py").write_text("# primary work\n")

        # The follow-up, discovered mid-work, filed as its own standalone
        # ticket -- left QUEUED, exactly like a real residue filing.
        sibling = new_ticket(
            wt, _spec("Follow-up discovered mid-work", scope=("src/sib622.py",))
        )
        assert sibling.is_ok
        sibling_draft_id = sibling.danger_ok.id
        assert sibling_draft_id.startswith("T-draft-")
        assert sibling_draft_id != primary_id

        _make_closeable(wt, primary_id)
        loaded = load_all(wt)
        ticket = loaded.danger_ok[primary_id]
        ticket = ticket.model_copy(
            update={
                "body": (
                    ticket.body
                    + f"\nFiled: {sibling_draft_id} (follow-up, out of scope)\n"
                )
            }
        )
        assert write_ticket(wt, ticket).is_ok
        _commit_all(wt, "primary work citing a standalone sibling draft")

        result = land(repo, primary_id, wt, dry_run=False)
        assert result.is_ok, result.err
        report = result.danger_ok
        final_id = report.final_id

        landed = load_all(repo)
        assert landed.is_ok
        landed_map = landed.danger_ok

        # The sibling must have been promoted to a real id alongside the
        # primary -- never left as a draft, never dropped.
        assert sibling_draft_id not in landed_map
        finalized_siblings = [
            tid
            for tid, t in landed_map.items()
            if t.title == "Follow-up discovered mid-work"
        ]
        assert finalized_siblings, "sibling draft ticket was dropped at land"
        sibling_final_id = finalized_siblings[0]
        assert not sibling_final_id.startswith("T-draft-")

        # And the PRIMARY's own Done report -- a DIFFERENT ticket's body
        # than the sibling's -- must cite the sibling's REAL final id, not
        # its now-defunct draft id, with no human intervention.
        final_body = landed_map[final_id].body
        assert sibling_draft_id not in final_body, (
            "primary's Done report still cites the sibling's dead draft id "
            "-- this is the exact toil T-1622 exists to eliminate"
        )
        assert f"Filed: {sibling_final_id}" in final_body

        ledger_text = ledger_path(repo).read_text(encoding="utf-8")
        assert "T-draft-" not in ledger_text

    def test_land_rewrites_strata_waive_clause_draft_id_reference(
        self, repo: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        # T-0812: extends the T-0811 body-prose rewrite to a `design/*.
        # strata` `waive` clause citing the SAME draft id being finalized
        # -- the original T-draft-8cd37914 incident class WAIVE007's
        # T-draft-* exemption otherwise leaves dangling forever.
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-strata", str(wt)], repo)

        primary = new_ticket(
            wt, _spec("Strata-citing draft work", scope=("src/strata_ref.py",))
        )
        assert primary.is_ok
        primary_id = primary.danger_ok.id
        assert primary_id.startswith("T-draft-")
        (wt / "src" / "strata_ref.py").write_text("# strata-citing draft work\n")

        design_dir = wt / "design"
        design_dir.mkdir(parents=True, exist_ok=True)
        (design_dir / "waivers.strata").write_text(
            "component demo {\n"
            f'    waive "SYS203:demo" reason "draft waiver" ticket "{primary_id}";\n'
            "}\n"
        )

        assert transition(wt, primary_id, TicketState.PLANNED).is_ok
        assert transition(wt, primary_id, TicketState.IN_PROGRESS).is_ok
        loaded = load_all(wt)
        ticket = loaded.danger_ok[primary_id]
        ticket = ticket.model_copy(
            update={
                "evidence": ("tests/test_x.py::test_ok",),
                "body": ticket.body + "\n## Done report\n\nevidence attached\n",
            }
        )
        assert write_ticket(wt, ticket).is_ok

        _commit_all(wt, "strata-citing draft work")

        result = land(repo, primary_id, wt, dry_run=False)
        assert result.is_ok, result.err
        final_id = result.danger_ok.final_id
        assert final_id != primary_id

        strata_text = (repo / "design" / "waivers.strata").read_text(encoding="utf-8")
        assert primary_id not in strata_text, (
            "stale draft-id reference survived in the landed .strata waive clause"
        )
        assert f'ticket "{final_id}"' in strata_text

    def test_land_rewrites_frob_waive_comment_draft_id_reference(
        self, repo: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        # T-0812: same rewrite, source `frob:waive ... ticket=` comment
        # channel rather than `.strata`.
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-waivecomment", str(wt)], repo)

        primary = new_ticket(
            wt, _spec("Comment-citing draft work", scope=("src/waive_ref.py",))
        )
        assert primary.is_ok
        primary_id = primary.danger_ok.id
        assert primary_id.startswith("T-draft-")
        (wt / "src" / "waive_ref.py").write_text(
            "x = 1  # noqa: E501\n"
            f'# frob:waive DEMO001 reason="draft waiver" ticket={primary_id}\n'
        )

        assert transition(wt, primary_id, TicketState.PLANNED).is_ok
        assert transition(wt, primary_id, TicketState.IN_PROGRESS).is_ok
        loaded = load_all(wt)
        ticket = loaded.danger_ok[primary_id]
        ticket = ticket.model_copy(
            update={
                "evidence": ("tests/test_x.py::test_ok",),
                "body": ticket.body + "\n## Done report\n\nevidence attached\n",
            }
        )
        assert write_ticket(wt, ticket).is_ok

        _commit_all(wt, "comment-citing draft work")

        result = land(repo, primary_id, wt, dry_run=False)
        assert result.is_ok, result.err
        final_id = result.danger_ok.final_id
        assert final_id != primary_id

        comment_text = (repo / "src" / "waive_ref.py").read_text(encoding="utf-8")
        assert primary_id not in comment_text, (
            "stale draft-id reference survived in the landed frob:waive comment"
        )
        assert f"ticket={final_id}" in comment_text

    def test_land_leaves_unrelated_draft_id_reference_untouched(
        self, repo: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        # T-0812 (reviewer follow-up on T-0811): the rewrite must be
        # per-id-keyed against the actual old->new mapping, not a blanket
        # "strip every T-draft- token" pass -- an UNRELATED draft id
        # mentioned in ledger prose (one that is not itself being
        # finalized by this land) must survive verbatim. Kept as its own
        # test since planting an unrelated draft id conflicts with the
        # existing blanket "zero T-draft- ids left in the ledger"
        # assertion in test_land_rewrites_own_draft_id_reference_in_done_report.
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-unrelated", str(wt)], repo)

        primary = new_ticket(
            wt, _spec("Primary work", scope=("src/unrelated_primary.py",))
        )
        assert primary.is_ok
        primary_id = primary.danger_ok.id
        assert primary_id.startswith("T-draft-")
        (wt / "src" / "unrelated_primary.py").write_text("# primary work\n")

        unrelated_draft_id = "T-draft-deadbeef"
        assert unrelated_draft_id != primary_id

        assert transition(wt, primary_id, TicketState.PLANNED).is_ok
        assert transition(wt, primary_id, TicketState.IN_PROGRESS).is_ok
        loaded = load_all(wt)
        ticket = loaded.danger_ok[primary_id]
        ticket = ticket.model_copy(
            update={
                "evidence": ("tests/test_x.py::test_ok",),
                "body": (
                    ticket.body
                    + "\n## Done report\n\nevidence attached\n"
                    + f"Note: unrelated to {unrelated_draft_id}, not landing it\n"
                ),
            }
        )
        assert write_ticket(wt, ticket).is_ok

        _commit_all(wt, "primary work citing an unrelated draft id in prose")

        result = land(repo, primary_id, wt, dry_run=False)
        assert result.is_ok, result.err
        final_id = result.danger_ok.final_id
        assert final_id != primary_id

        landed = load_all(repo)
        assert landed.is_ok
        final_ticket = landed.danger_ok[final_id]
        assert unrelated_draft_id in final_ticket.body, (
            "unrelated draft id in prose was rewritten/stripped -- the "
            "substitution must be scoped to this land's own old->new "
            "mapping, not a blanket T-draft- removal"
        )


class TestLandNotFound:
    """`land` on a ticket id the worktree's store has never heard of."""

    def test_unknown_ticket_id_returns_not_found(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-nf", str(wt)], repo)

        result = land(repo, "T-9999", wt, dry_run=True)
        assert result.is_err
        assert result.danger_err == LandError.NotFound


class TestGitSubprocessFailures:
    """`land`'s own git-failure early returns -- each wraps a `run_argv`
    call whose failure is otherwise only reachable via a real, hard-to-
    reproduce environment fault (permission denial, disk full, a corrupted
    ref). Deterministically forced here via `_failing_run_argv` patching
    the module's single `run_argv` import point."""

    def test_main_dirty_check_git_failure(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-l1", str(wt)], repo)
        created = new_ticket(wt, _spec("Whatever"))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        _commit_all(wt, "wip")

        _failing_run_argv(
            monkeypatch,
            lambda argv: str(repo) in argv and "status" in argv,
            hard_err=True,
        )
        result = land(repo, tid, wt, dry_run=True)
        assert result.is_err
        assert result.danger_err == LandError.GitFailed

    def test_main_branch_lookup_failure(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-l2", str(wt)], repo)
        created = new_ticket(wt, _spec("Whatever"))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        _commit_all(wt, "wip")

        # `current_branch` (frob.gitio) has its own internal `run_argv`
        # reference, independent of the one `_land.py` imports -- patch the
        # symbol `_land.py` calls directly rather than the git subprocess
        # layer, to exercise `land`'s own `main_branch.is_err` branch.
        def _fail(root: Path) -> Any:
            return Err(GitError.GitFailed)

        monkeypatch.setattr(_land_mod, "current_branch", _fail)
        result = land(repo, tid, wt, dry_run=True)
        assert result.is_err
        assert result.danger_err == LandError.GitFailed

    def test_wip_commit_status_check_failure(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-l3", str(wt)], repo)
        created = new_ticket(wt, _spec("Whatever"))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        _commit_all(wt, "wip")

        _failing_run_argv(
            monkeypatch,
            lambda argv: str(wt) in argv and "status" in argv,
            hard_err=True,
        )
        result = land(repo, tid, wt, dry_run=True)
        assert result.is_err
        assert result.danger_err == LandError.GitFailed

    def test_merge_command_failure(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-l4", str(wt)], repo)
        created = new_ticket(wt, _spec("Whatever"))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        _commit_all(wt, "wip")
        (repo / "src" / "extra.py").write_text("# extra main commit\n")
        _commit_all(repo, "main moves on")

        _failing_run_argv(
            monkeypatch,
            lambda argv: str(wt) in argv and "merge" in argv,
            hard_err=True,
        )
        result = land(repo, tid, wt, dry_run=True)
        assert result.is_err
        assert result.danger_err == LandError.GitFailed

    def test_unowned_deletions_diff_failure_after_merge(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-l5", str(wt)], repo)
        created = new_ticket(wt, _spec("Whatever", scope=("src/l5.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "l5.py").write_text("# l5\n")
        _commit_all(wt, "wip")
        (repo / "src" / "extra2.py").write_text("# extra main commit\n")
        _commit_all(repo, "main moves on")

        _failing_run_argv(
            monkeypatch,
            lambda argv: (
                str(wt) in argv and "diff" in argv and "--diff-filter=D" in argv
            ),
            hard_err=True,
        )
        result = land(repo, tid, wt, dry_run=True)
        assert result.is_err
        assert result.danger_err == LandError.GitFailed
        # The merge that already landed in the worktree must have been
        # aborted -- no half-applied merge state left behind. Mutation
        # evidence's own derived_state_lock legitimately leaves
        # `.frob/derived.lock` behind (same scratch-artifact class as
        # `.frob/land.lock`, T-0577) -- filter `.frob/` like every other
        # such assertion in this file.
        assert _status_ignoring_frob(wt) == ""

    def test_squash_command_failure(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-l6", str(wt)], repo)
        created = new_ticket(wt, _spec("Whatever", scope=("src/l6.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "l6.py").write_text("# l6\n")
        _commit_all(wt, "wip")

        _failing_run_argv(
            monkeypatch,
            lambda argv: str(repo) in argv and "--squash" in argv,
            hard_err=True,
        )
        result = land(repo, tid, wt, dry_run=False)
        assert result.is_err
        assert result.danger_err == LandError.GitFailed

    def test_final_commit_failure(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-l7", str(wt)], repo)
        created = new_ticket(wt, _spec("Whatever", scope=("src/l7.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "l7.py").write_text("# l7\n")
        _commit_all(wt, "wip")

        _failing_run_argv(
            monkeypatch,
            lambda argv: (
                str(repo) in argv and "commit" in argv and "--squash" not in argv
            ),
            hard_err=True,
        )
        result = land(repo, tid, wt, dry_run=False)
        assert result.is_err
        assert result.danger_err == LandError.CommitFailed


class TestLandDeeperBranches:
    """Additional `land`-body branches unreachable via ordinary happy/error
    fixture paths: the post-merge commit and finalize/close git-failure
    branches, each forced deterministically via monkeypatch since a real
    reproduction (disk full, permission denial mid-land) is impractical to
    fixture."""

    def test_unowned_deletion_real_run_with_actual_merge(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-l8", str(wt)], repo)

        (wt / "src" / "feature.py").unlink()
        created = new_ticket(wt, _spec("Unrelated", scope=("src/other8.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        _commit_all(wt, "accidentally delete feature.py")

        # Main gains a commit AFTER the worktree branched, so merging main
        # into the worktree is a REAL merge (did_merge=True), not a no-op --
        # exercising the `if did_merge: _abort_merge(...)` branch under the
        # unowned-deletion abort, in a real (non-dry-run) land.
        (repo / "src" / "unrelated8.py").write_text("# unrelated main commit\n")
        _commit_all(repo, "unrelated main-side commit")

        result = land(repo, tid, wt, dry_run=False)
        assert result.is_err
        assert result.danger_err == LandError.UnownedDeletions
        assert _run(["git", "status", "--porcelain"], wt).stdout.strip() == ""
        assert (repo / "src" / "feature.py").exists()

    def test_post_merge_commit_failure(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-l9", str(wt)], repo)
        created = new_ticket(wt, _spec("Whatever", scope=("src/l9.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "l9.py").write_text("# l9\n")
        _commit_all(wt, "wip")

        (repo / "src" / "unrelated9.py").write_text("# unrelated main commit\n")
        _commit_all(repo, "unrelated main-side commit")

        _failing_run_argv(
            monkeypatch,
            lambda argv: (
                str(wt) in argv
                and "commit" in argv
                and any("merge" in a and "landing" in a for a in argv)
            ),
            hard_err=True,
        )
        result = land(repo, tid, wt, dry_run=False)
        assert result.is_err
        assert result.danger_err == LandError.GitFailed

    def test_finalize_draft_failure(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        import frob.tickets as tickets_mod

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-l10", str(wt)], repo)
        created = new_ticket(wt, _spec("Filed off-branch", scope=("src/l10.py",)))
        assert created.is_ok
        draft_id = created.danger_ok.id
        assert draft_id.startswith("T-draft-")
        _make_closeable(wt, draft_id)
        (wt / "src" / "l10.py").write_text("# l10\n")
        _commit_all(wt, "off-branch ticket")

        from frob.tickets._models import TicketError

        # T-1179: land's own finalize step routes through
        # `finalize_draft_for_land` (main-fresh id ceiling), not plain
        # `finalize_draft` -- patch the symbol land actually calls.
        monkeypatch.setattr(
            tickets_mod,
            "finalize_draft_for_land",
            lambda *a, **k: Err(TicketError.NotFound),
        )
        result = land(repo, draft_id, wt, dry_run=False)
        assert result.is_err
        assert result.danger_err == LandError.GitFailed

    def test_worktree_branch_lookup_failure_after_close(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-l11", str(wt)], repo)
        created = new_ticket(wt, _spec("Whatever", scope=("src/l11.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "l11.py").write_text("# l11\n")
        _commit_all(wt, "wip")

        # T-1186: the worktree's own branch lookup this test targets lives
        # in `_land_finalize._land_squash_apply` now, not `_land.py`'s
        # `current_branch(root)` (that call is the MAIN repo's branch,
        # always `repo` here -- never `wt`).
        real_current_branch = _land_squash_mod.current_branch

        def _fake(root: Path) -> Any:
            if str(root) == str(wt):
                return Err(GitError.GitFailed)
            return real_current_branch(root)

        monkeypatch.setattr(_land_squash_mod, "current_branch", _fake)
        result = land(repo, tid, wt, dry_run=False)
        assert result.is_err
        assert result.danger_err == LandError.GitFailed


class TestPreworkSweepRefresh:
    """T-0236: an unrelated main landing that touches a ticket's scope globs
    moves its recorded pre-work sweep's scope digest out from under it --
    three consecutive reviews (T-0181, T-0203, T-0202) REJECTed solely or
    partly on this stale-PRE001 churn. `land` must refresh the sweep
    post-merge, pre-close so a ticket left in-progress after a landing
    failure (or a reviewer's `frob check --ticket` run in the interim)
    never sees a sweep stale for a reason outside the ticket's own control."""

    def test_land_refreshes_stale_sweep_after_unrelated_main_change(
        self, repo: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::_refresh_prework_sweep kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-sweep", str(wt)], repo)

        created = new_ticket(wt, _spec("Sweep refresh", scope=("src/feature.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)

        # Record a deliberately stale sweep -- this mirrors what `frob
        # ticket start` recorded before main moved.
        stale = PreworkSweep(
            date=date.today(), dup_findings=0, xref_hits=(), digest="stale-digest"
        )
        assert record_prework(wt, tid, stale).is_ok

        # main lands an UNRELATED commit that happens to touch the ticket's
        # scoped file -- the drift class this ticket is about.
        (repo / "src" / "feature.py").write_text("# landed feature, updated\n")
        _commit_all(repo, "unrelated main-side edit to a scope-owned file")

        result = land(repo, tid, wt, dry_run=False)
        assert result.is_ok, result.err

        # The sweep recorded in the worktree during land's post-merge,
        # pre-close refresh must reflect the POST-merge tree, not the stale
        # one recorded before `land` ran.
        refreshed = load_prework(wt, tid)
        assert refreshed is not None
        assert refreshed.digest != "stale-digest"

        graph = build_graph(wt, wt / ".frob" / "cache.db")
        assert graph.is_ok
        assert refreshed.digest == scope_digest(("src/feature.py",), graph.danger_ok)

    def test_sweep_refresh_failure_does_not_block_landing(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::_refresh_prework_sweep kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-sweep-fail", str(wt)], repo)

        created = new_ticket(wt, _spec("Sweep refresh failure", scope=("src/x.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "x.py").write_text("# x\n")
        _commit_all(wt, "add x")

        import frob.gates as gates_mod
        from frob.gates._models import GateError

        monkeypatch.setattr(
            gates_mod, "sweep_ticket", lambda *a, **k: Err(GateError.WriteFailed)
        )

        # `land` must still succeed -- the sweep refresh is best-effort and
        # is not what gates landing (close's own evidence/Done-report checks
        # are).
        result = land(repo, tid, wt, dry_run=False)
        assert result.is_ok, result.err


class TestLandCompleteness:
    """T-0463: `land` must bring the worktree's COMPLETE changeset (tracked
    edits + untracked new files + deletions), not just what a `git diff
    HEAD` patch would see, and must assert this BEFORE committing -- the
    root cause of the T-0448 `docs/modules/render.md` loss was a surgical
    git-diff/patch land that silently dropped an untracked file with no
    error."""

    def test_land_brings_tracked_edit_untracked_new_file_and_deletion(
        self, repo: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land_squash.py::_assert_land_complete kind="unit"
        # frob:tests src/frob/tickets/_land_squash.py::_worktree_full_changeset \
        # kind="unit"
        # `doomed.py` must exist BEFORE the worktree branches, so its
        # deletion has a real net effect relative to main (a file created
        # and deleted within the same branch history nets to "no change"
        # against main and would not exercise the deletion path at all).
        (repo / "src" / "doomed.py").write_text("# present before branch\n")
        _commit_all(repo, "add doomed.py (present before branch)")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-complete", str(wt)], repo)
        created = new_ticket(
            wt,
            _spec(
                "Complete changeset",
                scope=("src/feature.py", "src/brand_new.py", "src/doomed.py"),
            ),
        )
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)

        # (a) a tracked EDIT to a file main already has. (b) an uncommitted
        # DELETION of a file main already has -- exercises the wip-commit's
        # `git add -A` staging a deletion.
        (wt / "src" / "feature.py").write_text("# tracked edit\n")
        (wt / "src" / "doomed.py").unlink()

        # (c) an UNTRACKED new file, left uncommitted at land time -- the
        # exact T-0448 incident class.
        (wt / "src" / "brand_new.py").write_text("# brand new, never committed\n")

        result = land(repo, tid, wt, dry_run=False)
        assert result.is_ok, result.err
        report = result.danger_ok

        assert (repo / "src" / "feature.py").read_text() == "# tracked edit\n"
        assert (repo / "src" / "brand_new.py").exists()
        assert not (repo / "src" / "doomed.py").exists()

        # The completeness assertion actually ran and saw all three paths,
        # and every one of them landed in the final commit.
        assert "src/feature.py" in report.worktree_changeset
        assert "src/brand_new.py" in report.worktree_changeset
        assert "src/doomed.py" in report.worktree_changeset
        for path in report.worktree_changeset:
            assert path in report.files_changed

    def test_incomplete_land_fails_loudly_and_commits_nothing(
        self,
        repo: Path,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        # frob:tests src/frob/tickets/_land_squash.py::_assert_land_complete kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-incomplete", str(wt)], repo)
        created = new_ticket(wt, _spec("Incomplete", scope=("src/gadget2.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "gadget2.py").write_text("# gadget2\n")
        _commit_all(wt, "add gadget2")

        before_main_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()

        # Simulate a dropped file: the worktree "changed" a path the
        # squash-apply never actually staged (the T-0448 incident, forced
        # deterministically instead of relying on a real patch-based land
        # to reproduce it).
        real_changeset = _land_squash_mod._worktree_full_changeset

        def _fake_changeset(worktree: Path, main_branch_name: str) -> Any:
            result = real_changeset(worktree, main_branch_name)
            if result.is_err:
                return result
            return Ok(result.danger_ok | {"src/phantom_dropped.py"})

        monkeypatch.setattr(
            _land_squash_mod, "_worktree_full_changeset", _fake_changeset
        )

        with caplog.at_level("ERROR", logger="frob.tickets._land"):
            result = land(repo, tid, wt, dry_run=False)

        assert result.is_err
        assert result.danger_err == LandError.IncompleteLand
        assert "src/phantom_dropped.py" in caplog.text

        # The commit must never have happened, and the squash must have
        # been fully unwound -- root is exactly as found, not partially
        # staged or partially committed.
        assert (
            _run(["git", "rev-parse", "HEAD"], repo).stdout.strip() == before_main_sha
        )
        assert _run(["git", "status", "--porcelain"], repo).stdout.strip() == ""

    def test_worktree_pointed_at_same_branch_as_main_is_refused_not_silently_empty(
        self, repo: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land_squash.py::_worktree_full_changeset \
        # kind="unit"
        # frob:tests src/frob/tickets/_land_git_ops.py::_true_merge_base kind="unit"
        """T-0761 regression: the real T-0640 incident. `land()` was invoked
        with `--worktree` pointing at the SAME checkout/branch `root` had
        checked out -- no distinct feature branch was ever created. A NEW
        source file was added and committed directly on that shared branch
        (mirroring the incident's `src/frob/strata/_reliability.py`), then
        `land(repo, tid, repo)` ran.

        Before the T-0761 fix, this landed "successfully": the merge/squash
        steps against `worktree`'s own branch were git no-ops (a branch
        merged/squashed into itself), so the T-0463 completeness assertion's
        `expected` changeset came back EMPTY and passed vacuously -- only the
        version-bump/ledger-splice writes ended up in the final commit, and
        `new_feature.py` was silently dropped even though `frob ticket land`
        reported success. After the fix, `land` must refuse with
        `IncompleteLand` (a completeness error) rather than commit a
        changeset that drops the new file -- the ticket's acceptance
        criterion's second branch."""
        (repo / "src" / "new_feature.py").write_text("# brand new feature code\n")
        _commit_all(repo, "add new_feature.py directly on the shared branch")

        created = new_ticket(
            repo, _spec("Same-branch land", scope=("src/new_feature.py",))
        )
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(repo, tid)
        _commit_all(repo, "close ticket state directly on the shared branch")

        result = land(repo, tid, repo, dry_run=False)

        assert result.is_err
        assert result.danger_err == LandError.IncompleteLand

        # Refused, not silently landed: no "land T-XXXX" squash-apply commit
        # (the false-green signature -- version bump + ledger only) was ever
        # made, the squash-stage was unwound cleanly, and `new_feature.py`'s
        # content is exactly what was committed above -- nothing was dropped
        # by an incomplete commit.
        log = _run(["git", "log", "--oneline"], repo).stdout
        assert "land " not in log
        assert _status_ignoring_frob(repo) == ""
        assert (repo / "src" / "new_feature.py").read_text() == (
            "# brand new feature code\n"
        )


# frob:ticket T-0338
class TestReleaseBump:
    """T-0338: `land`'s optional `bump_version` callback -- the REL001
    version-bump/stamp coordinator step folded into `land` itself."""

    def test_bump_applied_and_reported(self, repo: Path) -> None:
        # frob:tests \
        # tests/test_ticket_land.py::TestReleaseBump.test_bump_applied_and_reported
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-bump", str(wt)], repo)
        created = new_ticket(wt, _spec("Bump me", scope=("src/bumped.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "bumped.py").write_text("# bumped\n")
        _commit_all(wt, "add bumped.py")

        def bump_version(root: Path, ticket: Any, final_id: str) -> Any:
            (root / "VERSION_BUMPED").write_text(final_id)
            _run(["git", "add", "VERSION_BUMPED"], root)
            return Ok("1.2.3")

        result = land(repo, tid, wt, dry_run=False, bump_version=bump_version)
        assert result.is_ok, result.err
        report = result.danger_ok
        assert report.release_bumped_to == "1.2.3"
        assert (repo / "VERSION_BUMPED").exists()
        # The bump's own write must have landed in the SAME commit as the
        # squash-apply, not a separate uncommitted change.
        assert _status_ignoring_frob(repo) == ""

    def test_no_bump_needed_reports_none(self, repo: Path) -> None:
        # frob:tests \
        # tests/test_ticket_land.py::TestReleaseBump.test_no_bump_needed_reports_none
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-nobump", str(wt)], repo)
        created = new_ticket(wt, _spec("No bump needed", scope=("src/quiet.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "quiet.py").write_text("# quiet\n")
        _commit_all(wt, "add quiet.py")

        result = land(
            repo,
            tid,
            wt,
            dry_run=False,
            bump_version=lambda root, ticket, fid: Ok(None),
        )
        assert result.is_ok, result.err
        assert result.danger_ok.release_bumped_to is None

    def test_bump_failure_unwinds_squash(self, repo: Path) -> None:
        # frob:tests \
        # tests/test_ticket_land.py::TestReleaseBump.test_bump_failure_unwinds_squash
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-badbump", str(wt)], repo)
        created = new_ticket(wt, _spec("Bad bump", scope=("src/badbump.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "badbump.py").write_text("# bad bump\n")
        _commit_all(wt, "add badbump.py")

        before_main_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()

        result = land(
            repo,
            tid,
            wt,
            dry_run=False,
            bump_version=lambda root, ticket, fid: Err(LandError.ReleaseBumpFailed),
        )
        assert result.is_err
        assert result.danger_err == LandError.ReleaseBumpFailed
        assert (
            _run(["git", "rev-parse", "HEAD"], repo).stdout.strip() == before_main_sha
        )
        assert _run(["git", "status", "--porcelain"], repo).stdout.strip() == ""

    def test_no_callback_is_noop(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestReleaseBump.test_no_callback_is_noop
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-nocallback", str(wt)], repo)
        created = new_ticket(wt, _spec("No callback", scope=("src/nc.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "nc.py").write_text("# no callback\n")
        _commit_all(wt, "add nc.py")

        result = land(repo, tid, wt, dry_run=False)
        assert result.is_ok, result.err
        assert result.danger_ok.release_bumped_to is None

    # frob:ticket T-0992
    def test_stale_worktree_version_bump_yields_main_plus_one(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestReleaseBump.test_stale_worktree_version_bump_yields_main_plus_one  # noqa: E501
        """T-0992 acceptance criterion: a worktree whose own pyproject.toml
        carries an OLDER version than main (it forked before some other
        land already bumped main) must still land at main-plus-one, never
        at a version recomputed from the worktree's stale carried value --
        the T-0976/T-0989 incident class. The `bump_version` callback here
        deliberately reads `root`'s (main's) CURRENT on-disk version, not
        the worktree's, modeling the fixed input-selection contract."""
        (repo / "pyproject.toml").write_text(
            '[project]\nname = "frob"\nversion = "0.183.0"\n'
        )
        _commit_all(repo, "main is ahead at 0.183.0")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-stale-version", str(wt)], repo)
        # The worktree's own pyproject still carries the OLDER version it
        # forked from main with -- never touched as part of this ticket's
        # scope, so it rides through the squash unchanged.
        (wt / "pyproject.toml").write_text(
            '[project]\nname = "frob"\nversion = "0.181.0"\n'
        )
        _commit_all(wt, "worktree still carries stale 0.181.0")

        created = new_ticket(wt, _spec("Stale worktree version", scope=("src/sv.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "sv.py").write_text("# stale version test\n")
        _commit_all(wt, "add sv.py")

        def bump_version(root: Path, ticket: Any, final_id: str) -> Any:
            # A correctly-implemented callback computes main+1 (0.184.0)
            # regardless of what the squash-apply did to the working
            # tree's pyproject.toml in between -- the T-0992 guard verifies
            # this independently against main's true pre-land committed
            # version, not the worktree's carried value.
            next_version = "0.184.0"
            (root / "pyproject.toml").write_text(
                f'[project]\nname = "frob"\nversion = "{next_version}"\n'
            )
            _run(["git", "add", "pyproject.toml"], root)
            return Ok(next_version)

        result = land(repo, tid, wt, dry_run=False, bump_version=bump_version)
        assert result.is_ok, result.err
        assert result.danger_ok.release_bumped_to == "0.184.0"
        assert (repo / "pyproject.toml").read_text().count('version = "0.184.0"') == 1

    # frob:ticket T-0992
    def test_downgrade_bump_is_refused(self, repo: Path) -> None:
        # frob:tests \
        # tests/test_ticket_land.py::TestReleaseBump.test_downgrade_bump_is_refused
        """T-0992 hard monotonicity refusal: a `bump_version` callback that
        computes a version no greater than main's CURRENT pre-land version
        (the T-0976/T-0989 failure mode -- a stale worktree-carried input
        winning over main's real version) must be refused loudly, and the
        staged squash unwound, rather than silently clobbering main."""
        (repo / "pyproject.toml").write_text(
            '[project]\nname = "frob"\nversion = "0.183.0"\n'
        )
        _commit_all(repo, "main is ahead at 0.183.0")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-downgrade", str(wt)], repo)
        created = new_ticket(wt, _spec("Downgrade bump", scope=("src/dg.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "dg.py").write_text("# downgrade test\n")
        _commit_all(wt, "add dg.py")

        before_main_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()

        def bump_version(root: Path, ticket: Any, final_id: str) -> Any:
            # Simulates the incident: recomputed from a stale (worktree-
            # carried) input, landing on a version <= main's current one.
            (root / "pyproject.toml").write_text(
                '[project]\nname = "frob"\nversion = "0.182.0"\n'
            )
            _run(["git", "add", "pyproject.toml"], root)
            return Ok("0.182.0")

        result = land(repo, tid, wt, dry_run=False, bump_version=bump_version)
        assert result.is_err
        assert result.danger_err == LandError.ReleaseBumpFailed
        assert (
            _run(["git", "rev-parse", "HEAD"], repo).stdout.strip() == before_main_sha
        )
        assert _run(["git", "status", "--porcelain"], repo).stdout.strip() == ""
        # Main's pyproject.toml must still read its pre-land version, not
        # the callback's would-be downgrade -- the unwind must be complete.
        assert (repo / "pyproject.toml").read_text().count('version = "0.183.0"') == 1


# frob:ticket T-1514
class TestPreCommitUnscopedSweep:
    """T-1514: `land`'s optional `pre_commit_sweep` callback, invoked at
    the last checkpoint before the final squash-apply commit -- `root`'s
    working tree holds only the staged, uncommitted merge-preview
    changeset at that point, so a `False` verdict unwinds via the same
    `_verified_reset_root` path every other pre-commit failure already
    uses and never touches a real commit."""

    # frob:ticket T-1514
    def _land_one(self, repo: Path, branch: str, filename: str) -> tuple[str, Path]:
        wt = repo.parent / branch
        _run(["git", "worktree", "add", "-b", branch, str(wt)], repo)
        created = new_ticket(wt, _spec(f"{branch} ticket", scope=(f"src/{filename}",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / filename).write_text(f"# {filename}\n")
        _commit_all(wt, f"add {filename}")
        return tid, wt

    # frob:ticket T-1514
    def test_true_verdict_lands_normally(self, repo: Path) -> None:
        # frob:tests \
        # tests/test_ticket_land.py::TestPreCommitUnscopedSweep.test_true_verdict_lands\
        # _normally
        tid, wt = self._land_one(repo, "feature-sweep-ok", "sweepok.py")
        calls: list[tuple[Path, str]] = []

        def sweep(root: Path, final_id: str) -> bool:
            calls.append((root, final_id))
            return True

        result = land(repo, tid, wt, dry_run=False, pre_commit_sweep=sweep)
        assert result.is_ok, result.err
        assert len(calls) == 1
        assert calls[0][0] == repo

    # frob:ticket T-1514
    def test_none_verdict_is_a_skip_lands_normally(self, repo: Path) -> None:
        # frob:tests \
        # tests/test_ticket_land.py::TestPreCommitUnscopedSweep.test_none_verdict_is_a_\
        # skip_lands_normally
        tid, wt = self._land_one(repo, "feature-sweep-skip", "sweepskip.py")

        result = land(
            repo, tid, wt, dry_run=False, pre_commit_sweep=lambda root, fid: None
        )
        assert result.is_ok, result.err

    # frob:ticket T-1514
    def test_false_verdict_unwinds_and_commits_nothing(self, repo: Path) -> None:
        # frob:tests \
        # tests/test_ticket_land.py::TestPreCommitUnscopedSweep.test_false_verdict_unwi\
        # nds_and_commits_nothing
        tid, wt = self._land_one(repo, "feature-sweep-refuse", "sweeprefuse.py")
        before_main_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()

        result = land(
            repo, tid, wt, dry_run=False, pre_commit_sweep=lambda root, fid: False
        )
        assert result.is_err
        assert result.danger_err == LandError.PreLandUnscopedSweepFailed
        assert (
            _run(["git", "rev-parse", "HEAD"], repo).stdout.strip() == before_main_sha
        )
        assert _run(["git", "status", "--porcelain"], repo).stdout.strip() == ""

    # frob:ticket T-1514
    def test_no_callback_is_noop(self, repo: Path) -> None:
        # frob:tests \
        # tests/test_ticket_land.py::TestPreCommitUnscopedSweep.test_no_callback_is_noop
        tid, wt = self._land_one(repo, "feature-sweep-none", "sweepnone.py")

        result = land(repo, tid, wt, dry_run=False)
        assert result.is_ok, result.err


# frob:ticket T-1078
class TestReleaseBumpQuartetAtomicity:
    """T-1078: land's REL001 bump used to update pyproject.toml/
    CHANGELOG.md while leaving `.frob-release.json` on its old version
    whenever a `bump_version` callback forgot (or failed silently) to
    write the manifest itself -- the desync then made every later land
    compute an already-taken version and refuse on the T-0992
    monotonicity guard. `land` now force-resyncs the manifest to the
    callback's reported version in the SAME step, and its refusal
    diagnostic names an incoherent quartet explicitly when that is the
    actual cause of a monotonicity refusal."""

    def test_manifest_version_written_same_step_as_pyproject(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestReleaseBumpQuartetAtomicity.test_manifest_version_written_same_step_as_pyproject  # noqa: E501
        (repo / ".frob-release.json").write_text(
            '{"version": "0.183.0", "api": {"a": "digest"}}\n'
        )
        _commit_all(repo, "seed release manifest at 0.183.0")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-quartet", str(wt)], repo)
        created = new_ticket(wt, _spec("Quartet atomicity", scope=("src/qa.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "qa.py").write_text("# quartet atomicity\n")
        _commit_all(wt, "add qa.py")

        def bump_version(root: Path, ticket: Any, final_id: str) -> Any:
            # Models the incident's root cause: the callback bumps
            # pyproject.toml/CHANGELOG.md but never touches (or fails to
            # write) `.frob-release.json` at all -- land itself must be
            # the thing that keeps the manifest coherent.
            (root / "pyproject.toml").write_text(
                '[project]\nname = "frob"\nversion = "0.184.0"\n'
            )
            _run(["git", "add", "pyproject.toml"], root)
            return Ok("0.184.0")

        result = land(repo, tid, wt, dry_run=False, bump_version=bump_version)
        assert result.is_ok, result.err
        assert result.danger_ok.release_bumped_to == "0.184.0"

        manifest_text = (repo / ".frob-release.json").read_text()
        assert '"version": "0.184.0"' in manifest_text
        # The pre-existing api map must survive the resync untouched.
        assert '"a": "digest"' in manifest_text
        # Landed in the SAME commit as pyproject.toml -- no leftover diff.
        assert _status_ignoring_frob(repo) == ""
        head_files = _run(["git", "show", "--stat", "--format=", "HEAD"], repo).stdout
        assert ".frob-release.json" in head_files
        assert "pyproject.toml" in head_files

    def test_incoherent_quartet_refusal_names_desync(
        self, repo: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestReleaseBumpQuartetAtomicity.test_incoherent_quartet_refusal_names_desync  # noqa: E501
        # Main's own quartet is ALREADY desynced before this land even
        # starts (mirrors the real incident: a prior land bumped
        # pyproject.toml but left the manifest stale).
        (repo / "pyproject.toml").write_text(
            '[project]\nname = "frob"\nversion = "0.211.0"\n'
        )
        (repo / ".frob-release.json").write_text('{"version": "0.210.0", "api": {}}\n')
        _commit_all(repo, "main quartet desynced: pyproject 0.211.0, manifest 0.210.0")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-desync", str(wt)], repo)
        created = new_ticket(wt, _spec("Desync refusal", scope=("src/dr.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "dr.py").write_text("# desync refusal\n")
        _commit_all(wt, "add dr.py")

        before_main_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()

        def bump_version(root: Path, ticket: Any, final_id: str) -> Any:
            # Derived from the stale manifest (0.210.0 -> 0.211.0), which
            # collides with pyproject's already-bumped 0.211.0 -- exactly
            # the incident's monotonicity trip.
            (root / "pyproject.toml").write_text(
                '[project]\nname = "frob"\nversion = "0.211.0"\n'
            )
            _run(["git", "add", "pyproject.toml"], root)
            return Ok("0.211.0")

        with caplog.at_level("ERROR", logger="frob.tickets._land"):
            result = land(repo, tid, wt, dry_run=False, bump_version=bump_version)

        assert result.is_err
        assert result.danger_err == LandError.ReleaseBumpFailed
        assert (
            _run(["git", "rev-parse", "HEAD"], repo).stdout.strip() == before_main_sha
        )
        assert _run(["git", "status", "--porcelain"], repo).stdout.strip() == ""
        assert "INCOHERENT" in caplog.text
        assert "frob release sync" in caplog.text
        assert "0.210.0" in caplog.text
        assert "0.211.0" in caplog.text


# frob:ticket T-1007
class TestRealCallbackStaleWorktreeManifest:
    """T-1007: the SAME T-0992 acceptance criterion (a stale worktree-
    carried value must never win over root's own state), now proven
    through the REAL `ticket_runner._apply_release_bump_for_land` callback
    instead of a fake `bump_version` closure that hardcodes the correct
    answer. Before T-1007's fix, this callback derived its baseline from
    whatever `.frob-release.json` ended up on root's WORKING TREE after
    the squash-apply -- which a stale, out-of-scope worktree copy can
    silently corrupt -- so this scenario tripped the T-0992 monotonicity
    guard's REFUSAL on the first land attempt every time (guard fires,
    but never prevents the retry churn). After the fix, the callback reads
    `.frob-release.json` from root's own git HEAD (never the working-tree
    copy the squash just wrote), computes main-plus-one correctly, and
    lands clean on the FIRST attempt -- the guard becomes a never-fires
    invariant for this callback, exactly as T-1007 required."""

    def test_stale_worktree_manifest_still_lands_main_plus_one(
        self, repo: Path
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestRealCallbackStaleWorktreeManifest.test_stale_worktree_manifest_still_lands_main_plus_one  # noqa: E501
        from frob.app import ticket_runner

        (repo / "pyproject.toml").write_text(
            '[project]\nname = "frob"\nversion = "0.183.0"\n'
        )
        (repo / "CHANGELOG.md").write_text("# Changelog\n\n## [0.183.0] - unreleased\n")
        (repo / ".frob-release.json").write_text('{"version": "0.183.0", "api": {}}\n')
        _commit_all(repo, "main is ahead at 0.183.0, manifest stamped to match")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-stale-manifest", str(wt)], repo)
        # Simulates the T-1007 incident directly: the worktree's OWN copy
        # of the manifest is stale (out of ticket scope, untouched by the
        # ticket itself, but present as a real diff against the fork
        # point) -- exactly the class of file that rides straight through
        # `git merge --squash` into root's working tree.
        (wt / ".frob-release.json").write_text('{"version": "0.181.0", "api": {}}\n')
        _commit_all(wt, "worktree still carries a stale manifest")

        created = new_ticket(wt, _spec("Stale worktree manifest", scope=("src/sm.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        # A new PUBLIC function -- a real MINOR-class API addition, so the
        # real `diff_class`/`required_version` machinery has something
        # genuine to compute against.
        (wt / "src" / "sm.py").write_text("def added():\n    pass\n")
        _commit_all(wt, "add sm.py (new public function)")

        result = land(
            repo,
            tid,
            wt,
            dry_run=False,
            bump_version=ticket_runner._land_bump_version_fn(),
        )
        assert result.is_ok, result.err
        # main-plus-one (0.184.0), computed from ROOT's committed manifest
        # (0.183.0) -- never the worktree's stale 0.181.0 copy, which would
        # have under-computed 0.182.0 and tripped the T-0992 guard instead.
        assert result.danger_ok.release_bumped_to == "0.184.0"
        assert (repo / "pyproject.toml").read_text().count('version = "0.184.0"') == 1
        manifest_text = (repo / ".frob-release.json").read_text()
        assert '"version": "0.184.0"' in manifest_text


# frob:ticket T-0793
class TestUvLockSync:
    """T-0793: land's release-bump step re-syncs `uv.lock` in the SAME
    commit as a real version bump, and the DirtyMain check tolerates (and
    auto-restores) a `uv.lock` whose only drift is the frob-version line
    flapping from a prior `uv run`/`uv lock` against an already-bumped
    pyproject.toml."""

    def test_bump_then_lock_synced_in_commit(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests \
        # tests/test_ticket_land.py::TestUvLockSync.test_bump_then_lock_synced_in_commit
        (repo / "pyproject.toml").write_text(
            '[project]\nname = "frob"\nversion = "0.1.0"\n'
        )
        _commit_all(repo, "add pyproject")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-lock", str(wt)], repo)
        created = new_ticket(wt, _spec("Bump with lock", scope=("src/locked.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "locked.py").write_text("# locked\n")
        _commit_all(wt, "add locked.py")

        def _fake_run_argv(argv: Sequence[str], **kwargs: Any) -> Any:
            if tuple(argv) == ("uv", "lock"):
                (kwargs["cwd"] / "uv.lock").write_text(
                    '[[package]]\nname = "frob"\nversion = "1.2.3"\n'
                )
                return Ok(
                    ProcResult(argv=tuple(argv), returncode=0, stdout="", stderr="")
                )
            return run_argv(argv, **kwargs)

        monkeypatch.setattr(_land_release_mod, "run_argv", _fake_run_argv)

        def bump_version(root: Path, ticket: Any, final_id: str) -> Any:
            (root / "pyproject.toml").write_text(
                '[project]\nname = "frob"\nversion = "1.2.3"\n'
            )
            _run(["git", "add", "pyproject.toml"], root)
            return Ok("1.2.3")

        result = land(repo, tid, wt, dry_run=False, bump_version=bump_version)
        assert result.is_ok, result.err
        assert result.danger_ok.release_bumped_to == "1.2.3"
        assert (repo / "uv.lock").read_text().count('version = "1.2.3"') == 1
        # uv.lock landed in the SAME commit as the bump, not left dirty.
        assert _status_ignoring_frob(repo) == ""
        committed_files = _run(
            ["git", "show", "--name-only", "--pretty=format:", "HEAD"], repo
        ).stdout.split()
        assert "uv.lock" in committed_files

    def test_dirty_lock_version_line_only_does_not_refuse(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestUvLockSync.test_dirty_lock_version_line_only_does_not_refuse  # noqa: E501
        (repo / "uv.lock").write_text(
            '[[package]]\nname = "frob"\nversion = "0.1.0"\nsource = { editable = "." }\n'
        )
        _commit_all(repo, "add uv.lock")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-lockdirty", str(wt)], repo)
        created = new_ticket(wt, _spec("Tolerate lock drift"))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        _commit_all(wt, "wip")

        # Simulate the flap: only the frob version line in uv.lock changed,
        # nothing else in the tree is dirty.
        (repo / "uv.lock").write_text(
            '[[package]]\nname = "frob"\nversion = "0.2.0"\nsource = { editable = "." }\n'
        )

        result = land(repo, tid, wt, dry_run=True)
        assert result.is_ok, result.err
        # The drift was auto-restored back to the committed content.
        assert 'version = "0.1.0"' in (repo / "uv.lock").read_text()
        assert _status_ignoring_frob(repo) == ""

    def test_worktree_side_lock_flap_auto_restored_before_wip_commit(
        self, repo: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestUvLockSync.test_worktree_side_lock_flap_auto_restored_before_wip_commit  # noqa: E501
        # frob:tests src/frob/tickets/_land_git_ops.py::_wip_commit kind="unit"
        """T-1003 (churn item 4): the T-0793 frob-version-only auto-restore
        applies to the WORKTREE's own `uv.lock` too, before the wip-commit
        dirty check -- not just `root`'s, as `test_dirty_lock_version_
        line_only_does_not_refuse` above already locks. Without this, the
        flap would get silently wip-committed as noise and squash-applied
        into the landing commit, needing the same manual `git checkout --
        uv.lock` ritual on the OTHER side of the land."""
        (repo / "uv.lock").write_text(
            '[[package]]\nname = "frob"\nversion = "0.1.0"\nsource = { editable = "." }\n'
        )
        _commit_all(repo, "add uv.lock")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-wtlockdirty", str(wt)], repo)
        created = new_ticket(wt, _spec("Tolerate worktree-side lock drift"))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        _commit_all(wt, "wip")

        # Simulate the flap IN THE WORKTREE (not root): only the frob
        # version line changed, uncommitted, nothing else dirty.
        (wt / "uv.lock").write_text(
            '[[package]]\nname = "frob"\nversion = "0.2.0"\nsource = { editable = "." }\n'
        )

        with caplog.at_level("INFO", logger="frob.tickets._land"):
            result = land(repo, tid, wt, dry_run=False)

        assert result.is_ok, result.err
        assert "wip-commit dirty check" in caplog.text
        # Restored back to the committed content in the worktree, never
        # wip-committed as noise nor squash-applied into the landing
        # commit -- root's own uv.lock still reads its one committed line.
        assert 'version = "0.1.0"' in (wt / "uv.lock").read_text()
        assert (repo / "uv.lock").read_text().count('version = "0.1.0"') == 1

    def test_dirty_lock_with_other_change_still_refuses(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestUvLockSync.test_dirty_lock_with_other_change_still_refuses  # noqa: E501
        (repo / "uv.lock").write_text(
            '[[package]]\nname = "frob"\nversion = "0.1.0"\nsource = { editable = "." }\n'
        )
        _commit_all(repo, "add uv.lock")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-lockplus", str(wt)], repo)
        created = new_ticket(wt, _spec("Real dirt"))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        _commit_all(wt, "wip")

        (repo / "uv.lock").write_text(
            '[[package]]\nname = "frob"\nversion = "0.2.0"\nsource = { editable = "." }\n'
        )
        (repo / "other.txt").write_text("real uncommitted change\n")

        result = land(repo, tid, wt, dry_run=True)
        assert result.is_err
        assert result.danger_err == LandError.DirtyMain

    def test_dirty_lock_version_plus_other_line_still_refuses(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestUvLockSync.test_dirty_lock_version_plus_other_line_still_refuses  # noqa: E501
        (repo / "uv.lock").write_text(
            "[[package]]\n"
            'name = "frob"\n'
            'version = "0.1.0"\n'
            'source = { editable = "." }\n'
        )
        _commit_all(repo, "add uv.lock")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-lockmixed", str(wt)], repo)
        created = new_ticket(wt, _spec("Mixed lock drift"))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        _commit_all(wt, "wip")

        # uv.lock is the SOLE dirty path, but its diff touches BOTH the
        # frob version line AND another line (a dependency hash flip,
        # here a changed `source` value) -- `_diff_is_frob_version_line_
        # only` must reject this shape (len(changed) != 2) so the
        # destructive auto-restore never fires on real lock content.
        dirty_content = (
            "[[package]]\n"
            'name = "frob"\n'
            'version = "0.2.0"\n'
            'source = { editable = "./elsewhere" }\n'
        )
        (repo / "uv.lock").write_text(dirty_content)

        result = land(repo, tid, wt, dry_run=True)
        assert result.is_err
        assert result.danger_err == LandError.DirtyMain
        # Not auto-restored: the dirty content is left exactly as written.
        assert (repo / "uv.lock").read_text() == dirty_content

    def test_lock_sync_spawn_failure_unwinds_squash(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestUvLockSync.test_lock_sync_spawn_failure_unwinds_squash  # noqa: E501
        (repo / "pyproject.toml").write_text(
            '[project]\nname = "frob"\nversion = "0.1.0"\n'
        )
        _commit_all(repo, "add pyproject")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-lockfail", str(wt)], repo)
        created = new_ticket(
            wt, _spec("Bump with failing lock", scope=("src/failedlock.py",))
        )
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "failedlock.py").write_text("# failed lock\n")
        _commit_all(wt, "add failedlock.py")

        before_main_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()

        def _fake_run_argv(argv: Sequence[str], **kwargs: Any) -> Any:
            if tuple(argv) == ("uv", "lock"):
                return Ok(
                    ProcResult(
                        argv=tuple(argv),
                        returncode=1,
                        stdout="",
                        stderr="simulated uv lock failure",
                    )
                )
            return run_argv(argv, **kwargs)

        monkeypatch.setattr(_land_release_mod, "run_argv", _fake_run_argv)

        def bump_version(root: Path, ticket: Any, final_id: str) -> Any:
            (root / "pyproject.toml").write_text(
                '[project]\nname = "frob"\nversion = "1.2.3"\n'
            )
            _run(["git", "add", "pyproject.toml"], root)
            return Ok("1.2.3")

        result = land(repo, tid, wt, dry_run=False, bump_version=bump_version)
        assert result.is_err
        assert result.danger_err == LandError.ReleaseBumpFailed
        assert (
            _run(["git", "rev-parse", "HEAD"], repo).stdout.strip() == before_main_sha
        )
        assert _run(["git", "status", "--porcelain"], repo).stdout.strip() == ""


# frob:ticket T-1699
class TestRapidDebtOnlyDriftAutoCommit:
    """T-1699: `_commit_rapid_debt_only_drift` -- the second DirtyMain
    auto-heal `_refuse_if_main_dirty` tries, alongside T-0793's uv.lock
    precedent. Unlike that precedent (which DISCARDS a benign flap),
    this one COMMITS: a `rapid-debt.jsonl` append is real, land-owned
    content a concurrent land's own two-step append-then-commit
    (deliberately outside the land lock, T-1684) can leave dirty for a
    second agent's land to observe mid-window."""

    def test_sole_rapid_debt_dirt_is_committed(self, repo: Path) -> None:
        # frob:tests \
        # tests/test_ticket_land.py::TestRapidDebtOnlyDriftAutoCommit.test_sole_rapid_d\
        # ebt_dirt_is_committed
        from frob.tickets._land_git_ops import _commit_rapid_debt_only_drift

        (repo / "rapid-debt.jsonl").write_text(
            '{"commit": "abc123", "skipped": "post-land-unscoped-sweep-deferred", '
            '"ticket": "T-0001"}\n'
        )
        _run(["git", "add", "rapid-debt.jsonl"], repo)
        _run(["git", "commit", "-q", "-m", "seed rapid-debt.jsonl"], repo)
        (repo / "rapid-debt.jsonl").write_text(
            '{"commit": "abc123", "skipped": "post-land-unscoped-sweep-deferred", '
            '"ticket": "T-0001"}\n'
            '{"commit": "def456", "skipped": "post-land-unscoped-sweep-deferred", '
            '"ticket": "T-0002"}\n'
        )

        assert _commit_rapid_debt_only_drift(repo) is True
        assert _run(["git", "status", "--porcelain"], repo).stdout.strip() == ""

    def test_a_second_dirty_file_blocks_the_auto_commit(self, repo: Path) -> None:
        # frob:tests \
        # tests/test_ticket_land.py::TestRapidDebtOnlyDriftAutoCommit.test_a_second_dir\
        # ty_file_blocks_the_auto_commit
        from frob.tickets._land_git_ops import _commit_rapid_debt_only_drift

        (repo / "rapid-debt.jsonl").write_text(
            '{"commit": "abc123", "skipped": "x", "ticket": "T-0001"}\n'
        )
        (repo / "other.py").write_text("# unrelated dirt\n")

        assert _commit_rapid_debt_only_drift(repo) is False
        status = _run(["git", "status", "--porcelain"], repo).stdout
        assert "rapid-debt.jsonl" in status
        assert "other.py" in status

    def test_no_dirt_at_all_is_a_noop(self, repo: Path) -> None:
        # frob:tests \
        # tests/test_ticket_land.py::TestRapidDebtOnlyDriftAutoCommit.test_no_dirt_at_a\
        # ll_is_a_noop
        from frob.tickets._land_git_ops import _commit_rapid_debt_only_drift

        assert _commit_rapid_debt_only_drift(repo) is False


# frob:ticket T-1699
class TestDirtOwnedByNoOpenTicket:
    """T-1699: `_dirt_owned_by_no_open_ticket` -- tells root dirt that
    matches SOME open ticket's declared scope (plausibly a crashed
    land's own leftover) apart from dirt no open ticket's scope covers
    at all (most often a coordinator working directly on the shared root
    outside the ticket workflow -- the shape three agents in one session
    each independently misdiagnosed as "a crashed land")."""

    def test_path_inside_an_open_tickets_scope_is_not_orphaned(
        self, repo: Path
    ) -> None:
        # frob:tests \
        # tests/test_ticket_land.py::TestDirtOwnedByNoOpenTicket.test_path_inside_an_op\
        # en_tickets_scope_is_not_orphaned
        from frob.tickets._land import _dirt_owned_by_no_open_ticket

        created = new_ticket(repo, _spec("Open work", scope=("src/owned.py",)))
        assert created.is_ok
        assert transition(repo, created.danger_ok.id, TicketState.PLANNED).is_ok

        assert _dirt_owned_by_no_open_ticket(repo, ("src/owned.py",)) is False

    def test_path_outside_every_open_tickets_scope_is_orphaned(
        self, repo: Path
    ) -> None:
        # frob:tests \
        # tests/test_ticket_land.py::TestDirtOwnedByNoOpenTicket.test_path_outside_ever\
        # y_open_tickets_scope_is_orphaned
        from frob.tickets._land import _dirt_owned_by_no_open_ticket

        created = new_ticket(repo, _spec("Open work", scope=("src/owned.py",)))
        assert created.is_ok
        assert transition(repo, created.danger_ok.id, TicketState.PLANNED).is_ok

        assert _dirt_owned_by_no_open_ticket(repo, ("src/coordinator_edit.py",)) is True

    def test_a_done_tickets_scope_does_not_count(self, repo: Path) -> None:
        # frob:tests \
        # tests/test_ticket_land.py::TestDirtOwnedByNoOpenTicket.test_a_done_tickets_sc\
        # ope_does_not_count
        """A DONE ticket's scope must not exempt its old files forever --
        only currently OPEN (non-terminal) tickets count."""
        from frob.tickets._land import _dirt_owned_by_no_open_ticket

        created = new_ticket(repo, _spec("Finished work", scope=("src/finished.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(repo, tid)
        assert transition(repo, tid, TicketState.DONE).is_ok

        assert _dirt_owned_by_no_open_ticket(repo, ("src/finished.py",)) is True


# frob:ticket T-0338
class TestRebuildNatives:
    """T-0338: `land`'s optional `rebuild_natives` callback -- invoked only
    when the landed changeset touches a native source tree."""

    def test_invoked_when_native_source_touched(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestRebuildNatives.test_invoked_when_native_source_touched  # noqa: E501
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-native-src", str(wt)], repo)
        created = new_ticket(
            wt, _spec("Native change", scope=("frob-core/src/lib.rs",))
        )
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "frob-core").mkdir()
        (wt / "frob-core" / "src").mkdir()
        (wt / "frob-core" / "src" / "lib.rs").write_text("// native change\n")
        _commit_all(wt, "touch frob-core")

        calls: list[Path] = []

        def rebuild_natives(root: Path) -> bool:
            calls.append(root)
            return True

        result = land(repo, tid, wt, dry_run=False, rebuild_natives=rebuild_natives)
        assert result.is_ok, result.err
        assert result.danger_ok.natives_rebuilt is True
        assert calls == [repo]

    def test_skipped_when_no_native_source_touched(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestRebuildNatives.test_skipped_when_no_native_source_touched  # noqa: E501
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-not-native", str(wt)], repo)
        created = new_ticket(wt, _spec("Regular change", scope=("src/regular.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "regular.py").write_text("# regular\n")
        _commit_all(wt, "add regular.py")

        calls: list[Path] = []

        def rebuild_natives(root: Path) -> bool:
            calls.append(root)
            return True

        result = land(repo, tid, wt, dry_run=False, rebuild_natives=rebuild_natives)
        assert result.is_ok, result.err
        assert result.danger_ok.natives_rebuilt is False
        assert calls == []

    def test_rebuild_failure_does_not_block_land(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestRebuildNatives.test_rebuild_failure_does_not_block_land  # noqa: E501
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-native-fail", str(wt)], repo)
        created = new_ticket(
            wt, _spec("Native change fails rebuild", scope=("strata-core/src/lib.rs",))
        )
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "strata-core").mkdir()
        (wt / "strata-core" / "src").mkdir()
        (wt / "strata-core" / "src" / "lib.rs").write_text("// native change\n")
        _commit_all(wt, "touch strata-core")

        result = land(repo, tid, wt, dry_run=False, rebuild_natives=lambda root: False)
        assert result.is_ok, result.err
        assert result.danger_ok.natives_rebuilt is False


# frob:ticket T-0682
class TestMergeMainIntoWorktreeRicherState:
    """T-0682 integration lock: `_merge_main_into_worktree` (the "merge main
    into the worktree" stage every `frob ticket land` call runs, and the
    exact site where the registered `tickets.md` git merge driver
    auto-fires on `git merge --no-commit --no-ff`) must not let main's
    bare, reportless copy of the LANDING ticket's own block win over the
    worktree's Done-reported copy WHEN the worktree's copy also outranks
    it -- the original T-0682 field incident."""

    def test_landing_tickets_in_progress_report_survives_the_merge_stage(
        self, repo: Path
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestMergeMainIntoWorktreeRicherState.test_landing_tickets_in_progress_report_survives_the_merge_stage  # noqa: E501
        # Ticket is created ON main (a real id, not a draft) so it exists
        # in BOTH the worktree's and main's ledgers before either side
        # diverges it -- the scenario under test is a genuine same-id
        # divergence, not draft finalization (covered elsewhere).
        created = new_ticket(repo, _spec("Landing ticket", scope=("src/widget.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _commit_all(repo, "file landing ticket")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-richer", str(wt)], repo)

        # Worktree: driven to `in-progress` with a substantive Done report
        # already attached -- a HIGHER state-rank than main's bare queued
        # AND a Done report, matching the real field incident (T-0633/
        # T-0637's landing tickets were in-progress+reported when the
        # merge stage regressed them).
        assert transition(wt, tid, TicketState.PLANNED).is_ok
        assert transition(wt, tid, TicketState.IN_PROGRESS).is_ok
        loaded = load_all(wt).danger_ok[tid]
        with_report = loaded.model_copy(
            update={
                "body": loaded.body
                + "\n## Done report\n\nSubstantive report text here.\n"
            }
        )
        assert write_ticket(wt, with_report).is_ok
        (wt / "src" / "widget.py").write_text("# new widget\n")
        _commit_all(wt, "advance ticket to in-progress+report")
        ticket_before_merge = load_all(wt).danger_ok[tid]

        # Main's OWN copy of the SAME ticket never advanced past its bare
        # `queued` state -- unrelated main-side history, no divergence in
        # rank OR report to work in the worktree's favor by accident.
        (repo / "src" / "unrelated.py").write_text("# unrelated main commit\n")
        _commit_all(repo, "unrelated main-side commit")

        result = _land_mod._merge_main_into_worktree(
            repo, wt, ticket_before_merge, "main"
        )
        assert result.is_ok, result.err

        merged_text = ledger_path(wt).read_text()
        from frob.tickets._store import _parse_ledger

        parsed = _parse_ledger(merged_text).danger_ok
        assert parsed[tid].state == TicketState.IN_PROGRESS
        assert "## Done report" in parsed[tid].body


class TestUnboundAcceptancePreflightBeforeMerge:
    """T-0763: an unbound acceptance criterion must be caught by land's
    PRE-merge closeability preflight (`_validate_closeable` ->
    `_validate_acceptance_bound`), not discovered only after the merge/
    finalize commits are already made. Before this fix, `_validate_closeable`
    checked only evidence-present/Done-report/cmd-evidence-kind, so an
    unbound acceptance criterion sailed through the precheck, `land` merged
    main into the worktree AND committed a finalize commit, and only then
    failed at `_close_finalized_ticket`'s `transition(..., DONE)` call with
    `LandError.CloseFailed` -- leaving a merge/finalize commit the caller
    had to `git reset --hard HEAD~1` before retrying. This test asserts the
    ENTIRE git log (both `repo`/main and `wt`/worktree) is byte-identical
    before and after the refused land -- not just that `land` returns an
    error -- since a fail-AFTER-merge regression would still return
    `Err(...)` while leaving exactly the commit(s) this asserts are absent.
    """

    def test_unbound_acceptance_refused_pre_merge_no_commits_created(
        self, repo: Path
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestUnboundAcceptancePreflightBeforeMerge.test_unbound_acceptance_refused_pre_merge_no_commits_created  # noqa: E501
        wt = repo.parent / "wt"
        _run(
            ["git", "worktree", "add", "-b", "feature-unbound-acceptance", str(wt)],
            repo,
        )

        created = new_ticket(
            wt,
            _spec("Ticket with unbound acceptance", scope=("src/other3.py",)),
        )
        assert created.is_ok
        tid = created.danger_ok.id

        # Attach an acceptance criterion whose own `evidence` tuple is
        # empty -- unbound by construction (T-0572) -- while the ticket
        # otherwise satisfies every OTHER closeability precondition
        # (evidence present, Done report present, evidence-kind
        # consistent), isolating this test to the acceptance-binding gate
        # alone.
        _make_closeable(wt, tid)
        loaded = load_all(wt)
        ticket = loaded.danger_ok[tid]
        ticket = ticket.model_copy(
            update={
                "acceptance": (
                    AcceptanceCriterion(text="GIVEN x WHEN y THEN z", evidence=()),
                )
            }
        )
        assert write_ticket(wt, ticket).is_ok
        _commit_all(wt, "advance ticket with unbound acceptance criterion")

        main_log_before = _run(["git", "log", "--oneline", "--all"], repo).stdout
        wt_log_before = _run(["git", "log", "--oneline", "--all"], wt).stdout
        wt_status_before = _status_ignoring_frob(wt)

        result = land(repo, tid, wt, dry_run=False)

        assert result.is_err
        assert result.danger_err == LandError.NotCloseable

        # Git log is UNCHANGED on both sides -- no merge commit, no
        # finalize commit, no squash-apply commit -- not merely "the same
        # HEAD sha", but the exact same full set of commits (a fail-after-
        # merge regression would add commits reachable only via a branch
        # ref, which `--all` catches even if `HEAD` itself were untouched).
        assert (
            _run(["git", "log", "--oneline", "--all"], repo).stdout == main_log_before
        )
        assert _run(["git", "log", "--oneline", "--all"], wt).stdout == wt_log_before
        # Working tree is clean -- no merge left half-applied/uncommitted.
        assert _status_ignoring_frob(wt) == wt_status_before
        assert _status_ignoring_frob(repo) == ""

        # The ticket itself is untouched: still in-progress, not closed.
        still = load_all(wt).danger_ok[tid]
        assert still.state == TicketState.IN_PROGRESS


class TestScopeUnboundPreflightBeforeMerge:
    """T-0774: `EvidenceScopeUnbound` (D-05's injected `covers_scope`
    callable) must ALSO be caught by land's PRE-merge closeability
    preflight (`_land_precheck` -> `_validate_scope_covered_preflight`),
    not discovered only after the merge/finalize commits already exist.
    Before this fix, `_land_precheck` never consulted `covers_scope` at
    all -- it was invoked for the first time inside `_land_finalize_and_close`,
    AFTER the merge commit was already made, so a ticket whose evidence does
    not cover its scope still merged+committed before `land` refused
    (`LandError.CloseFailed`, not `NotCloseable`). This test asserts the
    ENTIRE git log (both `repo`/main and `wt`/worktree) is byte-identical
    before and after the refused land -- not just that `land` returns an
    error -- mirroring `TestUnboundAcceptancePreflightBeforeMerge`'s own
    assertion shape for the sibling D-05 check this ticket closes."""

    def test_scope_unbound_refused_pre_merge_no_commits_created(
        self, repo: Path
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestScopeUnboundPreflightBeforeMerge.test_scope_unbound_refused_pre_merge_no_commits_created  # noqa: E501
        wt = repo.parent / "wt"
        _run(
            ["git", "worktree", "add", "-b", "feature-scope-unbound", str(wt)],
            repo,
        )

        created = new_ticket(
            wt,
            _spec("Ticket with scope-unbound evidence", scope=("src/other4.py",)),
        )
        assert created.is_ok
        tid = created.danger_ok.id

        # Otherwise fully closeable (evidence present, Done report present,
        # no unbound acceptance criteria) -- isolating this test to the
        # covers_scope preflight alone.
        _make_closeable(wt, tid)
        _commit_all(wt, "advance ticket with scope-unbound evidence")

        main_log_before = _run(["git", "log", "--oneline", "--all"], repo).stdout
        wt_log_before = _run(["git", "log", "--oneline", "--all"], wt).stdout
        wt_status_before = _status_ignoring_frob(wt)

        # A `covers_scope` callable that always answers False, exactly the
        # shape `frob.app.ticket_runner`'s `_land_covers_scope_fn` supplies
        # via `frob.gates.evidence_covers_scope` when no evidence id binds
        # to a touched/scope symbol.
        result = land(repo, tid, wt, dry_run=False, covers_scope=lambda _t: False)

        assert result.is_err
        assert result.danger_err == LandError.NotCloseable

        # Git log is UNCHANGED on both sides -- no merge commit, no
        # finalize commit, no squash-apply commit.
        assert (
            _run(["git", "log", "--oneline", "--all"], repo).stdout == main_log_before
        )
        assert _run(["git", "log", "--oneline", "--all"], wt).stdout == wt_log_before
        # Working tree is clean -- no merge left half-applied/uncommitted.
        assert _status_ignoring_frob(wt) == wt_status_before
        assert _status_ignoring_frob(repo) == ""

        # The ticket itself is untouched: still in-progress, not closed.
        still = load_all(wt).danger_ok[tid]
        assert still.state == TicketState.IN_PROGRESS

    def test_covers_scope_true_still_lands_normally(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestScopeUnboundPreflightBeforeMerge.test_covers_scope_true_still_lands_normally  # noqa: E501
        wt = repo.parent / "wt"
        _run(
            ["git", "worktree", "add", "-b", "feature-scope-bound", str(wt)],
            repo,
        )

        created = new_ticket(
            wt,
            _spec("Ticket with scope-bound evidence", scope=("src/other5.py",)),
        )
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        _commit_all(wt, "advance ticket with scope-bound evidence")

        result = land(repo, tid, wt, dry_run=False, covers_scope=lambda _t: True)

        assert result.is_ok, result.err


# frob:ticket T-0795
class TestLandRetryAfterFinalizeThenFail:
    """T-0795: three real lands this drive (T-0676, T-0774, T-0767) merged
    and finalized in the worktree (the ticket transitioned to `done` and
    that transition was committed there) but then failed at a LATER step
    -- the squash-apply onto `root` -- before the main commit landed.
    Retrying the identical `land()` call always errored `InvalidTransition`
    (`transition(..., DONE)` re-run against an already-`done` ticket), even
    though the land itself is perfectly resumable; each incident required a
    manual splice-apply onto main instead. This locks the fix: a retry
    recognizes the already-done ticket and resumes straight at
    squash-apply."""

    def test_retry_after_finalize_then_squash_failure_lands_the_diff(
        self, repo: Path
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestLandRetryAfterFinalizeThenFail.test_retry_after_finalize_then_squash_failure_lands_the_diff  # noqa: E501
        # frob:tests src/frob/tickets/_land_finalize.py::_close_finalized_ticket \
        # kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-retry", str(wt)], repo)
        created = new_ticket(wt, _spec("Retry me", scope=("src/retried.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "retried.py").write_text("# retried feature\n")
        _commit_all(wt, "add retried.py")

        before_main_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()

        # First attempt: `bump_version` fails (simulating whichever
        # post-finalize step actually failed in the real incidents --
        # squash conflict, REL001 bump, or the T-0463 completeness
        # assertion; all of them unwind `root` cleanly via `reset --hard`
        # the same way this callback's failure path does) AFTER the
        # worktree has already merged, finalized, and closed the ticket
        # (that whole sequence commits in the WORKTREE unconditionally
        # before `_land_squash_apply` -- see `_land_locked` -- so it
        # survives this failure).
        first = land(
            repo,
            tid,
            wt,
            dry_run=False,
            bump_version=lambda root, ticket, fid: Err(LandError.ReleaseBumpFailed),
        )
        assert first.is_err
        assert first.danger_err == LandError.ReleaseBumpFailed

        # root: untouched by the failed attempt (the bump failure unwound
        # the staged squash).
        assert (
            _run(["git", "rev-parse", "HEAD"], repo).stdout.strip() == before_main_sha
        )
        assert _status_ignoring_frob(repo) == ""

        # worktree: the ticket really did reach `done` and that transition
        # really did commit -- this is the exact precondition that used to
        # make the retry below error `InvalidTransition`. The first attempt
        # already finalized `tid`'s draft id to a real sequential id (that
        # finalize-and-commit step runs BEFORE the bump that then failed),
        # so the retry -- exactly like a real coordinator's retry -- must
        # address the ticket by its now-finalized id.
        wt_tickets = load_all(wt).danger_ok
        final_id = next(i for i, t in wt_tickets.items() if t.state == TicketState.DONE)
        assert final_id != tid
        assert _status_ignoring_frob(wt) == ""

        # Retry, identical arguments (final id, same worktree) except a
        # bump_version that now succeeds -- must NOT error InvalidTransition
        # on the already-done ticket; must resume at squash-apply and
        # actually land.
        second = land(
            repo,
            final_id,
            wt,
            dry_run=False,
            bump_version=lambda root, ticket, fid: Ok(None),
        )
        assert second.is_ok, second.err
        assert second.danger_ok.final_id == final_id

        # The diff really landed onto main: the new file exists on root's
        # branch, in a real "land <id>" commit distinct from before_main_sha.
        assert (repo / "src" / "retried.py").read_text() == "# retried feature\n"
        after_main_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        assert after_main_sha != before_main_sha
        log = _run(["git", "log", "--oneline"], repo).stdout
        assert f"land {final_id}" in log
        assert _status_ignoring_frob(repo) == ""

    def test_retry_after_full_success_reports_absorption_not_commit_failed(
        self, repo: Path
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestLandRetryAfterFinalizeThenFail.test_retry_after_full_success_reports_absorption_not_commit_failed  # noqa: E501
        """T-1001 (churn item 2): retrying a land whose FIRST attempt
        already fully succeeded (committed onto `root`, ticket `done` on
        both sides) stages nothing new -- the squash finds no file diff
        and the ledger splice of an already-matching block is a no-op.
        This must report a clean `absorbed by prior land` success
        (`ledger_spliced=False`, `commit_sha` naming the SAME commit the
        first land made, no new files), never `CommitFailed` from an
        empty `git commit`."""
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-absorbed", str(wt)], repo)
        created = new_ticket(wt, _spec("Absorbed by its own prior land"))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        _commit_all(wt, "advance ticket absorbed by its own prior land")

        first = land(repo, tid, wt, dry_run=False)
        assert first.is_ok, first.err
        final_id = first.danger_ok.final_id
        first_sha = first.danger_ok.commit_sha
        assert first_sha is not None

        retry = land(repo, final_id, wt, dry_run=False)

        assert retry.is_ok, retry.err
        assert retry.danger_ok.ledger_spliced is False
        assert retry.danger_ok.commit_sha == first_sha
        assert retry.danger_ok.files_changed == ()
        # No new commit was made -- root's tip is unchanged by the retry.
        assert _run(["git", "rev-parse", "HEAD"], repo).stdout.strip() == first_sha

    def test_retry_when_still_queued_re_runs_the_ordinary_transition(
        self, repo: Path
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestLandRetryAfterFinalizeThenFail.test_retry_when_still_queued_re_runs_the_ordinary_transition  # noqa: E501
        # frob:tests src/frob/tickets/_land_finalize.py::_close_finalized_ticket \
        # kind="unit"
        """Sanity companion: the ordinary (non-retry) first-time land, where
        the ticket is NOT already done, still runs the real transition --
        the T-0795 fix only short-circuits when the ticket is ALREADY
        `done`, it does not skip closing altogether."""
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-firsttime", str(wt)], repo)
        created = new_ticket(wt, _spec("First time", scope=("src/firsttime.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "firsttime.py").write_text("# first time\n")
        _commit_all(wt, "add firsttime.py")

        assert load_all(wt).danger_ok[tid].state == TicketState.IN_PROGRESS

        result = land(repo, tid, wt, dry_run=False)
        assert result.is_ok, result.err
        assert result.danger_ok.final_id != ""


# frob:ticket T-1701
# frob:ticket T-1721
class TestLandDroppedTicket:
    """T-1701: `frob ticket land` must be able to publish a DROPPED
    ticket's ledger entry to main -- before this fix, `_close_finalized_
    ticket` unconditionally forced a `dropped -> done` transition
    (illegal, `InvalidTransition`, every single retry) and `_validate_
    closeable` unconditionally required evidence + a Done report (neither
    applicable to a ticket dropped, not done), leaving no path through
    `land` for a legitimate DROPPED outcome -- forcing an agent to bypass
    worktree isolation and run `frob ticket drop` directly against the
    root checkout (the live incident: T-1538, then independently again
    T-1683 within the same hour)."""

    # frob:ticket T-1721
    def test_dropped_ticket_with_a_reason_lands_cleanly(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestLandDroppedTicket.test_dropped_ticket_with_a_reason_lands_cleanly  # noqa: E501
        # frob:tests src/frob/tickets/_land_merge.py::_validate_closeable kind="unit"
        # frob:tests src/frob/tickets/_land_finalize.py::_close_finalized_ticket \
        # kind="unit"
        from frob.tickets import drop_ticket

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-dropped", str(wt)], repo)
        created = new_ticket(wt, _spec("Already fixed elsewhere"))
        assert created.is_ok
        tid = created.danger_ok.id
        assert transition(wt, tid, TicketState.PLANNED).is_ok
        assert transition(wt, tid, TicketState.IN_PROGRESS).is_ok
        dropped = drop_ticket(wt, tid, "premise already resolved by an earlier ticket")
        assert dropped.is_ok, dropped.err
        _commit_all(wt, "drop the ticket")

        result = land(repo, tid, wt, dry_run=False)
        assert result.is_ok, result.err

        on_main = load_all(repo).danger_ok[result.danger_ok.final_id]
        assert on_main.state == TicketState.DROPPED
        assert "premise already resolved" in on_main.body

    def test_dropped_ticket_with_no_reason_refuses(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestLandDroppedTicket.test_dropped_ticket_with_no_reason_refuses  # noqa: E501
        # frob:tests src/frob/tickets/_land_merge.py::_validate_closeable kind="unit"
        """A `state: dropped` ticket whose body carries no `## Drop
        reason` section at all (only reachable by hand-editing the ledger
        -- `frob ticket drop` itself always refuses an empty reason at
        write time, `DropReasonMissing`) must still refuse to land: a
        drop with no recorded reason is indistinguishable from a silent
        discard, the exact hazard `_validate_closeable`'s DROPPED branch
        exists to keep unreachable end to end, not just at the CLI
        surface."""
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-dropped-blank", str(wt)], repo)
        created = new_ticket(wt, _spec("No reason recorded"))
        assert created.is_ok
        tid = created.danger_ok.id
        assert transition(wt, tid, TicketState.PLANNED).is_ok
        assert transition(wt, tid, TicketState.IN_PROGRESS).is_ok
        assert transition(wt, tid, TicketState.DROPPED).is_ok
        _commit_all(wt, "drop with no recorded reason (hand-transitioned)")

        result = land(repo, tid, wt, dry_run=False)
        assert result.is_err
        assert result.danger_err == LandError.NotCloseable


# frob:ticket T-0795
class TestLandRefusesWhenRootIsWorktree:
    """T-0795: `land()` invoked with `--worktree` resolving to the SAME
    path as `root` used to fall through to `_worktree_full_changeset`'s
    much later T-0640/T-0761 diagnosis ("`--worktree` almost certainly
    points at the same checkout/branch root has checked out ... create a
    real feature branch") -- a correct remedy for a worktree genuinely
    pointed at the wrong branch, but a misleading one for the far more
    common real cause: `root` defaults to the invoker's cwd, so running
    `frob ticket land` from a shell sitting INSIDE the worktree makes
    `root` resolve to `worktree` for free. This locks the new EARLY
    refusal (before any git mutation) that names the real mistake."""

    def test_refused_before_any_git_mutation_names_the_real_mistake(
        self, repo: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestLandRefusesWhenRootIsWorktree.test_refused_before_any_git_mutation_names_the_real_mistake  # noqa: E501
        # frob:tests src/frob/tickets/_land.py::_refuse_if_root_is_worktree kind="unit"
        created = new_ticket(
            repo, _spec("Same path as root", scope=("src/samepath.py",))
        )
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(repo, tid)
        _commit_all(repo, "close ticket state directly on root")

        before_main_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()

        with caplog.at_level("ERROR", logger="frob.tickets._land"):
            result = land(repo, tid, repo, dry_run=False)

        assert result.is_err
        assert result.danger_err == LandError.IncompleteLand
        assert "cwd" in caplog.text
        assert "ROOT checkout" in caplog.text

        # Refused before any git mutation at all: no merge/finalize/squash
        # commit, HEAD unmoved, tree exactly as found.
        assert (
            _run(["git", "rev-parse", "HEAD"], repo).stdout.strip() == before_main_sha
        )
        assert _status_ignoring_frob(repo) == ""
        still = load_all(repo).danger_ok[tid]
        assert still.state == TicketState.IN_PROGRESS

    def test_still_refuses_when_worktree_has_diverged_commits(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestLandRefusesWhenRootIsWorktree.test_still_refuses_when_worktree_has_diverged_commits  # noqa: E501
        # frob:tests src/frob/tickets/_land.py::_refuse_if_root_is_worktree kind="unit"
        """T-0761 regression preserved under a different name: the exact
        prior scenario (a new file committed directly on the branch `root`
        has checked out, then `land(repo, tid, repo)`) still refuses with
        `IncompleteLand` -- just via the new, earlier, more specific check
        rather than falling through to `_worktree_full_changeset`."""
        (repo / "src" / "new_feature2.py").write_text("# brand new feature code\n")
        _commit_all(repo, "add new_feature2.py directly on the shared branch")

        created = new_ticket(
            repo, _spec("Same-branch land 2", scope=("src/new_feature2.py",))
        )
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(repo, tid)
        _commit_all(repo, "close ticket state directly on the shared branch")

        result = land(repo, tid, repo, dry_run=False)

        assert result.is_err
        assert result.danger_err == LandError.IncompleteLand
        log = _run(["git", "log", "--oneline"], repo).stdout
        assert "land " not in log
        assert _status_ignoring_frob(repo) == ""


# frob:ticket T-1003
class TestLandChainedCdRootResolution:
    """T-1003 (churn item 4): `root` defaulting to the invoker's cwd makes
    it resolve to the IDENTICAL path as a REAL `--worktree` whenever the
    shell never `cd`ed out of the worktree first -- the "chained cd"
    ritual every land used to require. Unlike `TestLandRefusesWhenRootIs
    Worktree` (where `worktree` genuinely IS the primary checkout, no
    linked worktree exists at all, and refusing is correct), a REAL
    linked worktree's `git rev-parse --git-common-dir` resolves to a
    DIFFERENT primary checkout than `worktree` itself -- `land()` uses
    that to recover the true `root` and land onto it, transparently, with
    no manual `cd` required."""

    def test_root_equal_to_a_real_linked_worktree_resolves_and_lands(
        self, repo: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestLandChainedCdRootResolution.test_root_equal_to_a_real_linked_worktree_resolves_and_lands  # noqa: E501
        # frob:tests src/frob/tickets/_land.py::_resolve_primary_checkout kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-chained-cd", str(wt)], repo)

        created = new_ticket(wt, _spec("Chained-cd ticket"))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        _commit_all(wt, "advance chained-cd ticket")

        before_main_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()

        # Simulate a shell whose cwd never left the worktree: `root` here
        # is `wt`, identical to `--worktree wt`, exactly what `(cfg.
        # ticket_path or Path(".")).resolve()` produces from inside `wt`.
        with caplog.at_level("INFO", logger="frob.tickets._land"):
            result = land(wt, tid, wt, dry_run=False)

        assert result.is_ok, result.err
        assert "resolved the primary checkout" in caplog.text

        # It actually landed onto the TRUE primary checkout (`repo`), not
        # `wt` -- the ticket is done there, and `repo`'s HEAD moved.
        final_id = result.danger_ok.final_id
        landed = load_all(repo).danger_ok[final_id]
        assert landed.state == TicketState.DONE
        assert (
            _run(["git", "rev-parse", "HEAD"], repo).stdout.strip() != before_main_sha
        )

    def test_root_equal_to_the_primary_checkout_itself_still_refuses(
        self, repo: Path
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestLandChainedCdRootResolution.test_root_equal_to_the_primary_checkout_itself_still_refuses  # noqa: E501
        # frob:tests src/frob/tickets/_land.py::_resolve_primary_checkout kind="unit"
        """Sanity companion: when `--worktree` genuinely IS the primary
        checkout (no linked worktree at all, `TestLandRefusesWhenRootIs
        Worktree`'s scenario), `_resolve_primary_checkout` resolves back
        to the SAME path, so `root` is left unchanged and the original
        `_refuse_if_root_is_worktree` refusal still fires -- T-1003 never
        weakens that guard."""
        created = new_ticket(
            repo, _spec("Genuinely no worktree", scope=("src/noworktree.py",))
        )
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(repo, tid)
        _commit_all(repo, "close ticket state directly on root")

        result = land(repo, tid, repo, dry_run=False)

        assert result.is_err
        assert result.danger_err == LandError.IncompleteLand


class TestClaimDivergencePostMerge:
    """T-0754: `land`'s `passed`/`check_gates` callables re-verify a
    ticket's `### Captured claims` Done-report section against the
    POST-MERGE tree, mirroring D-05's evidence re-verification but for the
    captured test-count/gate-state CLAIMS themselves.

    Review round 2: `check_gates` returns `(errors, warnings, waived)`
    ints (never the raw `frob check` summary line, whose timing blob is
    nondeterministic even against an unchanged tree -- the FATAL this
    round's fix closes), and the test-count half is derived from the SAME
    `passed()` run D-05's own evidence re-verification already made (no
    separate `run_tests` parameter at the land layer any more)."""

    def _make_closeable_with_claims(
        self,
        root: Path,
        ticket_id: str,
        *,
        test_count: int,
        gate_errors: int = 0,
        gate_warnings: int = 0,
        gate_waived: int = 0,
    ) -> None:
        """Drive `ticket_id` to closeable (`_make_closeable`) then append a
        `### Captured claims` section to its Done report, exactly the shape
        `render_claims_block` writes."""
        _make_closeable(root, ticket_id)
        loaded = load_all(root)
        ticket = loaded.danger_ok[ticket_id]
        claims_block = (
            f"### Captured claims\n"
            f"- tests: {test_count} passed (from 1 evidence id(s))\n"
            f"- gates: {gate_errors} error(s), {gate_warnings} warning(s), "
            f"{gate_waived} waived"
        )
        ticket = ticket.model_copy(
            update={"body": ticket.body + "\n" + claims_block + "\n"}
        )
        assert write_ticket(root, ticket).is_ok

    def test_matching_claims_land_succeeds(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestClaimDivergencePostMerge.test_matching_claims_land_succeeds  # noqa: E501
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-claims-match", str(wt)], repo)

        created = new_ticket(wt, _spec("Ticket with matching captured claims"))
        assert created.is_ok
        tid = created.danger_ok.id
        self._make_closeable_with_claims(wt, tid, test_count=1)
        _commit_all(wt, "advance ticket with matching captured claims")

        result = land(
            repo,
            tid,
            wt,
            dry_run=False,
            passed=lambda ids: frozenset(ids),
            check_gates=lambda: (0, 0, 0),
        )

        assert result.is_ok

    def test_divergent_test_count_refuses_land(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestClaimDivergencePostMerge.test_divergent_test_count_refuses_land  # noqa: E501
        """`passed()` still reports the ticket's one real evidence id as
        PASSING (so D-05's own evidence re-verify stays green and does not
        pre-empt this with `NotCloseable`) -- but the Done report's own
        captured claim says 2 tests passed, which the real post-merge
        `passed()` run of 1 (D-05's own result, reused per review round 2
        fix #3) can never match. Isolates the `ClaimDivergence` path from
        D-05's own evidence-resolution/pass checks."""
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-claims-tests", str(wt)], repo)

        created = new_ticket(wt, _spec("Ticket with stale test-count claim"))
        assert created.is_ok
        tid = created.danger_ok.id
        self._make_closeable_with_claims(wt, tid, test_count=2)
        loaded = load_all(wt)
        ticket = loaded.danger_ok[tid]
        assert ticket.evidence == ("tests/test_x.py::test_ok",)
        _commit_all(wt, "advance ticket with stale test-count claim")

        main_log_before = _run(["git", "log", "--oneline", "--all"], repo).stdout
        wt_log_before = _run(["git", "log", "--oneline", "--all"], wt).stdout

        result = land(
            repo,
            tid,
            wt,
            dry_run=False,
            passed=lambda ids: frozenset(ids),
            check_gates=lambda: (0, 0, 0),
        )

        assert result.is_err
        assert result.danger_err == LandError.ClaimDivergence
        assert (
            _run(["git", "log", "--oneline", "--all"], repo).stdout == main_log_before
        )
        assert _run(["git", "log", "--oneline", "--all"], wt).stdout == wt_log_before

    def test_strictly_improved_test_count_auto_accepts_and_rewrites_recap(
        self, repo: Path
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestClaimDivergencePostMerge.test_strictly_improved_test_count_auto_accepts_and_rewrites_recap  # noqa: E501
        """T-1000 (churn item 1): a captured claim of 0/0 (recorded before
        the ticket's one real evidence id existed, or a stale recap from a
        send-back cycle) against a fresh post-merge re-run showing the
        real 1/1 passing is a STRICT IMPROVEMENT, never a divergence -- the
        land succeeds (no manual `frob ticket done-report` + re-land
        cycle) and the landed ticket's recap is rewritten to the fresh
        1/1 numbers."""
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-claims-improved", str(wt)], repo)

        created = new_ticket(wt, _spec("Ticket with stale 0/0 captured claim"))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        loaded = load_all(wt)
        ticket = loaded.danger_ok[tid]
        claims_block = (
            "### Captured claims\n"
            "- tests: 0 passed (from 0 evidence id(s))\n"
            "- gates: 0 error(s), 0 warning(s), 0 waived"
        )
        ticket = ticket.model_copy(
            update={"body": ticket.body + "\n" + claims_block + "\n"}
        )
        assert write_ticket(wt, ticket).is_ok
        _commit_all(wt, "advance ticket with stale 0/0 captured claim")

        result = land(
            repo,
            tid,
            wt,
            dry_run=False,
            passed=lambda ids: frozenset(ids),
            check_gates=lambda: (0, 0, 0),
        )

        assert result.is_ok
        final_id = result.danger_ok.final_id
        landed = load_all(repo).danger_ok[final_id]
        assert "- tests: 1 passed (from 1 evidence id(s))" in landed.body
        assert "- tests: 0 passed (from 0 evidence id(s))" not in landed.body

    def test_divergent_gate_errors_refuses_land(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestClaimDivergencePostMerge.test_divergent_gate_errors_refuses_land  # noqa: E501
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-claims-gates", str(wt)], repo)

        created = new_ticket(wt, _spec("Ticket with stale gate-state claim"))
        assert created.is_ok
        tid = created.danger_ok.id
        self._make_closeable_with_claims(wt, tid, test_count=1, gate_errors=0)
        _commit_all(wt, "advance ticket with stale gate-state claim")

        result = land(
            repo,
            tid,
            wt,
            dry_run=False,
            passed=lambda ids: frozenset(ids),
            check_gates=lambda: (3, 0, 0),
        )

        assert result.is_err
        assert result.danger_err == LandError.ClaimDivergence

    def test_lower_gate_error_count_than_claim_still_lands(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestClaimDivergencePostMerge.test_lower_gate_error_count_than_claim_still_lands  # noqa: E501
        """T-0846: a fresh post-merge error count LOWER than the captured
        claim (a sibling land fixed something on main between done-report
        time and this post-merge check, or a scoped-run WAIVE004 finding
        stopped counting) must not refuse the land -- only an INCREASE is
        the actionable signal. This fails against the pre-T-0846 strict
        `!=` comparison (3 != 0 also refused a strict decrease) and passes
        against the fixed `>` comparison."""
        wt = repo.parent / "wt"
        _run(
            ["git", "worktree", "add", "-b", "feature-claims-gate-decrease", str(wt)],
            repo,
        )

        created = new_ticket(wt, _spec("Ticket with an improved gate-state claim"))
        assert created.is_ok
        tid = created.danger_ok.id
        self._make_closeable_with_claims(wt, tid, test_count=1, gate_errors=3)
        _commit_all(wt, "advance ticket with an improved gate-state claim")

        result = land(
            repo,
            tid,
            wt,
            dry_run=False,
            passed=lambda ids: frozenset(ids),
            # Recorded claim was 3 error(s); the fresh post-merge check
            # now shows 0 -- an improvement, not a divergence.
            check_gates=lambda: (0, 0, 0),
        )

        assert result.is_ok

    # frob:tests tests/test_ticket_land.py::TestClaimDivergencePostMerge.test_masked_self_introduced_error_in_own_scope_still_refuses_via_identity  # noqa: E501
    def test_masked_self_introduced_error_in_own_scope_still_refuses_via_identity(
        self, repo: Path
    ) -> None:
        """T-0846 reviewer reject #1: a count-only comparison lets a land
        whose own diff introduces a NEW error sail through whenever an
        UNRELATED fix on the same branch removed MORE errors than that --
        the net total goes DOWN even though this land's own scope now has a
        genuinely new problem. Captured claim: 2 errors, with identities
        {RULE_A@src/other.py, RULE_B@src/other.py}. Fresh post-merge: 1
        error total (net LOWER, so the count-only `>` fallback alone would
        pass this land) but the ONE surviving finding is a brand-new
        RULE_C@src/feature.py -- inside THIS ticket's own declared scope
        (`src/**`) and absent from the captured claim. This must REFUSE via
        the identity-based comparison even though the raw count went down;
        it fails against a count-only `>` check (1 > 2 is False, would
        pass) and passes only when the identity/scope comparison is wired."""
        wt = repo.parent / "wt"
        _run(
            ["git", "worktree", "add", "-b", "feature-claims-masked", str(wt)],
            repo,
        )

        created = new_ticket(
            wt, _spec("Ticket whose own scope covers src/**", scope=("src/**",))
        )
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        loaded = load_all(wt)
        ticket = loaded.danger_ok[tid]
        claims = DoneReportClaims(
            test_count=1,
            evidence_count=1,
            gate_errors=2,
            gate_warnings=0,
            gate_waived=0,
            error_findings=frozenset(
                {("RULE_A", "src/other.py"), ("RULE_B", "src/other.py")}
            ),
        )
        ticket = ticket.model_copy(
            update={"body": ticket.body + "\n" + render_claims_block(claims) + "\n"}
        )
        assert write_ticket(wt, ticket).is_ok
        _commit_all(wt, "advance ticket with a to-be-masked gate-state claim")

        result = land(
            repo,
            tid,
            wt,
            dry_run=False,
            passed=lambda ids: frozenset(ids),
            # Scope-wide total DROPPED (2 -> 1) -- the count-only fallback
            # would pass this. But the one surviving finding is a NEW
            # identity, in a file this ticket's own scope covers.
            check_gates=lambda: (1, 0, 0),
            check_gate_findings=lambda: frozenset({("RULE_C", "src/feature.py")}),
        )

        assert result.is_err
        assert result.danger_err == LandError.ClaimDivergence

    def test_divergent_warning_or_waived_count_alone_still_lands(
        self, repo: Path
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestClaimDivergencePostMerge.test_divergent_warning_or_waived_count_alone_still_lands  # noqa: E501
        """Review round 2 fix #1: a warning/waived-count drift ALONE (errors
        unchanged) must never refuse a land -- repo-global warning counts
        legitimately move on a busy shared branch for reasons unrelated to
        this ticket's own work."""
        wt = repo.parent / "wt"
        _run(
            ["git", "worktree", "add", "-b", "feature-claims-warn-drift", str(wt)],
            repo,
        )

        created = new_ticket(wt, _spec("Ticket with warning-count drift only"))
        assert created.is_ok
        tid = created.danger_ok.id
        self._make_closeable_with_claims(
            wt, tid, test_count=1, gate_errors=0, gate_warnings=5, gate_waived=2
        )
        _commit_all(wt, "advance ticket with warning-count drift only")

        result = land(
            repo,
            tid,
            wt,
            dry_run=False,
            passed=lambda ids: frozenset(ids),
            # errors still 0 (matches the claim); warnings/waived drifted.
            check_gates=lambda: (0, 41, 9),
        )

        assert result.is_ok

    def test_no_claims_section_skips_reverification(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestClaimDivergencePostMerge.test_no_claims_section_skips_reverification  # noqa: E501
        """A Done report predating T-0754 (no `### Captured claims`
        section) lands normally even with `passed`/`check_gates`
        supplied -- there is nothing recorded to diverge from."""
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-no-claims", str(wt)], repo)

        created = new_ticket(wt, _spec("Ticket with no captured claims"))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        _commit_all(wt, "advance ticket with no captured claims")

        result = land(
            repo,
            tid,
            wt,
            dry_run=False,
            passed=lambda ids: frozenset(ids),
            check_gates=lambda: (99, 99, 99),
        )

        assert result.is_ok

    def test_unmeasured_fresh_check_skips_gate_reverification_land_proceeds(
        self, repo: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestClaimDivergencePostMerge.test_unmeasured_fresh_check_skips_gate_reverification_land_proceeds  # noqa: E501
        """T-0832: when the post-merge `check_gates()` callable cannot
        produce a gate-summary (e.g. the ticket lost its lease -- the real
        T-0830 incident), land must not compare a sentinel; it must skip
        the gate-state half of the claim comparison with an explicit
        logged notice and still land (the test-count half remains real and
        matching). No negative count appears anywhere in the notice."""
        import logging

        wt = repo.parent / "wt"
        _run(
            ["git", "worktree", "add", "-b", "feature-claims-unmeasurable", str(wt)],
            repo,
        )

        created = new_ticket(wt, _spec("Ticket whose fresh check cannot run"))
        assert created.is_ok
        tid = created.danger_ok.id
        self._make_closeable_with_claims(wt, tid, test_count=1, gate_errors=0)
        _commit_all(wt, "advance ticket with a recorded but now-unmeasurable claim")

        with caplog.at_level(logging.WARNING):
            result = land(
                repo,
                tid,
                wt,
                dry_run=False,
                passed=lambda ids: frozenset(ids),
                # T-0832: simulates the fresh post-merge check finding no
                # parsable gate-summary (no lease, a crash, ...).
                check_gates=lambda: None,
            )

        assert result.is_ok
        notices = [
            r.getMessage()
            for r in caplog.records
            if "skipping gate-state re-verification" in r.getMessage()
        ]
        assert notices, "expected an explicit skip notice, got none"
        # T-1635: the notice embeds `tid` (a randomly-minted `T-draft-
        # <hex>` id, `mint_draft_id`) verbatim, twice -- a bare `"-1" not
        # in notices[0]` check intermittently failed (~1/16 of runs,
        # independent of any load/scheduling) whenever that random hex
        # happened to start with "1" right after "draft-", producing the
        # substring "...draft-1..." and tripping the sentinel check on
        # pure coincidence, not a real `-1` sentinel leak. Strip the
        # ticket id out before checking so the assertion only ever
        # catches a genuine `-1` in the FORMATTED numbers this message is
        # actually guarding against.
        assert "-1" not in notices[0].replace(tid, "<TID>")

    def test_two_unmeasured_gate_claims_never_vacuously_match(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestClaimDivergencePostMerge.test_two_unmeasured_gate_claims_never_vacuously_match  # noqa: E501
        """T-0832 regression: the T-0830 incident was NOT merely that land
        printed a nonsense message -- it was that a done-report capture
        that recorded an unmeasured claim (formerly `-1`) and a land-time
        fresh check that ALSO could not measure (formerly `-1`) compared
        as vacuously EQUAL, silently passing a re-verification that
        actually verified nothing. Reproduce both halves unmeasured (via
        the real `set_done_report` capture path, not a hand-built claims
        block) and assert the gate-state comparison is skipped -- not
        silently "passed" as equal -- while the land still succeeds
        because the skip is explicit, not a false positive masquerading as
        one."""
        wt = repo.parent / "wt"
        _run(
            ["git", "worktree", "add", "-b", "feature-claims-both-unmeasured", str(wt)],
            repo,
        )

        created = new_ticket(wt, _spec("Ticket with a fully unmeasured claim"))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)

        # Capture the Done report through the REAL `set_done_report` path
        # with a `check_gates` that cannot measure -- exactly what
        # `_check_gates_summary_fn` returns for a lease-less/crashed check
        # (T-0832: `None`, never `-1`).
        done = set_done_report(
            wt,
            tid,
            why="claims captured while gate state was unmeasurable",
            run_tests=lambda ids: len(ids),
            check_gates=lambda: None,
        )
        assert done.is_ok, done.err
        assert "### Captured claims" in done.danger_ok.body
        assert "unmeasured" in done.danger_ok.body
        # T-1635: same defensive strip as the sibling test above -- `tid`
        # is a randomly-minted `T-draft-<hex>` id that can coincidentally
        # embed the substring "-1"; excluding it keeps this assertion
        # honest about what it actually guards (no `-1` sentinel in a
        # FORMATTED number, not "the random id happens to avoid one").
        assert "-1" not in done.danger_ok.body.replace(tid, "<TID>")
        _commit_all(wt, "advance ticket with a fully unmeasured captured claim")

        result = land(
            repo,
            tid,
            wt,
            dry_run=False,
            passed=lambda ids: frozenset(ids),
            # Land's own fresh post-merge check ALSO cannot measure.
            check_gates=lambda: None,
        )

        # The land succeeds -- but via the explicit "nothing recorded to
        # compare" skip (claims.gate_errors is None), never via a -1 == -1
        # false-positive comparison, which is no longer representable at
        # all now that the sentinel does not exist.
        assert result.is_ok


class TestDoneReportThenLandRealClosuresEndToEnd:
    """T-0754 review round 2 fix #2: exercises the REAL production
    closures (`_run_tests_count_fn`/`_check_gates_summary_fn`/
    `_land_passed_fn`/`_land_collected_fn` -- the exact ones `frob ticket
    done-report`/`frob ticket land` wire in, no fakes) through a full
    done-report -> land cycle against an IDENTICAL fixture-repo tree.

    This is the test that would have caught the FATAL immediately: the
    pre-review-round-2 `_check_gates_summary_fn` captured the raw `frob
    check` summary LINE, timing blob included, which differs on every
    single invocation even against a completely unchanged tree -- so
    land's strict-equality re-verification refused EVERY land, including
    this ticket's own. Every other T-0754 test (`TestClaimDivergencePostMerge`
    above, `tests/test_ticket_done_report_claims.py`) uses fake
    `passed=lambda ids: ...`/`check_gates=lambda: ...` callables, which
    cannot see this class of bug at all -- only a real subprocess spawn,
    run twice, can."""

    def test_real_closures_done_report_then_land_succeeds(self, tmp_path: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestDoneReportThenLandRealClosuresEndToEnd.test_real_closures_done_report_then_land_succeeds  # noqa: E501
        from frob.app.ticket_runner import (
            _check_gates_summary_fn,
            _land_collected_fn,
            _land_passed_fn,
            _run_tests_count_fn,
        )
        from frob.gates import sweep_ticket

        # A deliberately tiny fixture repo -- one real, fast, passing
        # pytest test -- so the two real `frob check` spawns below (one at
        # done-report time, one at land time) stay cheap.
        main_repo = tmp_path / "main"
        _git_init(main_repo)
        atomic_write(ledger_path(main_repo), "# Tickets\n\n")
        tests_dir = main_repo / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_sample.py").write_text("def test_ok():\n    assert True\n")
        _commit_all(main_repo, "init")

        wt = tmp_path / "wt"
        _run(
            ["git", "worktree", "add", "-b", "feature-e2e-real-closures", str(wt)],
            main_repo,
        )

        created = new_ticket(wt, _spec("e2e real closures"))
        assert created.is_ok
        tid = created.danger_ok.id

        assert transition(wt, tid, TicketState.PLANNED).is_ok
        # T-0473: entering IN_PROGRESS records the cross-worktree lease
        # `frob check --ticket <id>` requires to run at all (otherwise it
        # refuses with "no recorded lease ... run: frob ticket start",
        # matching real `frob ticket start`'s own side effect).
        assert transition(wt, tid, TicketState.IN_PROGRESS).is_ok

        loaded = load_all(wt)
        ticket = loaded.danger_ok[tid]
        ticket = ticket.model_copy(
            update={"evidence": ("tests/test_sample.py::test_ok",)}
        )
        assert write_ticket(wt, ticket).is_ok

        # Record an initial pre-work sweep synchronously (real `frob
        # ticket start` does this via a background spawn -- inlined here
        # for test determinism) so PRE001 does not fire on the real
        # `frob check --ticket` spawns below.
        swept = sweep_ticket(wt, ticket)
        assert swept.is_ok

        done = set_done_report(
            wt,
            tid,
            why="real e2e closures -- done-report capture",
            run_tests=_run_tests_count_fn(wt),
            check_gates=_check_gates_summary_fn(wt, tid),
        )
        assert done.is_ok, done.err
        assert "### Captured claims" in done.danger_ok.body

        _commit_all(wt, "advance e2e ticket with real captured claims")

        # THE assertion: landing this ticket through its own feature must
        # succeed -- not refuse with ClaimDivergence just because the
        # SECOND real `frob check` spawn (here) reports a different
        # per-gate timing blob than the FIRST one (above) did, against the
        # exact same tree.
        result = land(
            main_repo,
            tid,
            wt,
            dry_run=False,
            collected=_land_collected_fn(wt),
            passed=_land_passed_fn(wt),
            check_gates=_check_gates_summary_fn(wt, tid),
        )
        assert result.is_ok, result.err


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


class TestLandInternalEnvThroughHook:
    """T-0828: every land-internal git commit spawn (worktree wip
    snapshot, main-into-worktree merge, finalize/close, main-side
    squash-apply) must set `FROB_LAND_INTERNAL=1` in the child env or a
    scaffolded T-0731 land-owned-files `pre-commit` hook deadlocks the
    land the moment any of those commits stages CHANGELOG.md."""

    def test_land_through_changelog_guard_hook_succeeds(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestLandInternalEnvThroughHook.test_land_through_changelog_guard_hook_succeeds  # noqa: E501
        (repo / "CHANGELOG.md").write_text("# Changelog\n")
        _commit_all(repo, "add changelog")
        _install_changelog_guard_hook(repo)

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-hook", str(wt)], repo)
        created = new_ticket(wt, _spec("Hits the hook", scope=("src/hooked.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "hooked.py").write_text("# hooked\n")
        # An uncommitted CHANGELOG.md edit gets swept into `land`'s own
        # wip-snapshot commit -- exactly the real T-0594 incident shape
        # (the wip commit, not a hand-authored one, staged the guarded
        # file and tripped the hook).
        (wt / "CHANGELOG.md").write_text("# Changelog\n\n## hooked\n")

        result = land(repo, tid, wt, dry_run=False)
        assert result.is_ok, result.err
        assert result.danger_ok.commit_sha is not None

    def test_land_internal_git_env_restores_prior_value(self) -> None:
        # frob:tests src/frob/tickets/_land_git_ops.py::_land_internal_git_env \
        # kind="unit"
        os.environ.pop("FROB_LAND_INTERNAL", None)
        with _land_git_ops_mod._land_internal_git_env():
            assert (
                os.environ.get("FROB_LAND_INTERNAL") == "1"
            )  # frob:waive SEC110 reason="synthetic test-only var this test itself sets"
        assert "FROB_LAND_INTERNAL" not in os.environ

        os.environ["FROB_LAND_INTERNAL"] = (
            "prior-value"  # frob:waive SEC110 reason="synthetic test-only var this test itself sets"
        )
        try:
            with _land_git_ops_mod._land_internal_git_env():
                assert (
                    os.environ.get("FROB_LAND_INTERNAL") == "1"
                )  # frob:waive SEC110 reason="synthetic test-only var this test itself sets"
            assert (
                os.environ.get("FROB_LAND_INTERNAL") == "prior-value"
            )  # frob:waive SEC110 reason="synthetic test-only var this test itself sets"
        finally:
            os.environ.pop("FROB_LAND_INTERNAL", None)


class TestGitFailureMessageCarriesStderr:
    """T-0828: a failed land-internal git spawn must surface its argv and
    stderr in the log line, not collapse to a bare `GitFailed`."""

    def test_describe_git_failure_includes_argv_and_stderr(self) -> None:
        # frob:tests src/frob/tickets/_land_git_ops.py::_describe_git_failure \
        # kind="unit"
        argv = ["git", "-C", "/tmp/repo", "commit", "-m", "x"]
        failed = Ok(
            ProcResult(
                argv=tuple(argv),
                returncode=1,
                stdout="",
                stderr="frob: refusing commit -- CHANGELOG.md is land-owned (T-0731)",
            )
        )
        message = _land_git_ops_mod._describe_git_failure(argv, failed)
        assert "git -C /tmp/repo commit -m x" in message
        assert "exit 1" in message
        assert "CHANGELOG.md is land-owned" in message

    def test_describe_git_failure_includes_spawn_error(self) -> None:
        # frob:tests src/frob/tickets/_land_git_ops.py::_describe_git_failure \
        # kind="unit"
        argv = ["git", "-C", "/tmp/repo", "commit", "-m", "x"]
        message = _land_git_ops_mod._describe_git_failure(argv, Err(GitError.GitFailed))
        assert "git -C /tmp/repo commit -m x" in message
        assert "spawn error" in message

    def test_wip_commit_failure_logs_stderr(
        self,
        repo: Path,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        # frob:tests src/frob/tickets/_land_git_ops.py::_do_wip_commit kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-l8", str(wt)], repo)
        created = new_ticket(wt, _spec("Whatever", scope=("src/l8.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "l8.py").write_text("# l8\n")

        _failing_run_argv(
            monkeypatch,
            lambda argv: str(wt) in argv and "commit" in argv,
            hard_err=False,
        )
        with caplog.at_level("ERROR", logger="frob.tickets._land"):
            result = land(repo, tid, wt, dry_run=False)
        assert result.is_err
        assert result.danger_err == LandError.GitFailed
        assert any("simulated failure" in r.message for r in caplog.records)


# frob:ticket T-0755
class TestMutationEvidencePrecheck:
    """T-0755: `_check_mutation_evidence` blocks a security/bug-kind
    ticket's land on an ERROR-severity TEST016 finding, but only WARNs
    (does not block) every other kind -- unit-level over the private
    helper (same posture as `TestGitFailureMessageCarriesStderr` above),
    isolating the severity-gate decision from a full land() run."""

    def _ticket(self, kind: TicketKind) -> Any:
        from datetime import date as _date

        from frob.tickets._models import Ticket

        return Ticket(
            id="T-0900",
            title="sample",
            state=TicketState.IN_PROGRESS,
            kind=kind,
            origin=Origin.HUMAN,
            created=_date(2026, 1, 1),
            blocked_by=(),
            parent=None,
            scope=("m.py",),
            evidence=("test_m.py::test_add",),
            attachments=(),
            body="## Description\nx\n",
        )

    def test_security_kind_error_finding_blocks(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestMutationEvidencePrecheck.test_security_kind_error_finding_blocks  # noqa: E501
        from frob.gates._models import Severity, Violation

        ticket = self._ticket(TicketKind.SECURITY)
        import frob.gates as _gates_mod

        monkeypatch.setattr(
            _gates_mod,
            "mutation_evidence_violations",
            lambda *a, **k: (
                Violation(
                    rule="TEST016",
                    severity=Severity.ERROR,
                    file="m.py",
                    line=0,
                    message="TEST016: confirmatory-only",
                ),
            ),
        )
        result = _land_mod._check_mutation_evidence(tmp_path, ticket, "main")
        assert result.is_err
        assert result.danger_err == LandError.EvidenceConfirmatoryOnly

    def test_feature_kind_warn_finding_does_not_block(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestMutationEvidencePrecheck.test_feature_kind_warn_finding_does_not_block  # noqa: E501
        from frob.gates._models import Severity, Violation

        ticket = self._ticket(TicketKind.FEATURE)
        import frob.gates as _gates_mod

        monkeypatch.setattr(
            _gates_mod,
            "mutation_evidence_violations",
            lambda *a, **k: (
                Violation(
                    rule="TEST016",
                    severity=Severity.WARN,
                    file="m.py",
                    line=0,
                    message="TEST016: confirmatory-only",
                ),
            ),
        )
        result = _land_mod._check_mutation_evidence(tmp_path, ticket, "main")
        assert result.is_ok

    def test_no_findings_is_ok(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests \
        # tests/test_ticket_land.py::TestMutationEvidencePrecheck.test_no_findings_is_ok
        ticket = self._ticket(TicketKind.SECURITY)
        import frob.gates as _gates_mod

        monkeypatch.setattr(
            _gates_mod, "mutation_evidence_violations", lambda *a, **k: ()
        )
        result = _land_mod._check_mutation_evidence(tmp_path, ticket, "main")
        assert result.is_ok

    def test_skip_flag_bypasses_error_finding_but_still_logs(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestMutationEvidencePrecheck.test_skip_flag_bypasses_error_finding_but_still_logs  # noqa: E501
        from frob.gates._models import Severity, Violation

        ticket = self._ticket(TicketKind.SECURITY)
        import frob.gates as _gates_mod

        monkeypatch.setattr(
            _gates_mod,
            "mutation_evidence_violations",
            lambda *a, **k: (
                Violation(
                    rule="TEST016",
                    severity=Severity.ERROR,
                    file="m.py",
                    line=0,
                    message="TEST016: confirmatory-only",
                ),
            ),
        )
        result = _land_mod._check_mutation_evidence(tmp_path, ticket, "main", skip=True)
        assert result.is_ok


# frob:ticket T-0854
class TestLiveTrackerCitationPrecheck:
    """T-0854: `_check_live_tracker_citations` blocks land when a registry
    disposition or waiver still cites the landing ticket as its live
    tracker -- unit-level over the private helper (same posture as
    `TestMutationEvidencePrecheck` above), isolating the refusal decision
    from a full land() run."""

    def _ticket_t0900(self) -> Any:
        from frob.tickets._models import Ticket

        return Ticket(
            id="T-0900",
            title="sample",
            state=TicketState.IN_PROGRESS,
            kind=TicketKind.FEATURE,
            origin=Origin.HUMAN,
            created=date(2026, 1, 1),
            scope=("m.py",),
            evidence=("test_m.py::test_add",),
            body="## Description\nx\n",
        )

    def test_citations_found_blocks(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestLiveTrackerCitationPrecheck.test_citations_found_blocks  # noqa: E501
        import frob.tickets._live_tracker as _live_tracker_mod

        monkeypatch.setattr(
            _live_tracker_mod,
            "live_tracker_citations",
            lambda *a, **k: ("docs/design/registry/patterns.yaml:3: deferred:T-0900",),
        )
        result = _land_mod._check_live_tracker_citations(
            tmp_path, self._ticket_t0900(), "main"
        )
        assert result.is_err
        assert result.danger_err == LandError.LiveTrackerCited

    def test_no_citations_is_ok(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestLiveTrackerCitationPrecheck.test_no_citations_is_ok  # noqa: E501
        import frob.tickets._live_tracker as _live_tracker_mod

        monkeypatch.setattr(
            _live_tracker_mod, "live_tracker_citations", lambda *a, **k: ()
        )
        result = _land_mod._check_live_tracker_citations(
            tmp_path, self._ticket_t0900(), "main"
        )
        assert result.is_ok


# frob:ticket T-0755
class TestSkipMutationEvidenceCliWiring:
    """T-0755 reviewer round 2 finding 4: `frob ticket land
    --skip-mutation-evidence` must actually parse and reach `AppConfig`,
    and default to `False` when omitted -- the exact boolean default this
    ticket's own self-check (`test_self_check_t0755_own_diff_zero_error_
    findings`) caught as an UNTESTED mutant on first landing this flag."""

    def test_flag_parses_to_true(self, tmp_path: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestSkipMutationEvidenceCliWiring.test_flag_parses_to_true  # noqa: E501
        from frob.__main__ import _build_parser
        from frob.app.config import AppConfig

        parser = _build_parser()
        args = parser.parse_args(
            [
                "ticket",
                "land",
                "T-0001",
                "--worktree",
                str(tmp_path),
                "--skip-mutation-evidence",
                "--path",
                str(tmp_path),
            ]
        )
        cfg = AppConfig.from_external(args, tmp_path / "pyproject.toml")
        assert cfg.ticket_skip_mutation_evidence is True

    def test_flag_omitted_defaults_false(self, tmp_path: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestSkipMutationEvidenceCliWiring.test_flag_omitted_defaults_false  # noqa: E501
        from frob.__main__ import _build_parser
        from frob.app.config import AppConfig

        parser = _build_parser()
        args = parser.parse_args(
            [
                "ticket",
                "land",
                "T-0001",
                "--worktree",
                str(tmp_path),
                "--path",
                str(tmp_path),
            ]
        )
        cfg = AppConfig.from_external(args, tmp_path / "pyproject.toml")
        assert cfg.ticket_skip_mutation_evidence is False


# frob:ticket T-0844
class TestCloseSkipMutationEvidenceCliWiring:
    """T-0844 rework (reviewer REJECT): the close-path twin of
    `TestSkipMutationEvidenceCliWiring` above -- `frob ticket close
    --skip-mutation-evidence` must actually parse and reach `AppConfig`,
    and default to `False` when omitted, the exact boolean-default shape
    T-0755's own self-check test flagged as an untested mutant on
    `ticket_skip_mutation_evidence` the first time that flag landed. This
    is the same untested-default hole T-0844 originally left open on its
    OWN new `ticket_close_skip_mutation_evidence` field."""

    def test_flag_parses_to_true(self, tmp_path: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestCloseSkipMutationEvidenceCliWiring.test_flag_parses_to_true  # noqa: E501
        from frob.__main__ import _build_parser
        from frob.app.config import AppConfig

        parser = _build_parser()
        args = parser.parse_args(
            [
                "ticket",
                "close",
                "T-0001",
                "--skip-mutation-evidence",
                "--path",
                str(tmp_path),
            ]
        )
        cfg = AppConfig.from_external(args, tmp_path / "pyproject.toml")
        assert cfg.ticket_close_skip_mutation_evidence is True

    def test_flag_omitted_defaults_false(self, tmp_path: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestCloseSkipMutationEvidenceCliWiring.test_flag_omitted_defaults_false  # noqa: E501
        from frob.__main__ import _build_parser
        from frob.app.config import AppConfig

        parser = _build_parser()
        args = parser.parse_args(["ticket", "close", "T-0001", "--path", str(tmp_path)])
        cfg = AppConfig.from_external(args, tmp_path / "pyproject.toml")
        assert cfg.ticket_close_skip_mutation_evidence is False


# frob:ticket T-0844
class TestCloseMutationEvidenceForTicket:
    """T-0844 rework (reviewer REJECT): unit tests over
    `frob.app.ticket_runner._close_mutation_evidence_for_ticket` --
    proving the ERROR/WARN severity split and the branch-unresolvable
    ('cannot verify') case are each real, adversarially-covered behavior,
    not confirmatory-only lines T-0755's own self-check flagged."""

    def _ticket(self, kind: TicketKind = TicketKind.SECURITY) -> Any:
        from datetime import date as _date

        from frob.tickets._models import Ticket

        return Ticket(
            id="T-0900",
            title="sample",
            state=TicketState.IN_PROGRESS,
            kind=kind,
            origin=Origin.HUMAN,
            created=_date(2026, 1, 1),
            scope=("m.py",),
            evidence=("test_m.py::test_add",),
            body="## Description\nx\n",
        )

    def test_error_severity_finding_returns_false(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestCloseMutationEvidenceForTicket.test_error_severity_finding_returns_false  # noqa: E501
        from frob.gates._models import Severity, Violation

        _git_init(tmp_path)
        (tmp_path / "README.md").write_text("x\n")
        _commit_all(tmp_path, "init")
        import frob.gates as _gates_mod

        monkeypatch.setattr(
            _gates_mod,
            "mutation_evidence_violations",
            lambda *a, **k: (
                Violation(
                    rule="TEST016",
                    severity=Severity.ERROR,
                    file="m.py",
                    line=0,
                    message="TEST016: confirmatory-only",
                ),
            ),
        )
        from frob.app import ticket_runner

        result = ticket_runner._close_mutation_evidence_for_ticket(
            tmp_path, self._ticket()
        )
        assert result is False

    def test_warn_only_severity_returns_true(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestCloseMutationEvidenceForTicket.test_warn_only_severity_returns_true  # noqa: E501
        from frob.gates._models import Severity, Violation

        _git_init(tmp_path)
        (tmp_path / "README.md").write_text("x\n")
        _commit_all(tmp_path, "init")
        import frob.gates as _gates_mod

        monkeypatch.setattr(
            _gates_mod,
            "mutation_evidence_violations",
            lambda *a, **k: (
                Violation(
                    rule="TEST016",
                    severity=Severity.WARN,
                    file="m.py",
                    line=0,
                    message="TEST016: confirmatory-only",
                ),
            ),
        )
        from frob.app import ticket_runner

        result = ticket_runner._close_mutation_evidence_for_ticket(
            tmp_path, self._ticket()
        )
        assert result is True

    def test_no_findings_returns_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestCloseMutationEvidenceForTicket.test_no_findings_returns_none  # noqa: E501
        _git_init(tmp_path)
        (tmp_path / "README.md").write_text("x\n")
        _commit_all(tmp_path, "init")
        import frob.gates as _gates_mod

        monkeypatch.setattr(
            _gates_mod, "mutation_evidence_violations", lambda *a, **k: ()
        )
        from frob.app import ticket_runner

        result = ticket_runner._close_mutation_evidence_for_ticket(
            tmp_path, self._ticket()
        )
        assert result is None

    def test_unresolvable_branch_returns_none(self, tmp_path: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestCloseMutationEvidenceForTicket.test_unresolvable_branch_returns_none  # noqa: E501
        # tmp_path is NOT a git work tree -- current_branch(root) must
        # fail, and the whole check degrades to "skip", never a false
        # ERROR/OK verdict.
        from frob.app import ticket_runner

        result = ticket_runner._close_mutation_evidence_for_ticket(
            tmp_path, self._ticket()
        )
        assert result is None


# frob:ticket T-0417
class TestReverifyEvidenceForClose:
    """N-02 (docs/audits/tickets-testing-round2.md): unit tests over
    `frob.app.ticket_runner._reverify_evidence_for_close` -- proving the
    still-passes/no-longer-passes/no-evidence/collection-failed branches
    are each real, adversarially-covered behavior."""

    def _ticket(self) -> Any:
        from datetime import date as _date

        from frob.tickets._models import Ticket

        return Ticket(
            id="T-0900",
            title="sample",
            state=TicketState.IN_PROGRESS,
            kind=TicketKind.FEATURE,
            origin=Origin.HUMAN,
            created=_date(2026, 1, 1),
            scope=("m.py",),
            evidence=("test_m.py::test_add",),
            body="## Description\nx\n",
        )

    def test_no_non_cmd_evidence_returns_none(self, tmp_path: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestReverifyEvidenceForClose.test_no_non_cmd_evidence_returns_none  # noqa: E501
        from datetime import date as _date

        from frob.app import ticket_runner
        from frob.tickets._models import Ticket

        ticket = Ticket(
            id="T-0900",
            title="sample",
            state=TicketState.IN_PROGRESS,
            kind=TicketKind.DOCS,
            origin=Origin.HUMAN,
            created=_date(2026, 1, 1),
            evidence=("cmd:true exit=0 sha256=abcdef012345",),
            body="## Description\nx\n",
        )
        result = ticket_runner._reverify_evidence_for_close(tmp_path, ticket)
        assert result is None

    def test_collection_failure_returns_false(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestReverifyEvidenceForClose.test_collection_failure_returns_false  # noqa: E501
        from frob.app import ticket_runner

        monkeypatch.setattr(
            ticket_runner,
            "_collect_python_and_rust_ids",
            lambda root: Err("boom"),
        )
        result = ticket_runner._reverify_evidence_for_close(tmp_path, self._ticket())
        assert result is False

    def test_still_passing_returns_true(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestReverifyEvidenceForClose.test_still_passing_returns_true  # noqa: E501
        from frob.app import ticket_runner

        monkeypatch.setattr(
            ticket_runner,
            "_collect_python_and_rust_ids",
            lambda root: Ok((frozenset({"test_m.py::test_add"}), frozenset(), {})),
        )
        monkeypatch.setattr(
            ticket_runner,
            "_verify_ids_passing",
            lambda root, ids, py, rs, runners: frozenset(ids),
        )
        result = ticket_runner._reverify_evidence_for_close(tmp_path, self._ticket())
        assert result is True

    def test_no_longer_passing_returns_false(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestReverifyEvidenceForClose.test_no_longer_passing_returns_false  # noqa: E501
        from frob.app import ticket_runner

        monkeypatch.setattr(
            ticket_runner,
            "_collect_python_and_rust_ids",
            lambda root: Ok((frozenset({"test_m.py::test_add"}), frozenset(), {})),
        )
        monkeypatch.setattr(
            ticket_runner,
            "_verify_ids_passing",
            lambda root, ids, py, rs, runners: frozenset(),
        )
        result = ticket_runner._reverify_evidence_for_close(tmp_path, self._ticket())
        assert result is False


# frob:ticket T-0844
class TestCloseFailureHintMutationEvidence:
    """T-0844 rework (reviewer REJECT): `_close_failure_hint`'s
    `EvidenceConfirmatoryOnly` branch is real, dedicated behavior (names
    the skip-flag remedy), not indistinguishable from the generic
    fallback message -- the exact `compare Eq swapped` mutant T-0755's
    self-check caught as surviving."""

    def test_confirmatory_only_hint_names_skip_flag_remedy(self) -> None:
        # frob:tests tests/test_ticket_land.py::TestCloseFailureHintMutationEvidence.test_confirmatory_only_hint_names_skip_flag_remedy  # noqa: E501
        from frob.app.ticket_runner import _close_failure_hint
        from frob.tickets._models import TicketError, TicketState

        hint = _close_failure_hint(
            "T-0900", TicketState.IN_PROGRESS, TicketError.EvidenceConfirmatoryOnly
        )
        assert "--skip-mutation-evidence" in hint
        assert "TEST016" in hint

    def test_other_error_does_not_name_skip_flag_remedy(self) -> None:
        # frob:tests tests/test_ticket_land.py::TestCloseFailureHintMutationEvidence.test_other_error_does_not_name_skip_flag_remedy  # noqa: E501
        from frob.app.ticket_runner import _close_failure_hint
        from frob.tickets._models import TicketError, TicketState

        hint = _close_failure_hint(
            "T-0900", TicketState.IN_PROGRESS, TicketError.MissingEvidence
        )
        assert "--skip-mutation-evidence" not in hint


# frob:ticket T-0844
class TestCloseSkipMutationEvidenceBypass:
    """T-0844 rework (reviewer REJECT): `_close`'s
    `mutation_evidence is False and cfg.ticket_close_skip_mutation_evidence`
    guard -- both operands genuinely matter (kills `bool False negated`
    and `boolop And swapped`), exercised end to end through a real
    `frob ticket close` call rather than asserted in isolation."""

    def _write_closeable_security_ticket(
        self, root: Path, ticket_id: str = "T-0900"
    ) -> None:
        from datetime import date as _date

        from frob.tickets import Origin, Ticket, TicketKind, TicketState
        from frob.tickets._store import _serialize_ticket

        ticket = Ticket(
            id=ticket_id,
            title="sample",
            state=TicketState.IN_PROGRESS,
            kind=TicketKind.SECURITY,
            origin=Origin.HUMAN,
            created=_date(2026, 1, 1),
            evidence=("tests/test_thing.py::test_it",),
            body="## Description\nx\n\n## Done report\nDone.\n",
        )
        tickets_dir = root / "tickets"
        tickets_dir.mkdir(parents=True, exist_ok=True)
        (tickets_dir / f"{ticket_id}-sample.md").write_text(
            _serialize_ticket(ticket), encoding="utf-8"
        )

    def test_skip_flag_bypasses_error_verdict(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestCloseSkipMutationEvidenceBypass.test_skip_flag_bypasses_error_verdict  # noqa: E501
        from frob.app import ticket_runner
        from frob.app.config import AppConfig
        from frob.tickets import TicketState, load_all

        self._write_closeable_security_ticket(tmp_path)
        monkeypatch.setattr(
            ticket_runner,
            "_close_mutation_evidence_for_ticket",
            lambda root, ticket, base_ref="main": False,
        )
        monkeypatch.setattr(
            ticket_runner, "_covers_scope_for_ticket", lambda root, ticket: None
        )
        monkeypatch.setattr(
            ticket_runner, "_reverify_evidence_for_close", lambda root, ticket: None
        )
        cfg = AppConfig(ticket_id="T-0900", ticket_close_skip_mutation_evidence=True)
        ticket_runner._close(tmp_path, cfg)
        loaded = load_all(tmp_path)
        assert loaded.is_ok
        assert loaded.danger_ok["T-0900"].state == TicketState.DONE

    def test_no_skip_flag_refuses_on_error_verdict(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestCloseSkipMutationEvidenceBypass.test_no_skip_flag_refuses_on_error_verdict  # noqa: E501
        from frob.app import ticket_runner
        from frob.app.config import AppConfig
        from frob.tickets import TicketState, load_all

        self._write_closeable_security_ticket(tmp_path)
        monkeypatch.setattr(
            ticket_runner,
            "_close_mutation_evidence_for_ticket",
            lambda root, ticket, base_ref="main": False,
        )
        monkeypatch.setattr(
            ticket_runner, "_covers_scope_for_ticket", lambda root, ticket: None
        )
        monkeypatch.setattr(
            ticket_runner, "_reverify_evidence_for_close", lambda root, ticket: None
        )
        cfg = AppConfig(ticket_id="T-0900", ticket_close_skip_mutation_evidence=False)
        with pytest.raises(SystemExit):
            ticket_runner._close(tmp_path, cfg)
        loaded = load_all(tmp_path)
        assert loaded.is_ok
        assert loaded.danger_ok["T-0900"].state == TicketState.IN_PROGRESS


# frob:ticket T-0907
class TestVerifiedResetRoot:
    """T-0907: `_verified_reset_root` replaces every bare `git reset --hard`
    unwind in `land`'s squash-apply stage. A bare reset resolves its target
    from whatever `HEAD` happens to be AT RESET TIME -- the real incident
    this closes was a killed land whose unwind reset main to a stale tip
    ~60 commits behind, because at reset time root's `HEAD` had already
    (somehow) drifted from what the run started with. `_verified_reset_root`
    resets to an EXPLICIT sha captured at run start instead, and refuses
    loudly -- performing NO reset at all -- if root's current tip no longer
    matches it."""

    def test_resets_to_the_explicit_pre_land_tip_when_current_matches(
        self, repo: Path
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestVerifiedResetRoot.test_resets_to_the_explicit_pre_land_tip_when_current_matches  # noqa: E501
        pre = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        (repo / "scratch.txt").write_text("staged but never committed\n")
        _run(["git", "add", "scratch.txt"], repo)

        result = _land_git_ops_mod._verified_reset_root(repo, pre, "T-TEST")
        assert result.is_ok, result.err
        assert _run(["git", "rev-parse", "HEAD"], repo).stdout.strip() == pre
        assert _status_ignoring_frob(repo) == ""

    def test_refuses_and_does_not_reset_when_current_tip_has_drifted(
        self, repo: Path
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestVerifiedResetRoot.test_refuses_and_does_not_reset_when_current_tip_has_drifted  # noqa: E501
        pre = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        (repo / "another.txt").write_text("a real commit made after pre was captured\n")
        _commit_all(repo, "advance main past the recorded pre-land tip")
        drifted_tip = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        assert drifted_tip != pre

        result = _land_git_ops_mod._verified_reset_root(repo, pre, "T-TEST")
        assert result.is_err
        assert result.danger_err == LandError.GitFailed
        # NOT reset -- the drifted commit must still be there, untouched.
        assert _run(["git", "rev-parse", "HEAD"], repo).stdout.strip() == drifted_tip

    def test_drift_refusal_still_unstages_the_index(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestVerifiedResetRoot.test_drift_refusal_still_unstages_the_index  # noqa: E501
        """T-1740: the 2026-08-07 incident -- a refused land used to leave
        its own staged squash content sitting in root's index forever on
        the drift path, because a full `reset --hard` there is unsafe (it
        could destroy the concurrent commit that caused the drift). The
        fix unstages (never touches HEAD or the concurrent commit) even
        though it cannot fully unwind."""
        pre = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        # Land's own staged squash content, still in the index.
        (repo / "land_staged.txt").write_text("land's own staged squash content\n")
        _run(["git", "add", "land_staged.txt"], repo)
        # A concurrent, unrelated real commit that moved HEAD past `pre`.
        (repo / "concurrent.txt").write_text("a real concurrent commit\n")
        _commit_all(repo, "advance main past the recorded pre-land tip")
        drifted_tip = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        assert drifted_tip != pre

        result = _land_git_ops_mod._verified_reset_root(repo, pre, "T-TEST")
        assert result.is_err
        assert result.danger_err == LandError.GitFailed
        # The concurrent commit survives untouched -- never reset.
        assert _run(["git", "rev-parse", "HEAD"], repo).stdout.strip() == drifted_tip
        assert (repo / "concurrent.txt").exists()
        # But the index no longer holds land's own staged content -- a
        # bystander's next bare `git commit` cannot sweep it up anymore.
        staged = _run(["git", "diff", "--cached", "--name-only"], repo).stdout.strip()
        assert staged == ""

    def test_unstage_index_only_never_moves_head_or_touches_tracked_content(
        self, repo: Path
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestVerifiedResetRoot.test_unstage_index_only_never_moves_head_or_touches_tracked_content  # noqa: E501
        head_before = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        (repo / "new_staged.txt").write_text("new staged file\n")
        _run(["git", "add", "new_staged.txt"], repo)

        result = _land_git_ops_mod._unstage_index_only(repo)
        assert result.is_ok, result.err
        # HEAD never moved.
        assert _run(["git", "rev-parse", "HEAD"], repo).stdout.strip() == head_before
        # Unstaged, but the file itself (an untracked leftover) still exists.
        staged = _run(["git", "diff", "--cached", "--name-only"], repo).stdout.strip()
        assert staged == ""
        assert (repo / "new_staged.txt").exists()


# frob:ticket T-1740
class TestDescribeRootDirtNamesStagedState:
    """T-1740: `DirtyMain`'s message used to say only "uncommitted
    changes," which reads as working-tree edits and sent an agent
    looking for the wrong thing when the real cause was a PRIOR land's
    leftover STAGED index. `describe_root_dirt` now calls staged state
    out explicitly and first."""

    def test_working_tree_only_dirt_is_unchanged(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestDescribeRootDirtNamesStagedState.test_working_tree_only_dirt_is_unchanged  # noqa: E501
        (repo / "modified.txt").write_text("unstaged edit\n")
        described = _land_git_ops_mod.describe_root_dirt(repo)
        assert "modified.txt" in described
        assert "STAGED" not in described

    def test_staged_dirt_is_called_out_explicitly(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestDescribeRootDirtNamesStagedState.test_staged_dirt_is_called_out_explicitly  # noqa: E501
        (repo / "staged.txt").write_text("staged leftover\n")
        _run(["git", "add", "staged.txt"], repo)
        described = _land_git_ops_mod.describe_root_dirt(repo)
        assert "STAGED" in described
        assert "staged.txt" in described

    def test_porcelain_dirty_paths_staged_only_reports_index_status(
        self, repo: Path
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestDescribeRootDirtNamesStagedState.test_porcelain_dirty_paths_staged_only_reports_index_status  # noqa: E501
        (repo / "staged.txt").write_text("staged\n")
        _run(["git", "add", "staged.txt"], repo)
        (repo / "unstaged.txt").write_text("unstaged\n")

        staged_only = _land_git_ops_mod._porcelain_dirty_paths_staged(repo)
        assert staged_only == ("staged.txt",)


# frob:ticket T-1740
class TestCommitSquashApplyUnwindsOnCommitFailure:
    """T-1740's audit found this the ONE real gap: every other failure
    path in the squash-apply pipeline already unwinds via
    `_verified_reset_root`, but `_commit_squash_apply` -- the LAST step,
    the actual `git commit` -- used to just tell the operator to clean up
    root by hand on failure, leaving the fully-staged squash sitting in
    the index."""

    def test_commit_failure_unwinds_the_staged_squash(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestCommitSquashApplyUnwindsOnCommitFailure.test_commit_failure_unwinds_the_staged_squash  # noqa: E501
        pre = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        (repo / "staged_by_land.txt").write_text("staged squash content\n")
        _run(["git", "add", "staged_by_land.txt"], repo)

        ticket = Ticket(
            id="T-9999",
            title="test commit failure unwind",
            state=TicketState.IN_PROGRESS,
            kind=TicketKind.BUG,
            origin=Origin.HUMAN,
            created=date(2026, 1, 1),
        )

        _failing_run_argv(
            monkeypatch,
            lambda argv: "commit" in argv and "-m" in argv,
        )

        result = _land_squash_mod._commit_squash_apply(
            repo, ticket, "T-9999", pre_land_tip=pre
        )
        assert result.is_err
        assert result.danger_err == LandError.CommitFailed
        # The staged squash was unwound -- root is back to its pre-land
        # tip, clean, nothing left for a bystander's next commit to sweep.
        assert _run(["git", "rev-parse", "HEAD"], repo).stdout.strip() == pre
        assert _status_ignoring_frob(repo) == ""


# frob:ticket T-0907
class TestLandRepairMarker:
    """T-0907: `_repair_stale_land_marker` reconciles a crashed land's
    leftover land-repair marker at the start of the NEXT `land()` call
    against the same root/ticket."""

    def test_no_marker_is_a_silent_no_op(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestLandRepairMarker.test_no_marker_is_a_silent_no_op  # noqa: E501
        result = _land_mod._repair_stale_land_marker(repo)
        assert result.is_ok

    def test_repair_resets_root_when_current_tip_matches_the_marker(
        self, repo: Path
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestLandRepairMarker.test_repair_resets_root_when_current_tip_matches_the_marker  # noqa: E501
        pre = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        _land_mod._write_land_repair_marker(repo, "T-9999", pre)
        (repo / "leftover.txt").write_text("leftover staged squash content\n")
        _run(["git", "add", "leftover.txt"], repo)

        result = _land_mod._repair_stale_land_marker(repo)
        assert result.is_ok, result.err
        assert _run(["git", "rev-parse", "HEAD"], repo).stdout.strip() == pre
        assert _status_ignoring_frob(repo) == ""
        marker = _land_mod._land_repair_marker_path(repo, "T-9999")
        assert not marker.exists()

    def test_repair_refuses_loudly_when_current_tip_has_drifted_from_the_marker(
        self, repo: Path
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestLandRepairMarker.test_repair_refuses_loudly_when_current_tip_has_drifted_from_the_marker  # noqa: E501
        pre = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        _land_mod._write_land_repair_marker(repo, "T-9999", pre)
        (repo / "advance.txt").write_text("a real commit landed since the marker\n")
        _commit_all(repo, "advance main past the marker's recorded tip")
        drifted = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()

        result = _land_mod._repair_stale_land_marker(repo)
        assert result.is_err
        assert result.danger_err == LandError.GitFailed
        # refuses WITHOUT resetting -- the drifted commit must survive, and
        # the marker must be left in place for a human to inspect.
        assert _run(["git", "rev-parse", "HEAD"], repo).stdout.strip() == drifted
        marker = _land_mod._land_repair_marker_path(repo, "T-9999")
        assert marker.exists()


# frob:ticket T-1523
class TestPostLandVerifyPendingMarker:
    """T-1523: the post-commit twin of `TestLandRepairMarker` above --
    `_stale_post_land_verify_markers` reads back whatever `_write_post_
    land_verify_marker` recorded, read-only, for `_land_cmd._land_core`'s
    own `_report_stale_post_land_verify_markers` to reconcile at the start
    of the NEXT invocation."""

    def test_no_marker_is_a_silent_empty_result(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestPostLandVerifyPendingMarker.test_no_marker_is_a_silent_empty_result  # noqa: E501
        assert _land_mod._stale_post_land_verify_markers(repo) == ()

    def test_stale_marker_reports_verified_true_when_commit_is_a_clean_ancestor(
        self, repo: Path
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestPostLandVerifyPendingMarker.test_stale_marker_reports_verified_true_when_commit_is_a_clean_ancestor  # noqa: E501
        sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        _land_mod._write_post_land_verify_marker(repo, "T-9999", sha)

        found = _land_mod._stale_post_land_verify_markers(repo)
        assert found == (("T-9999", sha),)

        # Write + clear round-trips cleanly, like the T-0907 marker does.
        _land_mod._clear_post_land_verify_marker(repo, "T-9999")
        assert _land_mod._stale_post_land_verify_markers(repo) == ()

    def test_orphaned_marker_from_a_killed_prior_run_is_reported_and_cleared(
        self, repo: Path
    ) -> None:
        """The integration shape: a marker left behind by a "killed"
        prior land is picked up by `_land_cmd._land_core`'s own
        reconciliation call the NEXT time `frob ticket land` runs for a
        DIFFERENT ticket -- reported via a `LAND-PROOF-RECOVERED:` log
        line and cleared, never blocking the new ticket's own land."""
        # frob:tests tests/test_ticket_land.py::TestPostLandVerifyPendingMarker.test_orphaned_marker_from_a_killed_prior_run_is_reported_and_cleared  # noqa: E501
        from frob.app.ticket_runner._land_cmd import (
            _report_stale_post_land_verify_markers,
        )

        pre_existing_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        _land_mod._write_post_land_verify_marker(repo, "T-8888", pre_existing_sha)
        marker_path = _land_mod._land_verify_pending_marker_path(repo, "T-8888")
        assert marker_path.exists()

        _report_stale_post_land_verify_markers(repo)

        # Reconciled (cleared) regardless of verified outcome -- a
        # DIFFERENT, currently-landing ticket must never be blocked by a
        # PRIOR, unrelated ticket's leftover marker.
        assert not marker_path.exists()


def _t0907_child_land(
    root: Path, ticket_id: str, worktree: Path, ready_path: Path
) -> None:
    """Multiprocessing target (module-level so `fork` can spawn it, T-0907):
    monkeypatches `frob.tickets._land_squash.run_argv` (this CHILD
    process's own copy of the module, `fork` gives every child an
    independent copy-on-write memory image) so that once `land()`'s
    squash-apply merge onto `root` actually runs, it signals readiness
    (`ready_path`) and then sleeps well past however long the parent needs
    to `SIGKILL` this process -- reproducing "killed mid-staging"
    deterministically instead of relying on timing luck against a real
    580s coordinator timeout. T-1334: the squash-merge this patches now
    runs inside `_land_squash._squash_and_splice_ledger` (T-1186 originally
    put it in `_land_finalize`; T-1334 split that module further) --
    `land_mod.land` (the entry point actually invoked) still lives in
    `_land.py`."""

    import frob.tickets._land as land_mod
    import frob.tickets._land_squash as land_squash_mod

    real_run_argv = land_squash_mod.run_argv

    def _patched(
        argv: Sequence[str], *, cwd: Path | None = None, timeout_s: int | float = 30.0
    ) -> Result[ProcResult, GitError]:
        result = real_run_argv(argv, cwd=cwd, timeout_s=timeout_s)
        if "merge" in argv and "--squash" in argv:
            ready_path.write_text("ready\n")
            time.sleep(30)
        return result

    setattr(land_squash_mod, "run_argv", _patched)  # noqa: B010
    land_mod.land(root, ticket_id, worktree, dry_run=False)


# frob:ticket T-0907
class TestSigkillMidStaging:
    """T-0907's own regression lock: a real `SIGKILL` (uncatchable by any
    in-process signal handler, unlike SIGTERM) delivered while `land()` is
    mid-squash-apply onto root must leave root's tip completely unchanged,
    and the crash must be repairable by the next `land()` call for the same
    ticket -- the incident this ticket exists to close was the opposite: a
    killed land's own unwind reset main to a stale tip ~60 commits behind."""

    def test_sigkill_mid_squash_leaves_tip_unchanged_and_repairs_on_retry(
        self, repo: Path
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestSigkillMidStaging.test_sigkill_mid_squash_leaves_tip_unchanged_and_repairs_on_retry  # noqa: E501
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-kill", str(wt)], repo)
        created = new_ticket(wt, _spec("Add killable", scope=("src/killable.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "killable.py").write_text("# new file\n")
        _commit_all(wt, "add killable")

        before_main_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        ready_path = repo.parent / "ready.flag"

        ctx = multiprocessing.get_context("fork")
        proc = ctx.Process(target=_t0907_child_land, args=(repo, tid, wt, ready_path))
        proc.start()
        deadline = time.monotonic() + 20
        while not ready_path.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        assert ready_path.exists(), "child land() never reached the squash-apply step"
        assert proc.pid is not None
        os.kill(proc.pid, signal.SIGKILL)
        proc.join(timeout=15)
        assert not proc.is_alive()

        # The kill must not have moved root's tip AT ALL.
        after_kill_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        assert after_kill_sha == before_main_sha

        # A land-repair marker must survive the kill, recording exactly
        # this run's pre-land tip.
        marker_dir = repo / ".frob" / "land-repair"
        marker_files = list(marker_dir.glob("*.json"))
        assert len(marker_files) == 1, marker_files

        # The killed run already finalized/renumbered the draft id (and
        # closed it) in the worktree before its own crash -- exactly the
        # T-0795 retry shape (TestLandRetryAfterFinalizeThenFail above):
        # the retry addresses the ticket by its now-finalized id.
        wt_tickets = load_all(wt).danger_ok
        final_id = next(i for i, t in wt_tickets.items() if t.state == TicketState.DONE)

        # The next `land()` call for the same ticket reconciles the marker
        # (root's tip still matches it -- the crash happened before any
        # commit landed on root) and actually lands.
        result = land(repo, final_id, wt, dry_run=False)
        assert result.is_ok, result.err
        assert not marker_files[0].exists()
        assert (repo / "src" / "killable.py").exists()
        after_retry_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        assert after_retry_sha != before_main_sha
        assert _status_ignoring_frob(repo) == ""


class TestTick005LandRegressions:
    """T-0631: `_tick005_land_regressions` -- the TICK005-backed regression
    sweep run directly around a land's own squash-splice (mirrors
    `frob.gates._tick005_merge_state_regression`'s semantics without a
    two-parent merge commit, since a squash-apply never produces one)."""

    def test_no_regression_when_terminal_ticket_stays_terminal(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestTick005LandRegressions.test_no_regression_when_terminal_ticket_stays_terminal  # noqa: E501
        created = new_ticket(tmp_path, _spec("Widget"))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(tmp_path, tid)
        pre_text = ledger_path(tmp_path).read_text()

        regressions = _land_squash_mod._tick005_land_regressions(
            pre_text, pre_text, frozenset()
        )
        assert regressions == ()

    def test_detects_terminal_ticket_regressed_to_non_terminal(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestTick005LandRegressions.test_detects_terminal_ticket_regressed_to_non_terminal  # noqa: E501
        created = new_ticket(tmp_path, _spec("Widget"))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(tmp_path, tid)
        assert transition(tmp_path, tid, TicketState.DONE, covers_scope=True).is_ok
        pre_text = ledger_path(tmp_path).read_text()

        # Simulate the hand-resolved-conflict incident class: the "post"
        # ledger keeps the same id but reverts it to a non-terminal state.
        regressed = new_ticket(tmp_path, _spec("Widget2")).danger_ok
        assert _write_ticket_unchecked(
            tmp_path,
            regressed.model_copy(update={"id": tid, "state": TicketState.IN_PROGRESS}),
        ).is_ok
        post_text = ledger_path(tmp_path).read_text()

        regressions = _land_squash_mod._tick005_land_regressions(
            pre_text, post_text, frozenset()
        )
        assert regressions == (tid,)

    def test_archived_ids_are_excluded(self, tmp_path: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestTick005LandRegressions.test_archived_ids_are_excluded  # noqa: E501
        created = new_ticket(tmp_path, _spec("Widget"))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(tmp_path, tid)
        assert transition(tmp_path, tid, TicketState.DONE, covers_scope=True).is_ok
        pre_text = ledger_path(tmp_path).read_text()

        regressed = new_ticket(tmp_path, _spec("Widget2")).danger_ok
        assert _write_ticket_unchecked(
            tmp_path,
            regressed.model_copy(update={"id": tid, "state": TicketState.IN_PROGRESS}),
        ).is_ok
        post_text = ledger_path(tmp_path).read_text()

        # An archived id is exempt -- it is expected to be absent/stale in
        # the active ledger, not a regression.
        regressions = _land_squash_mod._tick005_land_regressions(
            pre_text, post_text, frozenset({tid})
        )
        assert regressions == ()

    def test_malformed_text_degrades_to_no_regressions(self, tmp_path: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestTick005LandRegressions.test_malformed_text_degrades_to_no_regressions  # noqa: E501
        malformed = "# Tickets\n\n<!-- ticket:T-0001 -->\nno frontmatter here\n"
        created = new_ticket(tmp_path, _spec("Widget"))
        assert created.is_ok
        valid_text = ledger_path(tmp_path).read_text()

        assert (
            _land_squash_mod._tick005_land_regressions(
                malformed, valid_text, frozenset()
            )
            == ()
        )
        assert (
            _land_squash_mod._tick005_land_regressions(
                valid_text, malformed, frozenset()
            )
            == ()
        )


class TestLandRefusesOnTerminalStateRegression:
    """T-0631: `land()` itself refuses (and unwinds root back to its
    pre-land tip) when the TICK005-backed regression sweep finds a
    regression in its own squash-splice."""

    def test_land_refuses_and_unwinds_when_sweep_finds_a_regression(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestLandRefusesOnTerminalStateRegression.test_land_refuses_and_unwinds_when_sweep_finds_a_regression  # noqa: E501
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-tick005", str(wt)], repo)
        created = new_ticket(wt, _spec("Add sprocket", scope=("src/sprocket.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "sprocket.py").write_text("# new sprocket\n")
        _commit_all(wt, "add sprocket")

        pre_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()

        monkeypatch.setattr(
            _land_squash_mod, "_tick005_land_regressions", lambda *a, **k: ("T-9999",)
        )

        result = land(repo, tid, wt, dry_run=False)
        assert result.is_err
        assert result.danger_err == LandError.TerminalStateRegression

        # root must be unwound back to exactly its pre-land tip -- nothing
        # from the refused land's squash-apply may remain staged/committed.
        assert _run(["git", "rev-parse", "HEAD"], repo).stdout.strip() == pre_sha
        assert _status_ignoring_frob(repo) == ""


class TestLandPushCliWiring:
    """T-0631: `frob ticket land --push` must actually parse and reach
    `AppConfig`, and default to `False` when omitted -- the same untested-
    boolean-default shape `TestSkipMutationEvidenceCliWiring` guards for
    the sibling `--skip-mutation-evidence` flag."""

    def test_flag_parses_to_true(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_ticket_land.py::TestLandPushCliWiring.test_flag_parses_to_true
        from frob.__main__ import _build_parser
        from frob.app.config import AppConfig

        parser = _build_parser()
        args = parser.parse_args(
            [
                "ticket",
                "land",
                "T-0001",
                "--worktree",
                str(tmp_path),
                "--push",
                "--path",
                str(tmp_path),
            ]
        )
        cfg = AppConfig.from_external(args, tmp_path / "pyproject.toml")
        assert cfg.ticket_land_push is True

    def test_flag_omitted_defaults_false(self, tmp_path: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestLandPushCliWiring.test_flag_omitted_defaults_false  # noqa: E501
        from frob.__main__ import _build_parser
        from frob.app.config import AppConfig

        parser = _build_parser()
        args = parser.parse_args(
            [
                "ticket",
                "land",
                "T-0001",
                "--worktree",
                str(tmp_path),
                "--path",
                str(tmp_path),
            ]
        )
        cfg = AppConfig.from_external(args, tmp_path / "pyproject.toml")
        assert cfg.ticket_land_push is False


# frob:ticket T-1057
class TestLandWorktreeResolvedAtArgParse:
    """T-1057: `frob ticket land <id> --worktree <RELATIVE path>` used to
    fail with `[Errno 2] No such file or directory: '<relative>/.venv/
    bin/python'` -- `ticket_runner._land`'s pre-`land()` spawn joined the
    still-relative `cfg.ticket_worktree` with `.venv/bin/python` and ran
    it with `cwd=` set to that same relative path, which the OS resolves
    against the CALLING process's cwd, not the target `cwd=`.
    `AppConfig.from_external` now resolves `ticket_worktree` to an
    absolute path at argument-parse time (the single place every `Path`-
    typed CLI arg is built), so a relative `--worktree` behaves
    identically to an absolute one from here on -- this test guards that
    `cfg.ticket_worktree` is always absolute regardless of how `--worktree`
    was spelled on the command line."""

    def test_relative_worktree_arg_resolves_to_absolute(self, tmp_path: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestLandWorktreeResolvedAtArgParse.test_relative_worktree_arg_resolves_to_absolute  # noqa: E501
        import os

        from frob.__main__ import _build_parser
        from frob.app.config import AppConfig

        worktree_dir = tmp_path / "worktree"
        worktree_dir.mkdir()
        old_cwd = Path.cwd()
        os.chdir(tmp_path)
        try:
            parser = _build_parser()
            args = parser.parse_args(
                [
                    "ticket",
                    "land",
                    "T-0001",
                    "--worktree",
                    "worktree",
                    "--path",
                    str(tmp_path),
                ]
            )
            cfg = AppConfig.from_external(args, tmp_path / "pyproject.toml")
        finally:
            os.chdir(old_cwd)

        assert cfg.ticket_worktree is not None
        assert cfg.ticket_worktree.is_absolute()
        assert cfg.ticket_worktree == worktree_dir.resolve()

    def test_absolute_worktree_arg_unchanged(self, tmp_path: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestLandWorktreeResolvedAtArgParse.test_absolute_worktree_arg_unchanged  # noqa: E501
        from frob.__main__ import _build_parser
        from frob.app.config import AppConfig

        parser = _build_parser()
        args = parser.parse_args(
            [
                "ticket",
                "land",
                "T-0001",
                "--worktree",
                str(tmp_path),
                "--path",
                str(tmp_path),
            ]
        )
        cfg = AppConfig.from_external(args, tmp_path / "pyproject.toml")
        assert cfg.ticket_worktree == tmp_path.resolve()


# frob:ticket T-0631
class TestPushAfterLand:
    """`_push_after_land` -- pushes root's current branch after a real
    land succeeds, never on a dry run, and exits non-zero (without
    unwinding the already-landed commit -- there is nothing left to
    unwind) on a push failure."""

    def _report(self, *, dry_run: bool, commit_sha: str | None = "deadbeef") -> Any:
        from frob.tickets._models import LandReport

        return LandReport(
            ticket_id="T-0001",
            final_id="T-0001",
            dry_run=dry_run,
            wip_committed=False,
            merged_main_into_worktree=False,
            ledger_spliced=not dry_run,
            commit_sha=commit_sha,
        )

    def test_dry_run_never_pushes(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests \
        # tests/test_ticket_land.py::TestPushAfterLand.test_dry_run_never_pushes
        from frob.app import ticket_runner

        def _fail_if_called(*a: Any, **k: Any) -> Any:
            raise AssertionError("git push must not be spawned on a dry run")

        monkeypatch.setattr(ticket_runner, "guarded_subprocess_run", _fail_if_called)
        ticket_runner._push_after_land(tmp_path, self._report(dry_run=True))

    def test_real_land_pushes_the_current_branch(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestPushAfterLand.test_real_land_pushes_the_current_branch  # noqa: E501
        from frob.app import ticket_runner

        calls: list[list[str]] = []

        def _fake(argv: list[str], **k: Any) -> Result[ProcResult, Any]:
            calls.append(argv)
            return Ok(ProcResult(argv=tuple(argv), returncode=0, stdout="", stderr=""))

        monkeypatch.setattr(ticket_runner, "guarded_subprocess_run", _fake)
        ticket_runner._push_after_land(repo, self._report(dry_run=False))

        assert len(calls) == 1
        assert calls[0][:3] == ["git", "-C", str(repo)]
        assert calls[0][3:] == ["push", "origin", "main"]

    def test_push_failure_exits_nonzero(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests \
        # tests/test_ticket_land.py::TestPushAfterLand.test_push_failure_exits_nonzero
        from frob.app import ticket_runner

        def _fake(argv: list[str], **k: Any) -> Result[ProcResult, Any]:
            return Ok(
                ProcResult(
                    argv=tuple(argv), returncode=1, stdout="", stderr="no such remote"
                )
            )

        monkeypatch.setattr(ticket_runner, "guarded_subprocess_run", _fake)
        with pytest.raises(SystemExit) as exc_info:
            ticket_runner._push_after_land(repo, self._report(dry_run=False))
        assert exc_info.value.code == 1

    def test_exec_disabled_exits_nonzero(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests \
        # tests/test_ticket_land.py::TestPushAfterLand.test_exec_disabled_exits_nonzero
        from frob.app import ticket_runner
        from frob.process._guard import ProcessGuardError

        def _fake(argv: list[str], **k: Any) -> Result[ProcResult, Any]:
            return Err(ProcessGuardError.ExecDisabled)

        monkeypatch.setattr(ticket_runner, "guarded_subprocess_run", _fake)
        with pytest.raises(SystemExit) as exc_info:
            ticket_runner._push_after_land(repo, self._report(dry_run=False))
        assert exc_info.value.code == 1


# frob:ticket T-1002
class TestUnionZoneMerge:
    """T-1002: append-only union-merge for the three chronic conflict
    hotspots (`[gates.severity]`, `_KNOWN_GATE_RULES`, `docs/audits/*.md`
    remediation logs) -- concurrent distinct appends compose with zero
    manual resolution; a true same-key contradiction still refuses."""

    def test_keyed_lines_union_composes(self) -> None:
        # frob:tests \
        # tests/test_ticket_land.py::TestUnionZoneMerge.test_keyed_lines_union_composes
        ours = '# comment for A\nRULEA = "error"\n'
        theirs = '# comment for B\nRULEB = "warn"\n'
        merged = _land_merge_zones_mod._union_keyed_chunks(
            ours, theirs, re.compile(r"^(?P<key>[A-Za-z0-9]+)\s*=")
        )
        assert merged is not None
        assert 'RULEA = "error"' in merged
        assert 'RULEB = "warn"' in merged

    def test_keyed_lines_union_refuses(self) -> None:
        # frob:tests \
        # tests/test_ticket_land.py::TestUnionZoneMerge.test_keyed_lines_union_refuses
        ours = 'RULEA = "error"\n'
        theirs = 'RULEA = "warn"\n'
        merged = _land_merge_zones_mod._union_keyed_chunks(
            ours, theirs, re.compile(r"^(?P<key>[A-Za-z0-9]+)\s*=")
        )
        assert merged is None

    def test_resolve_stages(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestUnionZoneMerge.test_resolve_stages
        target = repo / "frob.toml"
        target.write_text(
            "[gates.severity]\n"
            "# frob-zone-start gates.severity T-1002\n"
            "<<<<<<< HEAD\n"
            'RULEA = "error"\n'
            "=======\n"
            'RULEB = "warn"\n'
            ">>>>>>> main\n"
            "# frob-zone-end gates.severity T-1002\n"
        )
        _commit_all(repo, "conflict marker fixture")
        resolved = _land_merge_zones_mod._resolve_union_zone_conflicts(
            repo, {"frob.toml"}
        )
        assert resolved.is_ok
        assert resolved.danger_ok == frozenset()
        content = target.read_text()
        assert 'RULEA = "error"' in content
        assert 'RULEB = "warn"' in content
        assert "<<<<<<<" not in content

    def test_append_only_union_concatenates(self) -> None:
        # frob:tests tests/test_ticket_land.py::TestUnionZoneMerge.test_append_only_union_concatenates  # noqa: E501
        ours = "## Remediation log (T-A)\nfixed thing A\n"
        theirs = "## Remediation log (T-B)\nfixed thing B\n"
        merged = _land_merge_zones_mod._union_append_only(ours, theirs)
        assert "T-A" in merged and "T-B" in merged


# frob:ticket T-1011
class TestSyncGateRulesCallback:
    """T-1011(a): `land()`'s optional `sync_gate_rules` callback (invoked
    right after the REL001 bump, before the completeness assertion) lets a
    landing that changed `_KNOWN_GATE_RULES` auto-file `check-coverage.
    yaml` rows in the same commit, with the same fail-closed-unwind
    posture as `bump_version` on a real failure."""

    def test_sync_gate_rules_none_is_noop(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestSyncGateRulesCallback.test_sync_gate_rules_none_is_noop  # noqa: E501
        pre_land_tip = _land_git_ops_mod._rev_parse(repo, "HEAD").danger_ok
        result = _land_release_mod._apply_gate_rule_sync(
            repo, "T-0001", None, pre_land_tip
        )
        assert result.is_ok
        assert result.danger_ok is None

    def test_sync_gate_rules_applies_and_stages(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestSyncGateRulesCallback.test_sync_gate_rules_applies_and_stages  # noqa: E501
        pre_land_tip = _land_git_ops_mod._rev_parse(repo, "HEAD").danger_ok

        def _fake_sync(_root: Path, _tip: str) -> Result[tuple[str, ...] | None, Any]:
            return Ok(("SOME001",))

        result = _land_release_mod._apply_gate_rule_sync(
            repo, "T-0001", _fake_sync, pre_land_tip
        )
        assert result.is_ok
        assert result.danger_ok == ("SOME001",)
        # no unwind happened -- HEAD is untouched by a no-op callback.
        assert _land_git_ops_mod._rev_parse(repo, "HEAD").danger_ok == pre_land_tip

    def test_sync_gate_rules_failure_unwinds(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestSyncGateRulesCallback.test_sync_gate_rules_failure_unwinds  # noqa: E501
        pre_land_tip = _land_git_ops_mod._rev_parse(repo, "HEAD").danger_ok

        def _fake_sync(_root: Path, _tip: str) -> Result[tuple[str, ...] | None, Any]:
            return Err(_land_mod.LandError.GitFailed)

        result = _land_release_mod._apply_gate_rule_sync(
            repo, "T-0001", _fake_sync, pre_land_tip
        )
        assert result.is_err
        assert result.danger_err == _land_mod.LandError.GitFailed
        # the (no-op) unwind reset still leaves HEAD at pre_land_tip.
        assert _land_git_ops_mod._rev_parse(repo, "HEAD").danger_ok == pre_land_tip


class TestSyncGateRulesForLandDiffTarget:
    """T-1805 regression: `_sync_gate_rules_for_land`'s trigger diff must
    watch `src/frob/gates/_waive.py`, where `_KNOWN_GATE_RULES` has lived
    since T-1072 moved it out of `src/frob/gates/__init__.py`. Before the
    fix, a commit that only edited `_waive.py` (the ordinary shape of
    "add one rule id") never appeared in the old __init__.py-only diff, so
    the auto-sync silently no-oped on every real change -- confirmed root
    cause of PERF012/SYS108 landing unregistered."""

    def test_edit_to_waive_py_is_detected(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestSyncGateRulesForLandDiffTarget.test_edit_to_waive_py_is_detected  # noqa: E501
        from frob.app.ticket_runner import _sync_gate_rules_for_land

        pre_land_tip = _land_git_ops_mod._rev_parse(repo, "HEAD").danger_ok
        waive_path = repo / "src" / "frob" / "gates" / "_waive.py"
        waive_path.parent.mkdir(parents=True, exist_ok=True)
        waive_path.write_text(
            "_KNOWN_GATE_RULES = frozenset({'SOME001'})\n", encoding="utf-8"
        )
        run_argv(["git", "-C", str(repo), "add", "-A"])
        run_argv(["git", "-C", str(repo), "commit", "-m", "add rule id"])

        called: list[str] = []

        def _fake_scan(
            repo_root: Path, retired: frozenset[str] | None = None
        ) -> frozenset[str]:
            called.append("scanned")
            return frozenset({"SOME001"})

        # `_sync_gate_rules_for_land` imports `generated_gate_rule_ids`
        # locally at call time, so patching the source module's attribute
        # (rather than any already-bound name) is what the local import
        # actually re-resolves against.
        import frob.gates._rule_id_scan as _rule_id_scan_mod

        monkeypatch.setattr(_rule_id_scan_mod, "generated_gate_rule_ids", _fake_scan)
        result = _sync_gate_rules_for_land(repo, pre_land_tip)

        assert result.is_ok
        # the scanner must actually have been invoked -- proof the diff
        # against _waive.py was recognized as containing _KNOWN_GATE_RULES,
        # not silently short-circuited to Ok(None) the way the pre-fix
        # __init__.py-only diff target always did for this exact shape.
        assert called == ["scanned"]

    def test_unrelated_waive_py_edit_is_noop(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestSyncGateRulesForLandDiffTarget.test_unrelated_waive_py_edit_is_noop  # noqa: E501
        from frob.app.ticket_runner import _sync_gate_rules_for_land

        pre_land_tip = _land_git_ops_mod._rev_parse(repo, "HEAD").danger_ok
        waive_path = repo / "src" / "frob" / "gates" / "_waive.py"
        waive_path.parent.mkdir(parents=True, exist_ok=True)
        waive_path.write_text("# no rule-id literal here\n", encoding="utf-8")
        run_argv(["git", "-C", str(repo), "add", "-A"])
        run_argv(["git", "-C", str(repo), "commit", "-m", "unrelated edit"])

        result = _sync_gate_rules_for_land(repo, pre_land_tip)
        assert result.is_ok
        assert result.danger_ok is None


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


# frob:ticket T-1194
class TestNewerWinnerQualifiedPreferenceProperty:
    """T-0757: an establish-property obligation (INV008, `frob:invariant
    INV-043 establishes="..."` anchored on `_land._newer`) for T-0682's
    own qualified-preference rule (invariant spec:
    `invariants/INV-043.md`) -- exhaustively over the small state
    space `_newer_winner` actually discriminates on (rank in {0,1,2,3},
    Done-report presence, evidence count), rather than the hand-picked
    field-incident cases `TestSpliceLedgerRicherStatePreference` covers.
    Two properties, both restated from `_newer`'s own docstring tiers:

    1. TERMINAL SUPREMACY: a terminal side (rank 3) always beats a
       non-terminal side, regardless of richness.
    2. QUALIFIED RICHNESS: among two non-terminal sides, the richer side
       (by `_richness`'s tuple order) wins UNLESS the poorer side
       strictly outranks it -- a strictly-higher-rank poorer side always
       wins over a richer-but-lower-or-equal-rank side.
    """

    # frob:ticket T-1194
    # frob:tests tests/test_ticket_land.py::TestNewerWinnerQualifiedPreferenceProperty.test_terminal_side_always_wins_over_non_terminal  # noqa: E501
    @given(
        st.sampled_from([0, 1, 2]),
        st.booleans(),
        st.integers(min_value=0, max_value=3),
        st.sampled_from([TicketState.DONE, TicketState.DROPPED]),
        st.booleans(),
        st.integers(min_value=0, max_value=3),
    )
    def test_terminal_side_always_wins_over_non_terminal(
        self,
        non_terminal_rank: int,
        a_report: bool,
        a_evidence: int,
        terminal_state: TicketState,
        b_report: bool,
        b_evidence: int,
    ) -> None:
        a = _synthetic_ticket(
            "T-X",
            _STATE_BY_RANK[non_terminal_rank][0],
            has_report=a_report,
            evidence_count=a_evidence,
        )
        b = _synthetic_ticket(
            "T-X", terminal_state, has_report=b_report, evidence_count=b_evidence
        )
        assert _land_ledger_merge_mod._newer_winner(a, b) is b
        assert _land_ledger_merge_mod._newer_winner(b, a) is b

    # frob:ticket T-1194
    # frob:tests tests/test_ticket_land.py::TestNewerWinnerQualifiedPreferenceProperty.test_strictly_higher_rank_poorer_side_always_wins  # noqa: E501
    @given(
        st.sampled_from([0, 1, 2]),
        st.sampled_from([0, 1, 2]),
        st.integers(min_value=0, max_value=3),
        st.integers(min_value=0, max_value=3),
    )
    def test_strictly_higher_rank_poorer_side_always_wins(
        self,
        richer_rank: int,
        poorer_rank: int,
        richer_evidence: int,
        poorer_evidence: int,
    ) -> None:
        """A reportless-but-strictly-higher-rank side beats a
        reported-but-lower-rank side (the reviewer-caught inverse T-0682
        direction) -- richer here always carries the Done report, poorer
        never does, at a strictly lower rank."""
        if poorer_rank <= richer_rank:
            return
        richer = _synthetic_ticket(
            "T-X",
            _STATE_BY_RANK[richer_rank][0],
            has_report=True,
            evidence_count=richer_evidence,
        )
        poorer = _synthetic_ticket(
            "T-X",
            _STATE_BY_RANK[poorer_rank][0],
            has_report=False,
            evidence_count=poorer_evidence,
        )
        assert _land_ledger_merge_mod._newer_winner(richer, poorer) is poorer
        assert _land_ledger_merge_mod._newer_winner(poorer, richer) is poorer

    # frob:ticket T-1194
    # frob:tests tests/test_ticket_land.py::TestNewerWinnerQualifiedPreferenceProperty.test_richer_side_wins_at_equal_or_lower_rank  # noqa: E501
    @given(
        st.sampled_from([0, 1, 2]),
        st.sampled_from([0, 1, 2]),
        st.integers(min_value=0, max_value=3),
        st.integers(min_value=0, max_value=3),
    )
    def test_richer_side_wins_at_equal_or_lower_rank(
        self,
        richer_rank: int,
        poorer_rank: int,
        richer_evidence: int,
        poorer_evidence: int,
    ) -> None:
        """The original T-0682 incident shape: the richer (Done-reported)
        side wins whenever the poorer side does NOT strictly outrank it
        (equal rank, or the richer side is itself the higher-rank one)."""
        if poorer_rank > richer_rank:
            return
        richer = _synthetic_ticket(
            "T-X",
            _STATE_BY_RANK[richer_rank][0],
            has_report=True,
            evidence_count=richer_evidence,
        )
        poorer = _synthetic_ticket(
            "T-X",
            _STATE_BY_RANK[poorer_rank][0],
            has_report=False,
            evidence_count=poorer_evidence,
        )
        assert _land_ledger_merge_mod._newer_winner(richer, poorer) is richer
        assert _land_ledger_merge_mod._newer_winner(poorer, richer) is richer


# frob:ticket T-1256
class TestArchiveV2:
    """Ledger v2 design section 4.3: `archive` on a v2-mode tree does a
    plain `git mv tickets/T-#### tickets/archive/T-####` per done/dropped
    ticket, zero content rewrite -- eliminating the T-0959 archive-clobber
    failure mode structurally (no destination FILE is ever rewritten,
    only a rename) rather than merely guarding it the way
    `TestArchiveSpliceDiscipline` above guards the v1 monofile path."""

    def _v2_ticket(
        self,
        root: Path,
        ticket_id: str,
        *,
        state: TicketState = TicketState.DONE,
        blocked_by: tuple[str, ...] = (),
    ) -> Path:
        # Writes ticket.md directly (mirrors TestRenumberOneV2's own
        # `_v2_ticket` helper in tests/test_tickets_collision.py) so an
        # empty tmp_path's first ticket lands under tickets/<id>/ instead
        # of tickets.md, which write_ticket's own _store_mode dispatch
        # would otherwise choose for a tree with no v2 dir yet.
        from frob.tickets._models import Ticket
        from frob.tickets._store import _serialize_ticket, v2_ticket_path

        ticket = Ticket(
            id=ticket_id,
            title=f"Ticket {ticket_id}",
            state=state,
            kind=TicketKind.FEATURE,
            origin=Origin.AGENT,
            created=date.today(),
            blocked_by=blocked_by,
            evidence=("tests/test_x.py::test_ok",),
            body="## Description\nx\n\n## Done report\n\ndone\n",
        )
        path = v2_ticket_path(root, ticket_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_serialize_ticket(ticket), encoding="utf-8")
        return path

    # frob:ticket T-1256
    def test_archive_moves_directory_via_git_mv_no_content_rewrite(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/tickets/_archive.py::archive_v2 kind="unit"
        from frob.tickets import archive
        from frob.tickets._store import v2_archive_dir, v2_ticket_dir

        root = tmp_path / "repo"
        _git_init(root)
        path = self._v2_ticket(root, "T-0042")
        original_text = path.read_text(encoding="utf-8")
        _commit_all(root, "seed v2 ticket")

        result = archive(root)
        assert result.is_ok, result.err
        assert result.danger_ok == 1

        assert not v2_ticket_dir(root, "T-0042").exists()
        moved_path = v2_archive_dir(root, "T-0042") / "ticket.md"
        assert moved_path.exists()
        # Zero content rewrite: the moved file's bytes are byte-for-byte
        # identical to what git_mv_dir moved -- the AC's core claim.
        assert moved_path.read_text(encoding="utf-8") == original_text

        _run(["git", "add", "-A"], root)
        status = _run(["git", "status", "--porcelain"], root).stdout
        assert (
            "R  tickets/T-0042/ticket.md -> tickets/archive/T-0042/ticket.md" in status
        ), status

        # A second call is idempotent -- nothing left to archive.
        again = archive(root)
        assert again.is_ok and again.danger_ok == 0

    # frob:ticket T-1258
    # frob:doc docs/design/ledger-v2.md#43-archive-as-git-mv
    def test_first_ever_archive_uses_real_git_mv_not_rename_fallback(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests src/frob/tickets/_store.py::git_mv_dir kind="unit"
        # Chain-review fix: the VERY FIRST archive of a v2 repo (before
        # `tickets/archive/` has ever existed) used to silently take
        # `git_mv_dir`'s os.rename fallback -- `git mv` on a directory
        # refuses when the destination's PARENT does not exist yet, which
        # is exactly true on a repo's first-ever archive. Pre-creating the
        # parent (this fix) makes `git mv` itself succeed, so the fallback
        # log line must never fire here.
        from frob.tickets import archive

        root = tmp_path / "repo"
        _git_init(root)
        assert not (root / "tickets" / "archive").exists()
        self._v2_ticket(root, "T-0043")
        _commit_all(root, "seed v2 ticket")

        with caplog.at_level("DEBUG", logger="frob.tickets._store"):
            result = archive(root)
        assert result.is_ok, result.err
        assert result.danger_ok == 1
        assert "falling back to os.rename" not in caplog.text

    # frob:ticket T-1256
    def test_archive_v2_regression_two_sided_divergence_no_clobber(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/tickets/_archive.py::archive_v2 kind="unit"
        # Reproduces the T-0959 incident SHAPE (two branches each archive a
        # DIFFERENT ticket, then merge) against the v2 path: since each
        # archived ticket is its own disjoint git path, a real git merge
        # unions both sides with no custom splice code and no lost block --
        # unlike the v1 monofile path TestArchiveSpliceDiscipline guards.
        from frob.tickets import archive
        from frob.tickets._store import load_all, load_archive, write_ticket

        root = tmp_path / "repo"
        _git_init(root)
        self._v2_ticket(root, "T-0100")
        # T-0200 starts QUEUED (not archive-eligible yet) -- it only
        # becomes done+archived on the WORKTREE side, after main has
        # already branched and archived T-0100 -- the two-sided
        # divergence shape.
        self._v2_ticket(root, "T-0200", state=TicketState.QUEUED)
        _commit_all(root, "seed two v2 tickets")

        wt = tmp_path / "wt"
        _run(["git", "worktree", "add", "-b", "feature-archive", str(wt)], root)

        # Main archives T-0100 only, after the worktree branched.
        main_archived = archive(root)
        assert main_archived.is_ok and main_archived.danger_ok == 1
        _commit_all(root, "main archives T-0100")

        # The worktree, unaware of main's sweep, closes AND independently
        # archives T-0200 -- the exact two-sided-divergence shape.
        wt_loaded = load_all(wt)
        assert wt_loaded.is_ok
        wt_ticket = wt_loaded.danger_ok["T-0200"].model_copy(
            update={"state": TicketState.DONE}
        )
        assert write_ticket(wt, wt_ticket).is_ok
        # The worktree's own checkout still has T-0100 as active+done too
        # (its branch point predates main's archive commit) -- archiving
        # here independently re-archives T-0100 AND T-0200, the literal
        # T-0959 double-archive shape: both sides archive T-0100.
        wt_archived = archive(wt)
        assert wt_archived.is_ok and wt_archived.danger_ok == 2
        _commit_all(wt, "worktree closes and archives T-0200 (and re-archives T-0100)")

        merge_result = _run(["git", "merge", "--no-edit", "feature-archive"], root)
        assert merge_result.returncode == 0, merge_result.stderr

        active = load_all(root)
        assert active.is_ok
        assert "T-0100" not in active.danger_ok
        assert "T-0200" not in active.danger_ok

        archived = load_archive(root)
        assert archived.is_ok
        assert "T-0100" in archived.danger_ok, "main's own archive sweep was lost"
        assert "T-0200" in archived.danger_ok, (
            "the worktree's archive sweep was clobbered by main's -- the "
            "T-0959 shape this test guards against"
        )

    # frob:ticket T-1256
    def test_archived_v2_ticket_still_resolves_as_blocker(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_archive.py::load_queue kind="unit"
        from frob.tickets import archive, load_queue

        root = tmp_path / "repo"
        _git_init(root)
        self._v2_ticket(root, "T-0400")
        self._v2_ticket(
            root, "T-0500", state=TicketState.QUEUED, blocked_by=("T-0400",)
        )
        _commit_all(root, "seed blocker pair")

        archived_count = archive(root)
        assert archived_count.is_ok and archived_count.danger_ok == 1

        queue = load_queue(root)
        assert queue.is_ok, queue.err
        merged = queue.danger_ok.tickets
        assert "T-0400" in merged, "archived blocker no longer resolves"
        assert merged["T-0400"].state == TicketState.DONE
        assert "T-0500" in merged
        assert merged["T-0500"].blocked_by == ("T-0400",)

    # frob:ticket T-1491
    def test_v2_draft_survives_a_concurrent_worktree_restore(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestArchiveV2.test_v2_draft_survives_a_concurrent_worktree_restore  # noqa: E501
        """Regression for the T-1115/T-1126/T-1127/T-1128 draft-death
        shape (T-1259 acceptance[5], carried forward by this ticket): a
        draft ticket filed into a worktree, followed by the section 10b
        ledger-restore recipe (`git checkout main -- <ledger>`) another
        ticket in the SAME worktree runs before finalizing, used to WIPE
        the draft outright on the v1 monofile path -- because the whole
        ledger lives in one file, restoring main's copy of that file
        discards anything the worktree alone had written to it,
        including a draft nobody else has seen yet.

        On the v2 per-ticket-file path this class is structurally
        impossible: a draft is its own disjoint `tickets/T-draft-<hex>/
        ticket.md` file, never a section inside a shared ledger file, so
        there is no single-file "restore to main's copy" operation that
        could ever touch it. This reproduces the exact incident shape --
        main advances (landing an unrelated ticket) while a worktree
        independently files a draft, then the worktree does the
        equivalent of the section 10b restore (checking out main's
        ledger-relevant state) before its own final commit -- and asserts
        the draft file is untouched by either the restore or a
        subsequent merge back into main."""
        from frob.tickets import load_all
        from frob.tickets._store import v2_ticket_dir

        root = tmp_path / "repo"
        _git_init(root)
        self._v2_ticket(root, "T-0900", state=TicketState.QUEUED)
        _commit_all(root, "seed v2 repo")

        wt = tmp_path / "wt"
        _run(["git", "worktree", "add", "-b", "feature-draft", str(wt)], root)

        # Main advances independently (an unrelated ticket lands) after
        # the worktree branched off -- the same "main keeps moving while
        # you work" backdrop section 10b describes.
        main_ticket_path = self._v2_ticket(root, "T-1000", state=TicketState.QUEUED)
        assert main_ticket_path.exists()
        _commit_all(root, "main files an unrelated ticket")

        # The worktree, unaware of main's advance, files a brand-new
        # DRAFT (never seen by main, never committed anywhere else) --
        # the exact "original draft" this incident class loses.
        draft_path = self._v2_ticket(wt, "T-draft-deadbeef", state=TicketState.QUEUED)
        assert draft_path.exists()

        # Section 10b's restore recipe, applied here: bring the
        # worktree's tracked ledger-relevant state in line with main's
        # BEFORE the worktree's own final commit. On v1 this is
        # `git checkout main -- tickets.md`, which overwrites the whole
        # shared file and any draft section it held. On v2 there is no
        # single shared ledger file to check out -- the closest
        # structural equivalent is `git checkout main -- tickets/` for
        # the tracked (committed) subtree, which cannot reach a file
        # that was never committed in the first place.
        checkout_result = _run(["git", "checkout", "main", "--", "tickets/T-1000"], wt)
        assert checkout_result.returncode == 0, checkout_result.stderr

        # The draft, never committed, is untouched by the restore --
        # still on disk, still readable.
        assert draft_path.exists()
        wt_loaded = load_all(wt)
        assert wt_loaded.is_ok, wt_loaded.err
        assert "T-draft-deadbeef" in wt_loaded.danger_ok

        _commit_all(wt, "worktree commits its draft alongside restored state")

        merge_result = _run(["git", "merge", "--no-edit", "feature-draft"], root)
        assert merge_result.returncode == 0, merge_result.stderr

        merged = load_all(root)
        assert merged.is_ok, merged.err
        assert "T-draft-deadbeef" in merged.danger_ok, (
            "the worktree's draft was lost across restore+merge -- the "
            "TICK002/TICK006 draft-death shape this test guards against"
        )
        assert "T-1000" in merged.danger_ok, "main's own ticket was lost"
        assert v2_ticket_dir(root, "T-draft-deadbeef").exists()


# frob:ticket T-1349
class TestLandReleaseMonotonicityHelpers:
    """T-1349: T-1334's move of the REL001 monotonicity family into
    `_land_release.py` was landed with `--skip-mutation-evidence` on the
    claim that pre-existing structural coverage (via the full `land()`
    end-to-end tests elsewhere in this file) already proves these
    functions correct. These tests exercise each leaf function directly to
    kill the specific surviving mutants T-1349's mutation run found
    (boolop/compare swaps on the error-guard and monotonicity checks) --
    the exact claim mutation testing exists to falsify, not re-assert."""

    def test_read_root_pyproject_version_ok_but_nonzero_returncode_is_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestLandReleaseMonotonicityHelpers.test_read_root_pyproject_version_ok_but_nonzero_returncode_is_none  # noqa: E501
        """Kills the `or` -> `and` mutant on `_read_root_pyproject_version`'s
        error guard: `run_argv` succeeding (is_err=False) with a nonzero
        `returncode` (e.g. `git show` reporting a bad revision/path) must
        still read as "nothing to report" -- an `and` mutant would only
        treat `is_err` alone as the guard and fall through here."""

        def _fake_run_argv(argv: Sequence[str], **kwargs: Any) -> Any:
            return Ok(
                ProcResult(
                    argv=tuple(argv),
                    returncode=128,
                    stdout='version = "9.9.9"\n',
                    stderr="fatal: bad revision",
                )
            )

        monkeypatch.setattr(_land_release_mod, "run_argv", _fake_run_argv)
        result = _land_release_mod._read_root_pyproject_version(tmp_path, "deadbeef")
        assert result is None

    def test_read_root_manifest_version_ok_but_nonzero_returncode_is_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestLandReleaseMonotonicityHelpers.test_read_root_manifest_version_ok_but_nonzero_returncode_is_none  # noqa: E501
        """Same `or` -> `and` mutant, on `_read_root_manifest_version`'s
        identical guard shape."""

        def _fake_run_argv(argv: Sequence[str], **kwargs: Any) -> Any:
            return Ok(
                ProcResult(
                    argv=tuple(argv),
                    returncode=128,
                    stdout='{"version": "9.9.9"}',
                    stderr="fatal: bad revision",
                )
            )

        monkeypatch.setattr(_land_release_mod, "run_argv", _fake_run_argv)
        result = _land_release_mod._read_root_manifest_version(tmp_path, "deadbeef")
        assert result is None

    def test_monotonic_when_no_prior_version(self) -> None:
        # frob:tests tests/test_ticket_land.py::TestLandReleaseMonotonicityHelpers.test_monotonic_when_no_prior_version  # noqa: E501
        """`pre_bump_version=None` is vacuously monotonic."""
        assert _land_release_mod._release_bump_is_monotonic(None, "0.1.0") is True

    def test_fallback_path_equal_versions_not_monotonic(self) -> None:
        # frob:tests tests/test_ticket_land.py::TestLandReleaseMonotonicityHelpers.test_fallback_path_equal_versions_not_monotonic  # noqa: E501
        """Kills the `!=` -> `==` and `and` -> `or` mutants on the PEP-440
        parse-failure fallback: two EQUAL non-numeric versions must not be
        treated as monotonic (an `==` mutant would flip this, and an `or`
        mutant would treat equal-but-not-greater as monotonic since the
        left side of the fallback and-clause would already be enough)."""
        assert (
            _land_release_mod._release_bump_is_monotonic("nonnumeric", "nonnumeric")
            is False
        )

    def test_fallback_path_lesser_version_not_monotonic(self) -> None:
        # frob:tests tests/test_ticket_land.py::TestLandReleaseMonotonicityHelpers.test_fallback_path_lesser_version_not_monotonic  # noqa: E501
        """Kills the `>` -> other-comparator mutant on the same fallback:
        a strictly LESSER non-numeric string must not be monotonic."""
        assert (
            _land_release_mod._release_bump_is_monotonic(
                "zzz-nonnumeric", "aaa-nonnumeric"
            )
            is False
        )

    def test_fallback_path_greater_version_is_monotonic(self) -> None:
        # frob:tests tests/test_ticket_land.py::TestLandReleaseMonotonicityHelpers.test_fallback_path_greater_version_is_monotonic  # noqa: E501
        """Positive complement of the two fallback tests above: a
        genuinely greater non-numeric string IS monotonic."""
        assert (
            _land_release_mod._release_bump_is_monotonic(
                "aaa-nonnumeric", "zzz-nonnumeric"
            )
            is True
        )

    def test_log_monotonicity_refusal_quartet_desync_requires_all_three_legs(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestLandReleaseMonotonicityHelpers.test_log_monotonicity_refusal_quartet_desync_requires_all_three_legs  # noqa: E501
        """Kills the `and` -> `or` mutant on `quartet_desynced`'s three-leg
        check: a `pre_manifest_version` that is `None` (never observed at
        `pre_land_tip`) must NOT be treated as desynced even though the
        other two legs alone would satisfy an `or`-mutated check."""
        with caplog.at_level("ERROR", logger="frob.tickets._land_release"):
            _land_release_mod._log_monotonicity_refusal(
                "T-9999", "0.2.0", "0.2.0", None
            )
        assert "INCOHERENT" not in caplog.text

    def test_log_monotonicity_refusal_fires_on_genuine_desync(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestLandReleaseMonotonicityHelpers.test_log_monotonicity_refusal_fires_on_genuine_desync  # noqa: E501
        """Positive complement: all three legs present and manifest !=
        pre-bump DOES fire the INCOHERENT message."""
        with caplog.at_level("ERROR", logger="frob.tickets._land_release"):
            _land_release_mod._log_monotonicity_refusal(
                "T-9999", "0.3.0", "0.2.0", "0.1.0"
            )
        assert "INCOHERENT" in caplog.text

    def test_sync_uv_lock_ok_but_nonzero_returncode_on_git_add_is_failed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestLandReleaseMonotonicityHelpers.test_sync_uv_lock_ok_but_nonzero_returncode_on_git_add_is_failed  # noqa: E501
        """Kills the `or` -> `and` mutant on `_sync_uv_lock_for_land`'s
        `git add uv.lock` guard: `uv lock` itself succeeds, but the
        subsequent `git add` returns `Ok` with a nonzero returncode (e.g.
        `uv.lock` outside the repo's pathspec) -- must still refuse as
        `GitFailed`, not fall through to the success-log path an `and`
        mutant would take here."""
        (tmp_path / "pyproject.toml").write_text('[project]\nversion = "0.1.0"\n')

        def _fake_run_argv(argv: Sequence[str], **kwargs: Any) -> Any:
            if tuple(argv) == ("uv", "lock"):
                return Ok(
                    ProcResult(argv=tuple(argv), returncode=0, stdout="", stderr="")
                )
            return Ok(
                ProcResult(
                    argv=tuple(argv),
                    returncode=128,
                    stdout="",
                    stderr="fatal: pathspec did not match",
                )
            )

        monkeypatch.setattr(_land_release_mod, "run_argv", _fake_run_argv)
        result = _land_release_mod._sync_uv_lock_for_land(tmp_path, "T-9999")
        assert result.is_err
        assert result.danger_err == LandError.GitFailed

    def test_resync_release_manifest_ok_but_nonzero_returncode_on_git_add_is_failed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestLandReleaseMonotonicityHelpers.test_resync_release_manifest_ok_but_nonzero_returncode_on_git_add_is_failed  # noqa: E501
        """Kills the `or` -> `and` mutant on `_resync_release_manifest`'s
        `git add .frob-release.json` guard: the manifest write itself
        succeeds, but the subsequent `git add` returns `Ok` with a nonzero
        returncode -- must still refuse as `ReleaseBumpFailed`, not fall
        through to `Ok(None)` the way an `and` mutant would here."""
        (tmp_path / ".frob-release.json").write_text(
            '{"version": "0.1.0", "api": {}}\n'
        )

        def _fake_run_argv(argv: Sequence[str], **kwargs: Any) -> Any:
            return Ok(
                ProcResult(
                    argv=tuple(argv),
                    returncode=128,
                    stdout="",
                    stderr="fatal: pathspec did not match",
                )
            )

        monkeypatch.setattr(_land_release_mod, "run_argv", _fake_run_argv)
        result = _land_release_mod._resync_release_manifest(tmp_path, "T-9999", "0.2.0")
        assert result.is_err
        assert result.danger_err == LandError.ReleaseBumpFailed


# frob:ticket T-1349
class TestLandSquashHelpersMutationCoverage:
    """T-1349: same rationale as `TestLandReleaseMonotonicityHelpers` above,
    for the squash-apply/close family T-1334 moved into `_land_squash.py`.
    Each test targets one specific surviving mutant the T-1349 mutation
    run found, not a re-assertion of "the tests cover it structurally"."""

    def test_worktree_full_changeset_diff_ok_but_nonzero_returncode_is_failed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestLandSquashHelpersMutationCoverage.test_worktree_full_changeset_diff_ok_but_nonzero_returncode_is_failed  # noqa: E501
        """Kills the `or` -> `and` mutant on `_worktree_full_changeset`'s
        diff guard: `git diff` succeeding at the process level (is_err=
        False) with a nonzero returncode must still refuse as
        `GitFailed`, not fall through to parsing `stdout`."""
        root = tmp_path / "repo"
        _git_init(root)
        (root / "f.txt").write_text("x")
        _commit_all(root, "init")
        wt = tmp_path / "wt"
        _run(["git", "worktree", "add", "-b", "feat-changeset", str(wt)], root)
        (wt / "g.txt").write_text("y")
        _commit_all(wt, "add g")

        real_run_argv = _land_squash_mod.run_argv

        def _fake_run_argv(argv: Sequence[str], **kwargs: Any) -> Any:
            if "diff" in argv and "--name-only" in argv:
                return Ok(
                    ProcResult(
                        argv=tuple(argv),
                        returncode=129,
                        stdout="",
                        stderr="fatal: ambiguous argument",
                    )
                )
            return real_run_argv(argv, **kwargs)

        monkeypatch.setattr(_land_squash_mod, "run_argv", _fake_run_argv)
        result = _land_squash_mod._worktree_full_changeset(wt, "main")
        assert result.is_err
        assert result.danger_err == LandError.GitFailed

    def test_land_commit_details_diff_tree_fails_returns_empty_files(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestLandSquashHelpersMutationCoverage.test_land_commit_details_diff_tree_fails_returns_empty_files  # noqa: E501
        """Kills the `and` -> `or` mutant on `_land_commit_details`'s
        `files` derivation: when `diff-tree` itself fails (`Err`), the
        `and` guard must short-circuit to `()` without ever touching
        `stat.danger_ok` -- an `or` mutant instead evaluates
        `stat.danger_ok.returncode` unconditionally on the `Err` branch
        and crashes."""

        def _fake_run_argv(argv: Sequence[str], **kwargs: Any) -> Any:
            if "rev-parse" in argv:
                return Ok(
                    ProcResult(
                        argv=tuple(argv), returncode=0, stdout="deadbeef\n", stderr=""
                    )
                )
            return Err(GitError.GitFailed)

        monkeypatch.setattr(_land_squash_mod, "run_argv", _fake_run_argv)
        sha_str, files = _land_squash_mod._land_commit_details(tmp_path)
        assert sha_str == "deadbeef"
        assert files == ()

    def test_absorption_scoped_content_matches_worktree_head_err_is_false(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestLandSquashHelpersMutationCoverage.test_absorption_scoped_content_matches_worktree_head_err_is_false  # noqa: E501
        """Kills the `False` -> `True` negation mutant guarding
        `_absorption_scoped_content_matches`'s `worktree_head` error path:
        an unresolvable worktree HEAD must read as "not verified", never
        a confirmed match."""
        ticket = _ticket_from_spec("T-0001", _spec("t", scope=("x",)), ())
        monkeypatch.setattr(
            _land_squash_mod, "_rev_parse", lambda root, ref: Err(GitError.GitFailed)
        )
        result = _land_squash_mod._absorption_scoped_content_matches(
            tmp_path, tmp_path, ticket
        )
        assert result is False

    def test_absorption_scoped_content_matches_diff_ok_but_nonzero_is_false(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestLandSquashHelpersMutationCoverage.test_absorption_scoped_content_matches_diff_ok_but_nonzero_is_false  # noqa: E501
        """Kills both the `or` -> `and` mutant on the diff guard AND the
        `False` -> `True` negation on its return: `git diff` succeeding at
        the process level with a nonzero returncode must still read as
        unverified (`False`)."""
        ticket = _ticket_from_spec("T-0001", _spec("t", scope=("x",)), ())
        monkeypatch.setattr(
            _land_squash_mod, "_rev_parse", lambda root, ref: Ok("deadbeef")
        )
        monkeypatch.setattr(
            _land_squash_mod,
            "run_argv",
            lambda argv, **kwargs: Ok(
                ProcResult(
                    argv=tuple(argv), returncode=1, stdout="", stderr="diff failed"
                )
            ),
        )
        result = _land_squash_mod._absorption_scoped_content_matches(
            tmp_path, tmp_path, ticket
        )
        assert result is False

    def test_absorption_verified_false_when_ticket_not_done(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestLandSquashHelpersMutationCoverage.test_absorption_verified_false_when_ticket_not_done  # noqa: E501
        """Kills the `and` -> `or` mutant on `_absorption_verified`'s
        guard: a ticket loaded successfully but NOT yet `done` must
        short-circuit to `False` WITHOUT ever consulting
        `_absorption_scoped_content_matches` -- an `or` mutant instead
        treats `is_err=False` alone as sufficient to skip the early
        return, letting a not-done ticket fall through to whatever
        `_absorption_scoped_content_matches` says."""
        ticket = _ticket_from_spec("T-0001", _spec("t", scope=("x",)), ())
        not_done = ticket.model_copy(update={"state": TicketState.QUEUED})
        monkeypatch.setattr("frob.tickets._load_one", lambda root, tid: Ok(not_done))
        # If the early-return guard is mutated away, this stub's `True`
        # would leak through as the final result -- the real code must
        # never reach it.
        monkeypatch.setattr(
            _land_squash_mod, "_absorption_scoped_content_matches", lambda *a: True
        )
        result = _land_squash_mod._absorption_verified(
            tmp_path, tmp_path, ticket, "T-0001"
        )
        assert result is False

    def test_absorption_verified_false_when_load_fails(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestLandSquashHelpersMutationCoverage.test_absorption_verified_false_when_load_fails  # noqa: E501
        """Complement of the above: a failed ledger load also returns
        `False`, killing the `False` -> `True` negation mutant on the
        shared early-return statement."""
        ticket = _ticket_from_spec("T-0001", _spec("t", scope=("x",)), ())
        monkeypatch.setattr("frob.tickets._load_one", lambda root, tid: Err("boom"))
        result = _land_squash_mod._absorption_verified(
            tmp_path, tmp_path, ticket, "T-0001"
        )
        assert result is False

    def test_report_stacked_sibling_absorption_reports_real_land_not_dry_run(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestLandSquashHelpersMutationCoverage.test_report_stacked_sibling_absorption_reports_real_land_not_dry_run  # noqa: E501
        """Kills the literal `False` -> `True` negation mutants on
        `_report_stacked_sibling_absorption`'s `dry_run=False` and
        `natives_rebuilt=False` fields: an absorbed-land report always
        describes a REAL (non-dry-run) land that rebuilt nothing new,
        regardless of the caller's own dry-run status."""
        monkeypatch.setattr(
            _land_squash_mod, "_rev_parse", lambda root, ref: Ok("cafef00d")
        )
        report = _land_squash_mod._report_stacked_sibling_absorption(
            tmp_path, "T-0001", "T-0001", True, True
        )
        assert report.dry_run is False
        assert report.natives_rebuilt is False
        assert report.ledger_spliced is False
        assert report.commit_sha == "cafef00d"

    def test_absorbed_land_report_none_when_staged_files_nonempty(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestLandSquashHelpersMutationCoverage.test_absorbed_land_report_none_when_staged_files_nonempty  # noqa: E501
        """Kills the `or` -> `and` mutant on `_absorbed_land_report`'s
        first guard: a NON-EMPTY staged set (a genuine partial squash,
        not an absorbed no-op) must short-circuit to `None` even though
        `_staged_files` itself succeeded (`is_err=False`) -- an `and`
        mutant instead requires BOTH `is_err` and a truthy staged set,
        so a successful-but-nonempty read wrongly falls through toward
        `_absorption_verified`."""
        ticket = _ticket_from_spec("T-0001", _spec("t", scope=("x",)), ())
        monkeypatch.setattr(
            _land_squash_mod,
            "_staged_files",
            lambda root: Ok(frozenset({"some/file.py"})),
        )
        # If the guard is mutated away, this stub's `True` would let
        # execution reach `_report_stacked_sibling_absorption` instead of
        # returning `None` -- assert it never does.
        monkeypatch.setattr(_land_squash_mod, "_absorption_verified", lambda *a: True)
        result = _land_squash_mod._absorbed_land_report(
            tmp_path, tmp_path, ticket, "T-0001", "T-0001", True, True
        )
        assert result is None

    def test_staged_files_diff_ok_but_nonzero_returncode_is_failed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestLandSquashHelpersMutationCoverage.test_staged_files_diff_ok_but_nonzero_returncode_is_failed  # noqa: E501
        """Kills the `or` -> `and` mutant on `_staged_files`'s diff guard:
        `git diff --cached` succeeding at the process level with a
        nonzero returncode must still refuse as `GitFailed`."""
        monkeypatch.setattr(
            _land_squash_mod,
            "run_argv",
            lambda argv, **kwargs: Ok(
                ProcResult(
                    argv=tuple(argv), returncode=1, stdout="", stderr="diff failed"
                )
            ),
        )
        result = _land_squash_mod._staged_files(tmp_path)
        assert result.is_err
        assert result.danger_err == LandError.GitFailed

    def test_land_commit_details_rev_parse_ok_but_nonzero_returncode_is_no_sha(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestLandSquashHelpersMutationCoverage.test_land_commit_details_rev_parse_ok_but_nonzero_returncode_is_no_sha  # noqa: E501
        """Kills the `and` -> `or` mutant on `_land_commit_details`'s `sha`
        derivation: `rev-parse` succeeding at the process level with a
        nonzero returncode must still report `sha_str=None`, not the
        (meaningless in this case) stdout an `or` mutant would accept."""

        def _fake_run_argv(argv: Sequence[str], **kwargs: Any) -> Any:
            if "rev-parse" in argv:
                return Ok(
                    ProcResult(
                        argv=tuple(argv),
                        returncode=128,
                        stdout="stale-sha\n",
                        stderr="fatal",
                    )
                )
            return Ok(ProcResult(argv=tuple(argv), returncode=0, stdout="", stderr=""))

        monkeypatch.setattr(_land_squash_mod, "run_argv", _fake_run_argv)
        sha_str, files = _land_squash_mod._land_commit_details(tmp_path)
        assert sha_str is None


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


# frob:ticket T-1269
class TestLandPlan:
    """T-1269: `frob ticket land --plan` -- atomic design-phase land with
    automatic draft finalization. Real git subprocesses/worktrees,
    matching this whole file's established style."""

    # frob:ticket T-1269
    # frob:tests tests/test_ticket_land.py::TestLandPlan.test_merges_and_finalizes_every_draft_atomically  # noqa: E501
    def test_merges_and_finalizes_every_draft_atomically(
        self, repo: Path, tmp_path: Path
    ) -> None:
        from frob.tickets._land import land_plan

        worktree = _make_design_worktree(repo, tmp_path)
        (worktree / "docs").mkdir()
        (worktree / "docs" / "new.md").write_text("# New doc\n")
        draft = new_ticket(
            worktree,
            _spec("A design-phase draft ticket"),
        ).danger_ok
        assert draft.id.startswith("T-draft-")
        _commit_all(worktree, "docs: add new.md + file draft")

        result = land_plan(repo, worktree)
        assert result.is_ok, result.err
        report = result.danger_ok
        assert not report.dry_run
        assert report.merge_commit is not None
        assert report.commit_sha is not None
        assert len(report.finalized) == 1
        old_id, new_id = report.finalized[0]
        assert old_id == draft.id
        assert new_id.startswith("T-") and not new_id.startswith("T-draft-")

        # The finalized id (never the draft id) is what actually landed.
        loaded = load_all(repo).danger_ok
        assert new_id in loaded
        assert draft.id not in loaded
        assert (repo / "docs" / "new.md").exists()
        # Landing left root clean -- no half-merged state, no stray lock.
        assert _status_ignoring_frob(repo) == ""

    # frob:ticket T-1269
    # frob:tests tests/test_ticket_land.py::TestLandPlan.test_dry_run_unwinds_the_merge
    def test_dry_run_unwinds_the_merge(self, repo: Path, tmp_path: Path) -> None:
        from frob.tickets._land import land_plan

        worktree = _make_design_worktree(repo, tmp_path)
        (worktree / "docs").mkdir()
        (worktree / "docs" / "new.md").write_text("# New doc\n")
        _commit_all(worktree, "docs: add new.md")

        pre_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        result = land_plan(repo, worktree, dry_run=True)
        assert result.is_ok, result.err
        assert result.danger_ok.dry_run
        # root is back at its pre-merge tip -- nothing landed for real.
        post_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        assert post_sha == pre_sha
        assert not (repo / "docs" / "new.md").exists()

    # frob:ticket T-1269
    # frob:tests \
    # tests/test_ticket_land.py::TestLandPlan.test_merge_conflict_aborts_and_refuses
    def test_merge_conflict_aborts_and_refuses(
        self, repo: Path, tmp_path: Path
    ) -> None:
        from frob.tickets._land import land_plan

        worktree = _make_design_worktree(repo, tmp_path)
        (worktree / "src" / "feature.py").write_text("# worktree edit\n")
        _commit_all(worktree, "conflicting edit")

        # A genuine, real textual conflict on the SAME line in root.
        (repo / "src" / "feature.py").write_text("# root edit\n")
        _commit_all(repo, "root edit")

        pre_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        result = land_plan(repo, worktree)
        assert result.is_err
        assert result.danger_err is LandError.MergeConflict
        # The conflicted merge was aborted -- root is clean and unmoved.
        assert _status_ignoring_frob(repo) == ""
        post_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        assert post_sha == pre_sha

    # frob:ticket T-1269
    # frob:ticket T-1522
    # frob:tests tests/test_ticket_land.py::TestLandPlan.test_tick_gate_dirty_unwinds_finalize_but_keeps_the_durable_merge  # noqa: E501
    def test_tick_gate_dirty_unwinds_finalize_but_keeps_the_durable_merge(
        self, repo: Path, tmp_path: Path
    ) -> None:
        """T-1522: pre-T-1522 this fully unwound back to the pre-merge tip
        on a dirty TICK-gate re-check, discarding the merge commit itself
        -- the exact shape that ate the T-1199/T-1200 queue-drain commits
        in the 2026-08-04 incident when a LATER, unrelated step failed in
        the same invocation. The merge commit is now a durable checkpoint:
        only the finalize-renumbering commit on top of it is undone."""
        from frob.tickets._land import land_plan

        worktree = _make_design_worktree(repo, tmp_path)
        (worktree / "docs").mkdir()
        (worktree / "docs" / "new.md").write_text("# New doc\n")
        draft = new_ticket(worktree, _spec("Another draft")).danger_ok
        _commit_all(worktree, "docs: add new.md + file draft")

        pre_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        result = land_plan(repo, worktree, check_ticks=lambda: False)
        assert result.is_err
        assert result.danger_err is LandError.PlanTickGateDirty
        # The merge commit persists (T-1522): the doc file it carried
        # survives, and root's tip moved past the pre-merge sha even
        # though this call reported an error.
        post_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        assert post_sha != pre_sha
        assert (repo / "docs" / "new.md").exists()
        # Only the finalize step (draft -> real id renumbering) is
        # undone: the draft's id is back as a draft, not finalized to a
        # real id anywhere on root.
        loaded = load_all(repo).danger_ok
        assert draft.id in loaded
        assert loaded[draft.id].id.startswith("T-draft-")

    # frob:ticket T-1269
    # frob:tests tests/test_ticket_land.py::TestLandPlan.test_cli_dispatches_to_land_plan_and_reports  # noqa: E501
    def test_cli_dispatches_to_land_plan_and_reports(
        self, repo: Path, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        from frob.app.config import AppConfig
        from frob.app.ticket_runner._land_cmd import _land

        worktree = _make_design_worktree(repo, tmp_path)
        (worktree / "docs").mkdir()
        (worktree / "docs" / "new.md").write_text("# New doc\n")
        _commit_all(worktree, "docs: add new.md")

        cfg = AppConfig(
            ticket_command="land",
            ticket_land_plan=True,
            ticket_worktree=worktree,
            ticket_path=repo,
        )
        with caplog.at_level("INFO"):
            _land(repo, cfg)
        assert any("landed onto" in rec.message for rec in caplog.records)
        assert (repo / "docs" / "new.md").exists()


# frob:ticket T-1495
class TestLandPlanUnwindNeverDiscardsForeignCommits:
    """T-1495 (the 2026-08-04 incident): `land_plan`'s own unwind path
    (`_land_plan_reset_hard`) used to `reset --hard` unconditionally --
    if ANOTHER process committed to `root` after this run's own last
    commit but before the reset ran (a concurrent queue-drain land, a
    manual `frob ticket drop`), that foreign commit was silently
    destroyed along with this run's own half-finished work. The fix
    (`_assert_reset_only_discards_own_commits`) refuses instead."""

    # frob:ticket T-1495
    # frob:tests tests/test_ticket_land.py::TestLandPlanUnwindNeverDiscardsForeignCommits.test_foreign_commit_after_own_last_commit_refuses_instead_of_discarding  # noqa: E501
    def test_foreign_commit_after_own_last_commit_refuses_instead_of_discarding(
        self, repo: Path, tmp_path: Path
    ) -> None:
        from frob.tickets._land import land_plan

        worktree = _make_design_worktree(repo, tmp_path)
        (worktree / "docs").mkdir()
        (worktree / "docs" / "new.md").write_text("# New doc\n")
        _commit_all(worktree, "docs: add new.md")

        # check_ticks() simulates a FOREIGN process committing to root
        # (another land's queue-drain, a manual `frob ticket drop`)
        # DURING this invocation's own window, then reports dirty --
        # exactly the interleaving shape the 2026-08-04 incident hit.
        def foreign_commit_then_dirty() -> bool:
            (repo / "foreign.txt").write_text("someone else's work\n")
            _commit_all(repo, "chore: an unrelated interleaved commit")
            return False

        pre_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        result = land_plan(repo, worktree, check_ticks=foreign_commit_then_dirty)
        assert result.is_err
        assert result.danger_err is LandError.GitFailed
        # The foreign commit MUST survive -- root's tip must NOT have been
        # reset back past it, unlike the pre-T-1495 behavior.
        post_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        assert post_sha != pre_sha
        assert (repo / "foreign.txt").exists()
        log = _run(["git", "log", "--oneline"], repo).stdout
        assert "an unrelated interleaved commit" in log

    # frob:ticket T-1740
    def test_foreign_commit_refusal_still_unstages_own_leftover_content(
        self, repo: Path, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestLandPlanUnwindNeverDiscardsForeignCommits.test_foreign_commit_refusal_still_unstages_own_leftover_content  # noqa: E501
        """T-1740's second instance of the same defect class: `land
        --plan` runs its OWN unwind primitive (T-1495), separate from
        `_verified_reset_root`, with the identical gap -- refusing on
        foreign-commit detection used to leave whatever this run itself
        had staged sitting in root's index. Never allowed to reach the
        `_land_plan_reset_hard` unwind itself (the tip mismatch refuses
        first), so THIS staged content is whatever `check_ticks()`
        itself leaves in the index while faking the foreign interleave."""
        from frob.tickets._land import land_plan

        worktree = _make_design_worktree(repo, tmp_path)
        (worktree / "docs").mkdir()
        (worktree / "docs" / "new.md").write_text("# New doc\n")
        _commit_all(worktree, "docs: add new.md")

        def foreign_commit_and_leave_staged() -> bool:
            (repo / "foreign.txt").write_text("someone else's work\n")
            _commit_all(repo, "chore: an unrelated interleaved commit")
            (repo / "leftover_staged.txt").write_text("left behind by this run\n")
            _run(["git", "add", "leftover_staged.txt"], repo)
            return False

        result = land_plan(repo, worktree, check_ticks=foreign_commit_and_leave_staged)
        assert result.is_err
        assert result.danger_err is LandError.GitFailed
        staged = _run(["git", "diff", "--cached", "--name-only"], repo).stdout.strip()
        assert staged == "", (
            "land --plan's own T-1495 unwind path left staged content "
            "behind -- the T-1740 incident, reproduced in the --plan path"
        )

    # frob:ticket T-1495
    # frob:ticket T-1522
    # frob:tests tests/test_ticket_land.py::TestLandPlanUnwindNeverDiscardsForeignCommits.test_no_foreign_commit_unwinds_to_the_merge_commit_not_pre_merge  # noqa: E501
    def test_no_foreign_commit_unwinds_to_the_merge_commit_not_pre_merge(
        self, repo: Path, tmp_path: Path
    ) -> None:
        """The ordinary, non-interleaved case: no foreign commit landed,
        so the unwind still runs -- but (T-1522) it now stops at the
        merge commit rather than the pre-merge tip, since the merge
        commit is a durable checkpoint, not something a later, unrelated
        failure in the same invocation should discard."""
        from frob.tickets._land import land_plan

        worktree = _make_design_worktree(repo, tmp_path)
        (worktree / "docs").mkdir()
        (worktree / "docs" / "new.md").write_text("# New doc\n")
        _commit_all(worktree, "docs: add new.md")

        pre_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        result = land_plan(repo, worktree, check_ticks=lambda: False)
        assert result.is_err
        assert result.danger_err is LandError.PlanTickGateDirty
        post_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        assert post_sha != pre_sha
        assert (repo / "docs" / "new.md").exists()


# frob:ticket T-1522
class TestLandPlanQueueDrainCommitsDurable:
    """T-1522: the exact 2026-08-04 T-1199/T-1200 incident shape --
    `land_plan`'s merge step already durably carries a shared worktree
    branch's OTHER, queue-drained content onto `root` (a doc file, other
    already-merged tickets) before the finalize step runs at all. A
    finalize failure AFTER that merge succeeded must not discard it."""

    # frob:ticket T-1522
    # frob:tests tests/test_ticket_land.py::TestLandPlanQueueDrainCommitsDurable.test_finalize_failure_after_merge_keeps_the_merge_commit  # noqa: E501
    def test_finalize_failure_after_merge_keeps_the_merge_commit(
        self, repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from frob.tickets import _land as land_module
        from frob.tickets._land import land_plan
        from frob.tickets._models import LandError as _LandError

        worktree = _make_design_worktree(repo, tmp_path)
        (worktree / "docs").mkdir()
        (worktree / "docs" / "new.md").write_text("# New doc\n")
        _commit_all(worktree, "docs: add new.md -- the 'queue-drained' content")

        # Simulate a finalize failure (a `NotFound` from `finalize_draft`,
        # or any other post-merge finalize error) AFTER the merge commit
        # already exists on root -- exactly the 2026-08-04 shape where
        # something unrelated to the already-merged content fails.
        def _always_fails(_root: Path) -> Result[tuple, _LandError]:
            return Err(_LandError.NotFound)

        monkeypatch.setattr(land_module, "_land_plan_finalize_drafts", _always_fails)

        pre_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        result = land_plan(repo, worktree)
        assert result.is_err
        assert result.danger_err is LandError.NotFound

        # T-1522: the merge commit persists -- root's tip moved past the
        # pre-merge sha (it now IS the merge commit) and the doc file it
        # carried is on disk, even though this invocation reported an
        # error for the (unrelated) finalize failure.
        post_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        assert post_sha != pre_sha
        assert (repo / "docs" / "new.md").exists()

        # A retry of land_plan against the now-advanced root is a clean
        # no-op merge (nothing new to bring in) -- proving the content is
        # genuinely durable, not merely "not yet reset" mid-call.
        monkeypatch.undo()
        retry = land_plan(repo, worktree)
        assert retry.is_ok, retry.err


# frob:ticket T-1515
# frob:ticket T-1634
class TestLandLockHolderMetadataAndTimeout:
    """T-1515: `_land_lock` now writes pid/session/start-time into
    land.lock's own content on acquisition, and refuses (raising
    `LandLockTimeout`) rather than blocking forever when a foreign holder
    does not release within its timeout -- the fix for the 2026-08-04
    incident (an orphaned background land driver queued silently against a
    new coordinator session's own `land()` call)."""

    # frob:tests \
    # tests/test_ticket_land.py::TestLandLockHolderMetadataAndTimeout.test_holder_metad\
    # ata_written_on_acquire
    # frob:ticket T-1515
    def test_holder_metadata_written_on_acquire(self, tmp_path: Path) -> None:
        import json
        import os

        from frob.tickets._land import _LAND_LOCK_REL, _land_lock

        with _land_lock(tmp_path):
            content = (tmp_path / _LAND_LOCK_REL).read_text()
        parsed = json.loads(content)
        assert parsed["pid"] == os.getpid()
        assert "session_id" in parsed
        assert "started_at" in parsed

    # frob:tests \
    # tests/test_ticket_land.py::TestLandLockHolderMetadataAndTimeout.test_lock_release\
    # d_after_context_exits
    # frob:ticket T-1515
    def test_lock_released_after_context_exits(self, tmp_path: Path) -> None:
        import fcntl

        from frob.tickets._land import _LAND_LOCK_REL, _land_lock

        with _land_lock(tmp_path):
            pass

        # A fresh acquisition from a DIFFERENT fd must succeed non-
        # blocking now that the context above has released it.
        path = tmp_path / _LAND_LOCK_REL
        fd = os.open(str(path), os.O_CREAT | os.O_RDWR, 0o644)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)

    # frob:tests \
    # tests/test_ticket_land.py::TestLandLockHolderMetadataAndTimeout.test_timeout_rais\
    # es_when_a_foreign_holder_never_releases
    # frob:ticket T-1515
    def test_timeout_raises_when_a_foreign_holder_never_releases(
        self, tmp_path: Path
    ) -> None:
        import fcntl
        import json

        from frob.tickets._land import (
            _LAND_LOCK_REL,
            LandLockTimeout,
            _land_lock,
        )

        path = tmp_path / _LAND_LOCK_REL
        path.parent.mkdir(parents=True, exist_ok=True)
        holder_fd = os.open(str(path), os.O_CREAT | os.O_RDWR, 0o644)
        fcntl.flock(holder_fd, fcntl.LOCK_EX)
        os.write(
            holder_fd,
            (
                json.dumps(
                    {
                        "pid": 999999,
                        "session_id": "foreign-orphan",
                        "started_at": "2026-08-04T00:00:00+00:00",
                    }
                )
                + "\n"
            ).encode("utf-8"),
        )
        try:
            with pytest.raises(LandLockTimeout) as excinfo:
                with _land_lock(tmp_path, timeout=0.2):
                    pass  # pragma: no cover -- must never be reached
            assert excinfo.value.holder is not None
            assert excinfo.value.holder["session_id"] == "foreign-orphan"
        finally:
            fcntl.flock(holder_fd, fcntl.LOCK_UN)
            os.close(holder_fd)

    # frob:tests \
    # tests/test_ticket_land.py::TestLandLockHolderMetadataAndTimeout.test_orphaned_loc\
    # k_from_a_confirmed_dead_pid_is_reclaimed_and_logged
    # frob:ticket T-1634
    def test_orphaned_lock_from_a_confirmed_dead_pid_is_reclaimed_and_logged(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """T-1634: a land.lock file naming a pid that does not correspond
        to any running process, with NO real `flock` actually held (the
        orphaned-file-only shape a killed/SIGKILLed land leaves behind --
        the OS already released the real OS-level lock the instant that
        process exited), is proceeded through IMMEDIATELY by a fresh
        `_land_lock` acquisition -- never waits, never raises
        `LandLockTimeout` -- and logs a WARNING disclosing the dead
        holder's identity, closing the 'a human has to notice and delete
        this by hand' gap T-1634 was filed against."""
        import json
        import logging

        from frob.tickets._land import _LAND_LOCK_REL, _land_lock

        dead_pid = min(os.getpid() * 7 + 999983, 2**22)
        path = tmp_path / _LAND_LOCK_REL
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "pid": dead_pid,
                    "session_id": "orphaned-session",
                    "started_at": "2026-08-04T00:00:00+00:00",
                }
            )
            + "\n"
        )

        with caplog.at_level(logging.WARNING, logger="frob.tickets._land"):
            with _land_lock(tmp_path, timeout=5.0):
                pass

        reclaim_lines = [
            r.message
            for r in caplog.records
            if "reclaiming orphaned land.lock" in r.message
        ]
        assert reclaim_lines, caplog.text
        assert str(dead_pid) in reclaim_lines[0]
        assert "orphaned-session" in reclaim_lines[0]

    # frob:tests \
    # tests/test_ticket_land.py::TestLandLockHolderMetadataAndTimeout.test_orphaned_loc\
    # k_naming_a_genuinely_live_pid_still_refuses
    # frob:ticket T-1634
    def test_orphaned_lock_naming_a_genuinely_live_pid_still_refuses(
        self, tmp_path: Path
    ) -> None:
        """T-1634's reclaim must never override a genuinely-held OS lock:
        a land.lock naming THIS test process's own (genuinely live) pid,
        with the flock ACTUALLY held via a separate fd, still times out
        exactly as before -- liveness alone is never a substitute for the
        real `flock`."""
        import fcntl
        import json

        from frob.tickets._land import (
            _LAND_LOCK_REL,
            LandLockTimeout,
            _land_lock,
        )

        path = tmp_path / _LAND_LOCK_REL
        path.parent.mkdir(parents=True, exist_ok=True)
        holder_fd = os.open(str(path), os.O_CREAT | os.O_RDWR, 0o644)
        fcntl.flock(holder_fd, fcntl.LOCK_EX)
        os.write(
            holder_fd,
            (
                json.dumps(
                    {
                        "pid": os.getpid(),
                        "session_id": "genuinely-live",
                        "started_at": "2026-08-04T00:00:00+00:00",
                    }
                )
                + "\n"
            ).encode("utf-8"),
        )
        try:
            with pytest.raises(LandLockTimeout) as excinfo:
                with _land_lock(tmp_path, timeout=0.2):
                    pass  # pragma: no cover -- must never be reached
            assert excinfo.value.holder is not None
            assert excinfo.value.holder["session_id"] == "genuinely-live"
        finally:
            fcntl.flock(holder_fd, fcntl.LOCK_UN)
            os.close(holder_fd)


class TestUnscopedErrorFindingsExcludesNoTicketNoise:
    """T-1804: `_unscoped_error_findings` -- the shared spawn both
    the deferred post-land sweep and `--land-parity` use -- must exclude
    PRE001/SCOPE001 from its returned finding-identity set. Both rules
    fire unconditionally under `_no_active_ticket_violation` (B9,
    `frob.gates.__init__`) whenever this deliberately-no-`--ticket` spawn
    sees ANY non-empty diff with no derivable ticket -- a hygiene signal
    about root's git state at measurement time (commonly a concurrent
    land's transient dirt on the shared checkout), never a code
    regression either caller exists to catch. Measured 2026-08-07: five
    sweep-filed regression tickets in one hour whose only findings were
    these two."""

    @staticmethod
    def _json_payload(findings: list[tuple[str, str]]) -> str:
        """A minimal `frob check --json` payload shape
        (`_parse_check_json`/`_parse_error_findings_from_json`'s own
        contract: a `"results"` list of `{"tool", "diagnostics"}` dicts,
        each diagnostic an error-severity `{"code", "file", "severity"}`)
        with one ToolResult carrying exactly `findings`."""
        return json.dumps(
            {
                "results": [
                    {
                        "tool": "gate-summary",
                        "diagnostics": [
                            {"code": rule, "file": file, "severity": "error"}
                            for rule, file in findings
                        ],
                    }
                ]
            }
        )

    def test_pre001_and_scope001_are_excluded_but_real_findings_survive(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests \
        # tests/test_ticket_land.py::TestUnscopedErrorFindingsExcludesNoTicketNoise.tes\
        # t_pre001_and_scope001_are_excluded_but_real_findings_survive
        from frob.app import ticket_runner

        payload = self._json_payload(
            [
                ("PRE001", "tickets/T-0001"),
                ("SCOPE001", "some/file.py"),
                ("DEAD001", "src/frob/real_module.py"),
            ]
        )

        def _fake(argv: list[str], **k: Any) -> Result[ProcResult, Any]:
            return Ok(
                ProcResult(argv=tuple(argv), returncode=1, stdout=payload, stderr="")
            )

        monkeypatch.setattr(ticket_runner, "guarded_subprocess_run", _fake)
        from frob.app.ticket_runner._land_cmd import _unscoped_error_findings

        result = _unscoped_error_findings(tmp_path, "T-0001")

        assert result == frozenset({("DEAD001", "src/frob/real_module.py")})

    def test_only_no_ticket_noise_present_returns_empty_not_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests \
        # tests/test_ticket_land.py::TestUnscopedErrorFindingsExcludesNoTicketNoise.tes\
        # t_only_no_ticket_noise_present_returns_empty_not_none
        """A run whose ONLY findings are PRE001/SCOPE001 -- exactly the
        five-tickets-in-an-hour incident -- must read as a real, measured
        EMPTY set (clean), never `None` (unmeasurable): the whole point is
        that the sweep stops comparing this noise against its baseline at
        all, not that it falls back to skipping the comparison."""
        from frob.app import ticket_runner

        payload = self._json_payload(
            [("PRE001", "tickets/T-0001"), ("SCOPE001", "some/file.py")]
        )

        def _fake(argv: list[str], **k: Any) -> Result[ProcResult, Any]:
            return Ok(
                ProcResult(argv=tuple(argv), returncode=1, stdout=payload, stderr="")
            )

        monkeypatch.setattr(ticket_runner, "guarded_subprocess_run", _fake)
        from frob.app.ticket_runner._land_cmd import _unscoped_error_findings

        result = _unscoped_error_findings(tmp_path, "T-0001")

        assert result == frozenset()
