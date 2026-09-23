"""T-4491: lease-staleness's ledger read must not scale with the
number of live lease records.

Measured incident (2026-09-15, three SIGUSR1 stack dumps on a live land):
`_ticket_ledger_staleness_shape` called `load_queue(root)` -- the FULL
active+archive merge, which YAML-parses every archived ticket file (v2
mode: one `_parse_ticket_file` per `tickets/archive/T-####/ticket.md`) --
once PER lease record inside `_live_leases_pruning_stale`, called by
`read_all_leases`. With N archived-ticket leases that is N full-ledger
re-parses per call; on the real repo (3391 archived tickets at measurement
time) a single such parse cost ~25.5s.

Three things this file checks, matching the ticket's three acceptance
criteria:

1. `_live_leases_pruning_stale` loads the ticket ledger AT MOST ONCE per
   call, never once per record (`TestLiveLeasesPruningStaleSingleLoad`).
2. An archived ticket id answers "ticket-terminal" via a plain filesystem
   existence check under `tickets/archive/<id>/`, never by YAML-parsing
   the archive (`TestTicketLedgerStalenessShapeArchiveFastPath`).
3. `read_all_leases` stays fast (bounded well under the 5s BUG002
   threshold) even with many archived-ticket leases outstanding
   (`TestReadAllLeasesStaysFast`) -- a smaller-scale, CI-portable stand-in
   for the real ~4200-ticket/~20-worktree repo timing recorded by hand in
   this ticket's Done report.

Real git fixture repos throughout (same style as `tests/test_ticket_
leases.py`) -- no mocking of the ledger/archive layer itself except where
a test's whole point IS to assert something was NOT called."""

from __future__ import annotations

import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest

from frob.app.config import AppConfig
from frob.app.ticket_runner import run as ticket_run
from frob.tickets._leases import (
    _LeaseRecord,
    _live_leases_pruning_stale,
    _ticket_ledger_staleness_shape,
    leases_dir,
    read_all_leases,
)

pytestmark = pytest.mark.heavy_subprocess


def _run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess:
    """Thin `subprocess.run` wrapper matching `test_ticket_leases.py`'s
    own helper -- raises on a non-zero exit so a fixture-setup failure
    surfaces immediately rather than as a confusing downstream assert."""
    return subprocess.run(
        argv, cwd=str(cwd), check=True, capture_output=True, text=True
    )


# frob:waive DUP001 reason="test-fixture-shaped git-init helper duplicated by \
# design across 25+ test files repo-wide (test files are not a shared library, \
# T-4243's own precedent) -- extracting a shared helper module for this one \
# three-line body would be a bigger, unrelated refactor than this ticket's \
# narrow perf-fix scope covers"  # noqa: E501
def _git_init(root: Path) -> None:
    """A minimal, hermetic git repo -- same shape as `test_ticket_leases.
    py`'s `_git_init`, kept local to avoid importing a sibling test
    module (test files are not a shared library)."""
    root.mkdir(parents=True, exist_ok=True)
    _run(["git", "init", "-q", "-b", "main"], root)
    _run(["git", "config", "user.email", "test@example.com"], root)
    _run(["git", "config", "user.name", "Test"], root)


# frob:waive DUP001 reason="same test-fixture-shaped duplication as _git_init above -- \
# matches tests/test_ticket_leases.py::_commit_all exactly, kept local per this file's \
# own test-files-are-not-a-shared-library convention"
def _commit_all(root: Path, message: str) -> None:
    """Stage and commit everything dirty in `root`; a no-op stage is not
    an error (matches `test_ticket_leases.py`'s own `_commit_all`)."""
    _run(["git", "add", "-A"], root)
    diff = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=root, check=False)
    if diff.returncode == 0:
        return
    _run(["git", "commit", "-q", "-m", message], root)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A main checkout with a real git history and an initialized (v2
    default) ledger -- same fixture shape as `test_ticket_leases.py`'s
    `repo`."""
    main_repo = tmp_path / "main"
    _git_init(main_repo)
    (main_repo / ".gitignore").write_text(".frob/\n")
    (main_repo / "src").mkdir()
    (main_repo / "src" / "feature.py").write_text("# feature\n")
    _commit_all(main_repo, "init: empty ledger committed")
    return main_repo


# frob:waive DUP001 reason="same test-fixture-shaped duplication as _git_init \
# above -- a second linked worktree fixture is identical in shape across every \
# test module that needs one, matching tests/test_ticket_leases.py's own \
# second_worktree; kept local per this file's own test-files-are-not-a-shared- \
# library convention"  # noqa: E501
@pytest.fixture
def second_worktree(repo: Path) -> Path:
    """A second linked `git worktree` of `repo` -- the lease "holder"
    every fixture-written lease below points at, so `_probe_worktree_
    liveness` reads it as `"present"` (matching `test_ticket_leases.py`'s
    own `second_worktree`)."""
    wt = repo.parent / "wt"
    _run(["git", "worktree", "add", "-b", "feature-wt", str(wt)], repo)
    return wt


# frob:waive WIRE001 reason="test-only fixture helper, called by three test methods in \
# this same file (TestTicketLedgerStalenessShapeArchiveFastPath, \
# TestLiveLeasesPruningStaleSingleLoad, TestReadAllLeasesStaysFast) -- no production \
# caller is expected, matching the shape every other test-file- local fixture builder \
# in this suite (e.g. tests/test_ticket_leases.py's own _write_lease) already has" \
# permanent="true"
def _new_archived_ticket(repo: Path, index: int) -> str:
    """Create, start, close and archive one throwaway ticket end to end
    via the real CLI dispatch path (matching `test_ticket_leases.py`'s
    `test_archive_cli_leaves_repo_clean`), returning its id. Building
    real archived tickets this way -- not hand-rolled YAML -- is what
    makes the fast-path assertions below trustworthy: the ticket really
    is terminal and really does live under `tickets/archive/<id>/`,
    exactly like the real repo's 3391 archived tickets this ticket's
    measured incident found."""
    scope_file = f"src/feature_{index}.py"
    (repo / scope_file).write_text(f"# feature {index}\n")
    ticket_run(
        AppConfig(
            ticket_command="new",
            ticket_path=repo,
            ticket_title=f"throwaway {index}",
            ticket_kind="docs",
            ticket_scope=[scope_file],
            ticket_body="## Done report\n\nDone.\n",
            ticket_ack_related=True,
        )
    )
    from frob.tickets import load_all

    queue = load_all(repo)
    assert queue.is_ok
    ticket_id = max(queue.danger_ok, key=lambda tid: int(tid.split("-")[1]))
    ticket_run(AppConfig(ticket_command="start", ticket_path=repo, ticket_id=ticket_id))
    ticket_run(
        AppConfig(
            ticket_command="close",
            ticket_path=repo,
            ticket_id=ticket_id,
            ticket_evidence_cmd="echo verified",
        )
    )
    _commit_all(repo, f"pre-archive: {ticket_id} closed")
    ticket_run(AppConfig(ticket_command="archive", ticket_path=repo))
    return ticket_id


# frob:waive WIRE001 reason="test-only fixture helper, called by two test methods in \
# this same file -- same shape as tests/test_ticket_leases.py's own _write_lease, no \
# production caller expected" permanent="true"
def _write_lease_for(root: Path, ticket_id: str, worktree: Path) -> _LeaseRecord:
    """Write a real lease file for `ticket_id` pinned to `worktree`
    directly (matching `test_ticket_leases.py`'s own `_write_lease`
    helper) -- `record_lease`'s production path resolves the WORKTREE
    it is called from as the lease holder and best-effort-skips writing
    from the shared primary checkout, neither of which fits a fixture
    that wants to pin an ARBITRARY ticket to an ARBITRARY already-
    existing worktree directory."""
    leases_root = leases_dir(root).danger_ok
    leases_root.mkdir(parents=True, exist_ok=True)
    record = _LeaseRecord(
        ticket_id=ticket_id,
        scope=("src/feature.py",),
        worktree=str(worktree),
        branch="feature-wt",
        recorded_at=datetime.now(UTC).isoformat(),
    )
    (leases_root / f"{ticket_id}.json").write_text(
        record.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )
    return record


class TestTicketLedgerStalenessShapeArchiveFastPath:
    """Acceptance 2: an archived ticket id answers "ticket-terminal"
    without YAML-parsing the archive."""

    # frob:tests tests/unit/test_leases_staleness_perf.py::TestTicketLedgerStalenessShapeArchiveFastPath.test_archived_ticket_id_is_terminal_without_parsing_the_archive kind="unit"  # noqa: E501
    # frob:tests src/frob/tickets/_leases.py::_ticket_ledger_staleness_shape kind="unit"
    def test_archived_ticket_id_is_terminal_without_parsing_the_archive(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """FAILS FIRST at the parent commit: before the fix, this shape
        is answered exclusively by `load_queue`, which calls `load_
        archive`, which (v2 mode) globs and YAML-parses every archived
        ticket -- calling `load_archive` here would trip the monkeypatch
        below. After the fix, an archived id is recognized by a plain
        `tickets/archive/<id>/ticket.md` existence check and `load_
        archive` is never reached for it."""
        ticket_id = _new_archived_ticket(repo, 0)

        from frob.tickets import _archive as archive_mod

        def _forbidden(*_args: object, **_kwargs: object) -> None:
            raise AssertionError(
                "load_archive was called -- the archive was YAML-parsed "
                "instead of answered by a filesystem existence check"
            )

        monkeypatch.setattr(archive_mod, "load_archive", _forbidden)

        shape = _ticket_ledger_staleness_shape(repo, ticket_id)
        assert shape == "ticket-terminal"

    # frob:tests tests/unit/test_leases_staleness_perf.py::TestTicketLedgerStalenessShapeArchiveFastPath.test_unknown_ticket_id_is_still_ticket_gone kind="unit"  # noqa: E501
    def test_unknown_ticket_id_is_still_ticket_gone(self, repo: Path) -> None:
        """Positive control: a ticket id that is neither active nor
        archived is still `"ticket-gone"` -- the fast-path change must
        not turn every unrecognized id into a false `None`/"live"."""
        shape = _ticket_ledger_staleness_shape(repo, "T-9999")
        assert shape == "ticket-gone"


class TestLiveLeasesPruningStaleSingleLoad:
    """Acceptance 1: the ticket ledger is loaded at most once per `_live_
    leases_pruning_stale` call, never once per record."""

    # frob:tests tests/unit/test_leases_staleness_perf.py::TestLiveLeasesPruningStaleSingleLoad.test_load_queue_called_at_most_once_for_n_records kind="unit"  # noqa: E501
    def test_load_queue_called_at_most_once_for_n_records(
        self,
        repo: Path,
        second_worktree: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """FAILS FIRST at the parent commit: the old `_ticket_ledger_
        staleness_shape` called `load_queue` once per record, so N
        archived-ticket leases meant N calls; this asserts `<= 1` and the
        parent commit's `N` (>1 for `N=3`) trips it. After the fix, a
        v2-mode archived ticket is answered via a filesystem check and
        never reaches `load_queue` at all -- `0` calls, well within
        `<= 1`."""
        n = 3
        ticket_ids = [_new_archived_ticket(repo, i) for i in range(n)]
        leases_root = leases_dir(repo).danger_ok
        records = [
            _write_lease_for(repo, ticket_id, second_worktree)
            for ticket_id in ticket_ids
        ]
        assert len(records) == n

        from frob.tickets import _archive as archive_mod

        call_count = 0
        real_load_queue = archive_mod.load_queue

        def _counting_load_queue(root: Path):
            nonlocal call_count
            call_count += 1
            return real_load_queue(root)

        monkeypatch.setattr(archive_mod, "load_queue", _counting_load_queue)

        live = _live_leases_pruning_stale(repo, leases_root, records)

        assert call_count <= 1, (
            f"load_queue was called {call_count} times for {n} records -- "
            "the ledger is being loaded once per record, not once per call"
        )
        # Every record's ticket is archived/terminal, so all n are pruned
        # (unlinked), matching pre-fix ticket-terminal semantics exactly.
        assert live == ()
        for path in leases_root.glob("*.json"):
            assert False, f"terminal lease {path} was not unlinked"


class TestReadAllLeasesStaysFast:
    """Acceptance 3 (CI-portable stand-in): `read_all_leases` must not
    take seconds merely because many archived-ticket leases are
    outstanding. The real repo's ~4200-ticket/~20-worktree timing is
    recorded by hand in the Done report; this asserts a much smaller
    fixture completes near-instantly, so a regression that reintroduces
    an O(records) full-ledger reload would still show up here long
    before it reached the real repo's scale."""

    # frob:tests tests/unit/test_leases_staleness_perf.py::TestReadAllLeasesStaysFast.test_many_archived_ticket_leases_stay_fast kind="unit"  # noqa: E501
    def test_many_archived_ticket_leases_stay_fast(
        self, repo: Path, second_worktree: Path
    ) -> None:
        n = 8
        ticket_ids = [_new_archived_ticket(repo, i) for i in range(n)]
        for ticket_id in ticket_ids:
            _write_lease_for(repo, ticket_id, second_worktree)

        started = time.monotonic()
        leases = read_all_leases(repo)
        elapsed = time.monotonic() - started

        assert leases == ()
        assert elapsed < 5.0, (
            f"read_all_leases took {elapsed:.2f}s for {n} archived-ticket "
            "leases -- BUG002's 5s threshold"
        )
