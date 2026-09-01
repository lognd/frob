import json
import subprocess
from pathlib import Path

import pytest

from tests.unit.conftest import (
    _completed,  # noqa: F401 -- T-3596
    _write_ticket,  # noqa: F401 -- T-3596
    fleet_status,
)


class TestRootDirt:
    """`fleet_status.root_dirt`."""

    def test_clean_repo(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Empty porcelain output means no dirt lines."""
        monkeypatch.setattr(subprocess, "run", lambda *a, **k: _completed(""))
        assert fleet_status.root_dirt() == []

    def test_dirty_repo(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Non-empty porcelain lines are returned verbatim, blank lines dropped."""
        monkeypatch.setattr(
            subprocess, "run", lambda *a, **k: _completed(" M foo.py\n ?? bar.py\n")
        )
        assert fleet_status.root_dirt() == ["M foo.py", " ?? bar.py"]

    def test_phantom_modified_entry_dropped(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2586: a bare 'M' status whose content-comparing `git diff --stat
        HEAD` comes back empty is a stat-shortcut phantom (CRLF/mtime
        churn with no logical change) and must NOT be reported dirty."""

        def _fake_run(args, **_k):  # noqa: ANN001
            if "status" in args:
                return _completed("M rapid-debt.jsonl\n")
            if "diff" in args:
                return _completed("")  # no real content difference
            return _completed("")

        monkeypatch.setattr(subprocess, "run", _fake_run)
        assert fleet_status.root_dirt() == []

    def test_genuine_modified_entry_kept(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """T-2586: a bare 'M' status whose `git diff --stat HEAD` DOES show
        a real difference must still be reported dirty -- the positive
        control that proves this is content confirmation, not a blanket
        suppression of the 'M' status class."""

        def _fake_run(args, **_k):  # noqa: ANN001
            if "status" in args:
                return _completed("M rapid-debt.jsonl\n")
            if "diff" in args:
                return _completed(" rapid-debt.jsonl | 1 +\n 1 file changed\n")
            return _completed("")

        monkeypatch.setattr(subprocess, "run", _fake_run)
        assert fleet_status.root_dirt() == ["M rapid-debt.jsonl"]

    def test_untracked_entry_never_reverified(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2586: an untracked ('??') path is never a stat-shortcut
        candidate -- it must be reported dirty without ever calling
        `git diff` to confirm it (untracked residue, e.g. from a killed
        retry loop, has no HEAD blob to diff against in the first
        place)."""
        calls: list[list[str]] = []

        def _fake_run(args, **_k):  # noqa: ANN001
            calls.append(args)
            if "status" in args:
                return _completed("?? stray-file.txt\n")
            return _completed("")

        monkeypatch.setattr(subprocess, "run", _fake_run)
        assert fleet_status.root_dirt() == ["?? stray-file.txt"]
        assert not any("diff" in c for c in calls), (
            "an untracked entry must never trigger a content re-verification call"
        )


class TestLeases:
    """`fleet_status.leases`."""

    def test_reads_lease_records(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Every `*.json` lease file under LEASES is parsed as a record."""
        leases_dir = tmp_path / "leases"
        leases_dir.mkdir()
        (leases_dir / "T-0001.json").write_text(
            json.dumps({"ticket_id": "T-0001", "worktree": "/x"}), encoding="utf-8"
        )
        monkeypatch.setattr(fleet_status, "LEASES", leases_dir)
        assert fleet_status.leases() == [{"ticket_id": "T-0001", "worktree": "/x"}]

    def test_no_lease_dir(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A missing leases directory returns an empty list, not an error."""
        monkeypatch.setattr(fleet_status, "LEASES", tmp_path / "does-not-exist")
        assert fleet_status.leases() == []

    def test_unreadable_lease_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Malformed JSON is reported with an '<unreadable>' worktree, not raised."""
        leases_dir = tmp_path / "leases"
        leases_dir.mkdir()
        (leases_dir / "T-0002.json").write_text("{not json", encoding="utf-8")
        monkeypatch.setattr(fleet_status, "LEASES", leases_dir)
        records = fleet_status.leases()
        assert records == [{"ticket_id": "T-0002", "worktree": "<unreadable>"}]


class TestInProgressTicketScopeLeases:
    """`fleet_status.in_progress_ticket_scope_leases` (T-2651)."""

    @staticmethod
    def _write_ticket(
        tickets_dir: Path, ticket_id: str, state: str, scope: list[str]
    ) -> None:
        scope_block = "\n".join(f"- {item}" for item in scope)
        text = (
            "---\n"
            f"id: {ticket_id}\n"
            "title: fixture\n"
            f"state: {state}\n"
            "kind: bug\n"
            "scope:\n"
            f"{scope_block}\n"
            "---\n"
        )
        ticket_dir = tickets_dir / ticket_id
        ticket_dir.mkdir(parents=True)
        (ticket_dir / "ticket.md").write_text(text, encoding="utf-8")

    def test_no_worktree_flagged_as_leak(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An in-progress ticket with declared scope and NO resolvable
        worktree (no lease file, no scope-correlated worktree) appears,
        flagged `leaked=True` -- the missing case T-2651 exists to catch:
        T-2377 sat in-progress for nine hours after its worktree was
        removed and was invisible to the old, file-based reporter."""
        tickets_dir = tmp_path / "tickets"
        self._write_ticket(tickets_dir, "T-0001", "in-progress", ["src/a.py"])
        monkeypatch.setattr(fleet_status, "TICKETS_DIR", tickets_dir)
        monkeypatch.setattr(fleet_status, "LEASES", tmp_path / "no-leases")
        monkeypatch.setattr(fleet_status, "WORKTREES", tmp_path / "no-worktrees")
        entries = fleet_status.in_progress_ticket_scope_leases()
        assert entries == [
            {
                "ticket_id": "T-0001",
                "scope": ["src/a.py"],
                "worktree": None,
                "leaked": True,
            }
        ]

    def test_live_worktree_named_not_leaked(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An in-progress ticket whose lease file still resolves to a
        live worktree directory is named, not leaked -- the unchanged
        case: today's behavior for a healthy lease stays exactly as it
        was."""
        tickets_dir = tmp_path / "tickets"
        self._write_ticket(tickets_dir, "T-0002", "in-progress", ["src/b.py"])
        monkeypatch.setattr(fleet_status, "TICKETS_DIR", tickets_dir)

        worktrees_dir = tmp_path / "worktrees"
        live_wt = worktrees_dir / "t-0002"
        live_wt.mkdir(parents=True)
        monkeypatch.setattr(fleet_status, "WORKTREES", worktrees_dir)

        leases_dir = tmp_path / "leases"
        leases_dir.mkdir()
        (leases_dir / "T-0002.json").write_text(
            json.dumps({"ticket_id": "T-0002", "worktree": str(live_wt)}),
            encoding="utf-8",
        )
        monkeypatch.setattr(fleet_status, "LEASES", leases_dir)

        entries = fleet_status.in_progress_ticket_scope_leases()
        assert entries == [
            {
                "ticket_id": "T-0002",
                "scope": ["src/b.py"],
                "worktree": "t-0002",
                "leaked": False,
            }
        ]

    def test_queued_ticket_excluded(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A QUEUED ticket's declared scope never appears -- a lease binds
        only at in-progress (T-0453); reporting queued scopes as leases
        would make the list useless in the opposite direction."""
        tickets_dir = tmp_path / "tickets"
        self._write_ticket(tickets_dir, "T-0003", "queued", ["src/c.py"])
        monkeypatch.setattr(fleet_status, "TICKETS_DIR", tickets_dir)
        monkeypatch.setattr(fleet_status, "LEASES", tmp_path / "no-leases")
        monkeypatch.setattr(fleet_status, "WORKTREES", tmp_path / "no-worktrees")
        assert fleet_status.in_progress_ticket_scope_leases() == []


# frob:ticket T-2654
class TestBlockedInProgressLeases:
    """`fleet_status.blocked_in_progress_leases` (T-2654): an in-progress
    ticket that is also `blocked_by` an open blocker cannot proceed, so
    any lease it holds is pure waste -- the T-2377 shape, detectable
    without waiting for its worktree to vanish."""

    # frob:ticket T-2654
    def test_in_progress_with_open_blocker_flagged(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The positive control: in-progress + blocked_by a still-open
        (queued) blocker is flagged, naming the open blocker id."""
        tickets_dir = tmp_path / "tickets"
        _write_ticket(tickets_dir, "T-2568", state="queued")
        _write_ticket(
            tickets_dir, "T-2377", state="in-progress", blocked_by=("T-2568",)
        )
        monkeypatch.setattr(fleet_status, "TICKETS_DIR", tickets_dir)
        entries = fleet_status.blocked_in_progress_leases()
        assert entries == [{"ticket_id": "T-2377", "open_blockers": ["T-2568"]}]

    # frob:ticket T-2654
    def test_in_progress_with_no_blockers_not_flagged(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Negative control: an in-progress ticket with NO `blocked_by`
        at all is not flagged -- without this, every in-progress ticket
        would read as flagged."""
        tickets_dir = tmp_path / "tickets"
        _write_ticket(tickets_dir, "T-0010", state="in-progress")
        monkeypatch.setattr(fleet_status, "TICKETS_DIR", tickets_dir)
        assert fleet_status.blocked_in_progress_leases() == []

    # frob:ticket T-2654
    def test_in_progress_with_only_terminal_blockers_not_flagged(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Negative control: an in-progress ticket whose only blocker is
        `done` is not flagged -- a resolved blocker must not read as
        still holding the lease hostage."""
        tickets_dir = tmp_path / "tickets"
        _write_ticket(tickets_dir, "T-0011", state="done")
        _write_ticket(
            tickets_dir, "T-0012", state="in-progress", blocked_by=("T-0011",)
        )
        monkeypatch.setattr(fleet_status, "TICKETS_DIR", tickets_dir)
        assert fleet_status.blocked_in_progress_leases() == []

    # frob:ticket T-2654
    def test_queued_ticket_with_open_blocker_not_flagged(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Negative control: a QUEUED ticket blocked by an open blocker
        is never flagged -- a lease binds only at in-progress (T-0453),
        so a queued-and-blocked ticket holds no lease to waste."""
        tickets_dir = tmp_path / "tickets"
        _write_ticket(tickets_dir, "T-0013", state="queued")
        _write_ticket(tickets_dir, "T-0014", state="queued", blocked_by=("T-0013",))
        monkeypatch.setattr(fleet_status, "TICKETS_DIR", tickets_dir)
        assert fleet_status.blocked_in_progress_leases() == []


class TestWorktrees:
    """`fleet_status.worktrees`."""

    def test_reports_idle_age(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A worktree whose last commit is older than idle_seconds is flagged idle."""
        worktrees_dir = tmp_path / "worktrees"
        (worktrees_dir / "one").mkdir(parents=True)
        monkeypatch.setattr(fleet_status, "WORKTREES", worktrees_dir)
        monkeypatch.setattr(fleet_status.time, "time", lambda: 1_000_000.0)
        monkeypatch.setattr(
            fleet_status, "_git", lambda args, cwd: str(int(1_000_000.0) - 9999)
        )
        rows = fleet_status.worktrees(idle_seconds=100)
        assert rows == [("one", 9999, True)]

    def test_no_worktree_dir(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A missing worktrees directory returns an empty list, not an error."""
        monkeypatch.setattr(fleet_status, "WORKTREES", tmp_path / "does-not-exist")
        assert fleet_status.worktrees(idle_seconds=100) == []


# frob:ticket T-2599
# frob:ticket T-2755
class TestWorktreeContentClassification:
    """`fleet_status.worktree_content_classification` (T-2599): the
    content-presence test that replaces the three measured-wrong tests
    (`git log main..HEAD` commit count, `git diff --stat` size, and a
    raw insertion count with no direction check)."""

    def _fake_git(self, diff_by_args: dict, show_by_path: dict):  # noqa: ANN001, ANN201
        """A `_git` stand-in keyed on the exact argv this module calls
        with -- `("diff", "main", "HEAD", "--", ...)` and
        `("show", "main:<path>")` are the only two shapes
        `worktree_content_classification` issues."""

        def fake(args: list[str], cwd: Path) -> str:  # noqa: ARG001
            if args[0] == "diff":
                return diff_by_args.get(tuple(args), "")
            if args[0] == "show":
                return show_by_path.get(args[1], "")
            return ""

        return fake

    def test_stranded_new_content_not_on_main(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """frob:tests scripts/fleet_status.py::worktree_content_classification"""
        diff_args = (
            "diff",
            "main",
            "HEAD",
            "--",
            "src",
            "tests",
            "docs",
            "scripts",
        )
        diff_text = (
            "diff --git a/src/x.py b/src/x.py\n+++ b/src/x.py\n+def brand_new():\n"
        )
        monkeypatch.setattr(
            fleet_status,
            "_git",
            self._fake_git(
                {diff_args: diff_text}, {"main:src/x.py": "def old():\n    pass\n"}
            ),
        )
        verdict, samples = fleet_status.worktree_content_classification(tmp_path)
        assert verdict == "STRANDED"
        assert any("brand_new" in s for s in samples)

    def test_stale_when_content_fully_landed_despite_many_commits(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The failure mode `git log main..HEAD` fell into: land SQUASHES,
        so a worktree whose content fully landed can still show a big
        `main..HEAD` diff in raw form, but every `+` line's text is
        already present on main -- not stranded.
        frob:tests scripts/fleet_status.py::worktree_content_classification"""
        diff_args = (
            "diff",
            "main",
            "HEAD",
            "--",
            "src",
            "tests",
            "docs",
            "scripts",
        )
        diff_text = "diff --git a/src/x.py b/src/x.py\n+++ b/src/x.py\n+def landed():\n"
        monkeypatch.setattr(
            fleet_status,
            "_git",
            self._fake_git(
                {diff_args: diff_text}, {"main:src/x.py": "def landed():\n    pass\n"}
            ),
        )
        verdict, samples = fleet_status.worktree_content_classification(tmp_path)
        assert verdict == "STALE"
        assert samples == []

    def test_stale_when_only_behind_main(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An empty restricted diff (the worktree is purely behind, or the
        diff is entirely outside src/tests/docs/scripts) is STALE, never
        STRANDED. frob:tests scripts/fleet_status.py::worktree_content_classification"""
        monkeypatch.setattr(fleet_status, "_git", self._fake_git({}, {}))
        verdict, samples = fleet_status.worktree_content_classification(tmp_path)
        assert verdict == "STALE"
        assert samples == []

    # frob:ticket T-2755
    def test_active_ticket_never_stranded_or_stale(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A worktree whose branch resolves to a NON-terminal ticket is
        ACTIVE regardless of its diff -- the content test is never even
        run (a stranded-content-shaped diff here would otherwise read
        STRANDED). frob:tests scripts/fleet_status.py::worktree_content_classification"""
        diff_args = (
            "diff",
            "main",
            "HEAD",
            "--",
            "src",
            "tests",
            "docs",
            "scripts",
        )
        diff_text = (
            "diff --git a/src/x.py b/src/x.py\n+++ b/src/x.py\n+def brand_new():\n"
        )
        monkeypatch.setattr(
            fleet_status, "_git", self._fake_git({diff_args: diff_text}, {})
        )
        monkeypatch.setattr(
            fleet_status,
            "ticket_frontmatter_on_main",
            lambda ticket_id: {"state": "in-progress"},
        )
        verdict, samples = fleet_status.worktree_content_classification(
            tmp_path, ticket_ids=["T-2599"]
        )
        assert verdict == "ACTIVE"
        assert samples == []

    # frob:ticket T-2625
    # frob:ticket T-2755
    def test_queued_ticket_with_live_lease_still_active(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2625 positive control: a `queued` ticket that DOES hold a
        live lease record still reads ACTIVE unconditionally -- ACTIVE
        stays the safe direction for anything actually claimed, even in
        the unusual state where a lease outlives a state write."""
        diff_args = (
            "diff",
            "main",
            "HEAD",
            "--",
            "src",
            "tests",
            "docs",
            "scripts",
        )
        diff_text = (
            "diff --git a/src/x.py b/src/x.py\n+++ b/src/x.py\n+def brand_new():\n"
        )
        monkeypatch.setattr(
            fleet_status, "_git", self._fake_git({diff_args: diff_text}, {})
        )
        monkeypatch.setattr(
            fleet_status,
            "ticket_frontmatter_on_main",
            lambda ticket_id: {"state": "queued"},
        )
        monkeypatch.setattr(
            fleet_status,
            "ticket_lease",
            lambda ticket_id: {"ticket_id": ticket_id, "worktree": "/w/t-2625"},
        )
        verdict, samples = fleet_status.worktree_content_classification(
            tmp_path, ticket_ids=["T-2625"]
        )
        assert verdict == "ACTIVE"
        assert samples == []

    # frob:ticket T-2625
    # frob:ticket T-2755
    def test_queued_ticket_with_no_lease_falls_through_to_content_test(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2625 negative control (the ticket's own measured instance):
        a `queued` ticket with NO lease record anywhere is NOT
        automatically ACTIVE -- it falls through to the ordinary content
        test, which here reports STALE for an empty diff. Without this
        fix, `t-1599`'s queued-with-no-lease shape would read identically
        to a genuinely in-progress worktree."""
        monkeypatch.setattr(fleet_status, "_git", self._fake_git({}, {}))
        monkeypatch.setattr(
            fleet_status,
            "ticket_frontmatter_on_main",
            lambda ticket_id: {"state": "queued"},
        )
        monkeypatch.setattr(fleet_status, "ticket_lease", lambda ticket_id: None)
        verdict, samples = fleet_status.worktree_content_classification(
            tmp_path, ticket_ids=["T-1599"]
        )
        assert verdict == "STALE"
        assert samples == []

    # frob:ticket T-2755
    def test_stale_when_terminal_ticket_land_commit_is_ancestor_of_main(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2617: a terminal ticket whose recorded `land_commit` IS an
        ancestor of main is STALE even though its diff LOOKS
        stranded-shaped (new content with no counterpart line on main by
        exact text) -- the real failure mode T-2617 measured: `t-2576`/
        `t-2593` both landed, but the superseding code renamed the
        symbols their own diffs added, so exact-line-text matching alone
        misreads them as STRANDED. `land_commit`-ancestry is the precise
        signal that overrides the diff-shape guess entirely.
        frob:tests scripts/fleet_status.py::worktree_content_classification"""
        diff_args = (
            "diff",
            "main",
            "HEAD",
            "--",
            "src",
            "tests",
            "docs",
            "scripts",
        )
        diff_text = (
            "diff --git a/src/x.py b/src/x.py\n+++ b/src/x.py\n"
            "+_write_baseline(root, fresh, actual_head)\n"
        )
        monkeypatch.setattr(
            fleet_status, "_git", self._fake_git({diff_args: diff_text}, {})
        )
        monkeypatch.setattr(
            fleet_status,
            "ticket_frontmatter_on_main",
            lambda ticket_id: {"state": "done", "land_commit": "deadbeef"},
        )
        monkeypatch.setattr(
            fleet_status, "_is_ancestor_of_main", lambda commit, path: True
        )
        verdict, samples = fleet_status.worktree_content_classification(
            tmp_path, ticket_ids=["T-2576"]
        )
        assert verdict == "STALE"
        assert samples == []

    # frob:ticket T-2755
    def test_stranded_survives_terminal_ticket_with_unlanded_land_commit(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A terminal ticket whose `land_commit` is NOT an ancestor of main
        (dangling/garbage-collected sha, or a ledger edited by hand) falls
        through to the ordinary content test instead of being trusted
        blindly. frob:tests scripts/fleet_status.py::worktree_content_classification"""
        diff_args = (
            "diff",
            "main",
            "HEAD",
            "--",
            "src",
            "tests",
            "docs",
            "scripts",
        )
        diff_text = (
            "diff --git a/src/x.py b/src/x.py\n+++ b/src/x.py\n+def brand_new():\n"
        )
        monkeypatch.setattr(
            fleet_status,
            "_git",
            self._fake_git(
                {diff_args: diff_text}, {"main:src/x.py": "def old():\n    pass\n"}
            ),
        )
        monkeypatch.setattr(
            fleet_status,
            "ticket_frontmatter_on_main",
            lambda ticket_id: {"state": "done", "land_commit": "deadbeef"},
        )
        monkeypatch.setattr(
            fleet_status, "_is_ancestor_of_main", lambda commit, path: False
        )
        verdict, samples = fleet_status.worktree_content_classification(
            tmp_path, ticket_ids=["T-2576"]
        )
        assert verdict == "STRANDED"
        assert any("brand_new" in s for s in samples)

    def test_stale_when_deletion_dominant(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2617: an ad-hoc-named worktree (no resolvable ticket, so no
        `land_commit` to consult) whose diff is overwhelmingly deletion-
        side is STALE -- the `gate-internals` shape T-2617 measured
        (110259 deletions against 12618 insertions, ratio ~8.7), detected
        by magnitude since there is no ticket to check ancestry against.
        frob:tests scripts/fleet_status.py::worktree_content_classification"""
        diff_args = (
            "diff",
            "main",
            "HEAD",
            "--",
            "src",
            "tests",
            "docs",
            "scripts",
        )
        numstat_args = (
            "diff",
            "--numstat",
            "main",
            "HEAD",
            "--",
            "src",
            "tests",
            "docs",
            "scripts",
        )
        diff_text = (
            "diff --git a/src/x.py b/src/x.py\n+++ b/src/x.py\n+def renamed_form():\n"
        )
        numstat_text = "10\t100\tsrc/x.py\n"

        def fake(args: list[str], cwd: Path) -> str:  # noqa: ARG001, ANN001
            if tuple(args) == numstat_args:
                return numstat_text
            if tuple(args) == diff_args:
                return diff_text
            if args and args[0] == "show":
                return ""
            return ""

        monkeypatch.setattr(fleet_status, "_git", fake)
        verdict, samples = fleet_status.worktree_content_classification(tmp_path)
        assert verdict == "STALE"
        assert samples == []

    def test_stranded_survives_a_small_mostly_additive_diff(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The deliberately-constructed T-2617 positive control: an
        ad-hoc-named worktree whose diff is almost entirely additions
        (no deletion-dominant shape to short-circuit on) with a symbol
        genuinely absent from main is still STRANDED -- proves the
        deletion-ratio fallback does not degrade into "everything STALE".
        frob:tests scripts/fleet_status.py::worktree_content_classification"""
        diff_args = (
            "diff",
            "main",
            "HEAD",
            "--",
            "src",
            "tests",
            "docs",
            "scripts",
        )
        numstat_args = (
            "diff",
            "--numstat",
            "main",
            "HEAD",
            "--",
            "src",
            "tests",
            "docs",
            "scripts",
        )
        diff_text = (
            "diff --git a/src/x.py b/src/x.py\n+++ b/src/x.py\n+def never_landed():\n"
        )
        numstat_text = "1\t0\tsrc/x.py\n"

        def fake(args: list[str], cwd: Path) -> str:  # noqa: ARG001, ANN001
            if tuple(args) == numstat_args:
                return numstat_text
            if tuple(args) == diff_args:
                return diff_text
            if args and args[0] == "show" and args[1] == "main:src/x.py":
                return "def old():\n    pass\n"
            return ""

        monkeypatch.setattr(fleet_status, "_git", fake)
        verdict, samples = fleet_status.worktree_content_classification(tmp_path)
        assert verdict == "STRANDED"
        assert any("never_landed" in s for s in samples)


class TestWorktreeTicketId:
    """`fleet_status._worktree_ticket_id` (T-2599)."""

    def test_ticket_named_worktree_resolves(self) -> None:
        """frob:tests scripts/fleet_status.py::_worktree_ticket_id"""
        assert fleet_status._worktree_ticket_id("t-2599") == "T-2599"

    def test_ad_hoc_named_worktree_resolves_to_none(self) -> None:
        """frob:tests scripts/fleet_status.py::_worktree_ticket_id"""
        assert fleet_status._worktree_ticket_id("dev-friction") is None


class TestTicketLease:
    """`fleet_status.ticket_lease` (T-2133)."""

    def test_reads_a_live_lease(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The single `<id>.json` lease file is read and parsed directly."""
        leases_dir = tmp_path / "leases"
        leases_dir.mkdir()
        record = {
            "ticket_id": "T-2114",
            "scope": ["src/x.py"],
            "worktree": "/w",
            "branch": "b",
            "recorded_at": "2026-08-01T00:00:00+00:00",
        }
        (leases_dir / "T-2114.json").write_text(json.dumps(record), encoding="utf-8")
        monkeypatch.setattr(fleet_status, "LEASES", leases_dir)
        assert fleet_status.ticket_lease("T-2114") == record

    def test_no_lease_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """No lease file for this specific id returns None, not an error."""
        leases_dir = tmp_path / "leases"
        leases_dir.mkdir()
        monkeypatch.setattr(fleet_status, "LEASES", leases_dir)
        assert fleet_status.ticket_lease("T-9999") is None

    def test_unreadable_lease_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Malformed JSON reads as '<unreadable>', mirroring `leases()`."""
        leases_dir = tmp_path / "leases"
        leases_dir.mkdir()
        (leases_dir / "T-2114.json").write_text("{not json", encoding="utf-8")
        monkeypatch.setattr(fleet_status, "LEASES", leases_dir)
        assert fleet_status.ticket_lease("T-2114") == {
            "ticket_id": "T-2114",
            "worktree": "<unreadable>",
        }


class TestTicketFrontmatterOnMain:
    """`fleet_status.ticket_frontmatter_on_main` (T-2133)."""

    def test_reads_state_and_scope(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """`state:` and the `scope:` list block are parsed from the
        committed ticket.md's YAML frontmatter."""
        text = (
            "---\n"
            "id: T-2114\n"
            "state: in-progress\n"
            "scope:\n"
            "- src/a.py\n"
            "- 'src/b.py'\n"
            "priority: high\n"
        )
        monkeypatch.setattr(fleet_status, "_git", lambda args, cwd: text)
        assert fleet_status.ticket_frontmatter_on_main("T-2114") == {
            "state": "in-progress",
            "scope": ["src/a.py", "src/b.py"],
            "blocked_by": [],
            "land_commit": None,
        }

    # frob:ticket T-2196
    # frob:tests \
    # tests/unit/coordinator_suite/test_fleet_worktrees.py::TestTicketFrontmatterOnMain\
    # .test_reads_blocked_by
    def test_reads_blocked_by(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The `blocked_by:` list block parses the same way `scope:` does."""
        text = (
            "---\n"
            "id: T-2114\n"
            "state: queued\n"
            "blocked_by:\n"
            "- T-0001\n"
            "- 'T-0002'\n"
            "scope:\n"
            "- src/a.py\n"
            "priority: high\n"
        )
        monkeypatch.setattr(fleet_status, "_git", lambda args, cwd: text)
        assert fleet_status.ticket_frontmatter_on_main("T-2114") == {
            "state": "queued",
            "scope": ["src/a.py"],
            "blocked_by": ["T-0001", "T-0002"],
            "land_commit": None,
        }

    def test_missing_ticket_returns_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """`git show` returning nothing (ticket absent on main) is None."""
        monkeypatch.setattr(fleet_status, "_git", lambda args, cwd: "")
        assert fleet_status.ticket_frontmatter_on_main("T-9999") is None

    # frob:ticket T-2449
    def test_falls_back_to_archive_when_active_ledger_has_no_such_ticket(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2449's own fix: the ACTIVE `tickets/<id>/ticket.md` path
        resolves to nothing (empty git show), so this must fall back to
        `tickets/archive/<id>/ticket.md` before giving up -- the exact
        shape a completed-and-archived blocker has. Confirms the SECOND
        `_git` call (not the first) is what supplies the archived text."""
        archived_text = "---\nid: T-1692\nstate: done\nland_commit: abc123\nscope:\n- src/a.py\n---\n"
        calls: list[list[str]] = []

        def fake_git(args: list[str], cwd) -> str:  # noqa: ANN001
            calls.append(args)
            if "tickets/archive/" in args[-1]:
                return archived_text
            return ""

        monkeypatch.setattr(fleet_status, "_git", fake_git)
        result = fleet_status.ticket_frontmatter_on_main("T-1692")
        assert result == {
            "state": "done",
            "scope": ["src/a.py"],
            "blocked_by": [],
            "land_commit": "abc123",
        }
        assert any("tickets/T-1692/ticket.md" in c[-1] for c in calls)
        assert any("tickets/archive/T-1692/ticket.md" in c[-1] for c in calls)


# frob:ticket T-2449
class TestClassifyBlockers:
    """`fleet_status._classify_blockers` (T-2449): the `main:`-committed
    resolver, archive-aware via `ticket_frontmatter_on_main`."""

    def test_done_blocker_is_closed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            fleet_status,
            "ticket_frontmatter_on_main",
            lambda tid: {"state": "done", "scope": [], "blocked_by": []},
        )
        open_ids, unresolved_ids = fleet_status._classify_blockers(["T-0001"])
        assert open_ids == []
        assert unresolved_ids == []

    def test_archived_done_blocker_is_closed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2449's own measured incident: a blocker that only resolves
        via the archive fallback (`ticket_frontmatter_on_main` handles
        that internally) must still classify as closed, not unresolved
        and not open."""
        monkeypatch.setattr(
            fleet_status,
            "ticket_frontmatter_on_main",
            lambda tid: {"state": "done", "scope": [], "blocked_by": []},
        )
        open_ids, unresolved_ids = fleet_status._classify_blockers(["T-1692", "T-1693"])
        assert open_ids == []
        assert unresolved_ids == []

    def test_in_progress_blocker_is_open(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """MUST-STILL-BLOCK control: a genuinely open blocker still reports
        open -- this fix must never simply stop checking blocked_by."""
        monkeypatch.setattr(
            fleet_status,
            "ticket_frontmatter_on_main",
            lambda tid: {"state": "in-progress", "scope": [], "blocked_by": []},
        )
        open_ids, unresolved_ids = fleet_status._classify_blockers(["T-0002"])
        assert open_ids == ["T-0002"]
        assert unresolved_ids == []

    def test_missing_blocker_is_unresolved_not_open(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Acceptance [2]: a blocker id that resolves nowhere is reported
        in its OWN list, distinct from a genuinely open one."""
        monkeypatch.setattr(
            fleet_status, "ticket_frontmatter_on_main", lambda tid: None
        )
        open_ids, unresolved_ids = fleet_status._classify_blockers(["T-9999"])
        assert open_ids == []
        assert unresolved_ids == ["T-9999"]


# frob:ticket T-2449
class TestClassifyBlockersLocal:
    """`fleet_status._classify_blockers_local` (T-2449): the local-disk
    twin used by `_rotting_entry` so NEEDS DISPATCH agrees with
    `ticket_readiness`."""

    def test_done_archived_blocker_is_closed(self, tmp_path: Path) -> None:
        tickets_dir = tmp_path / "tickets"
        _write_ticket(
            tickets_dir / "archive",
            "T-1692",
            state="done",
            priority="critical",
        )
        open_ids, unresolved_ids = fleet_status._classify_blockers_local(
            ["T-1692"], tickets_dir
        )
        assert open_ids == []
        assert unresolved_ids == []

    def test_queued_blocker_is_open(self, tmp_path: Path) -> None:
        tickets_dir = tmp_path / "tickets"
        _write_ticket(tickets_dir, "T-0002", state="queued", priority="high")
        open_ids, unresolved_ids = fleet_status._classify_blockers_local(
            ["T-0002"], tickets_dir
        )
        assert open_ids == ["T-0002"]
        assert unresolved_ids == []

    def test_missing_blocker_is_unresolved(self, tmp_path: Path) -> None:
        tickets_dir = tmp_path / "tickets"
        tickets_dir.mkdir(parents=True)
        open_ids, unresolved_ids = fleet_status._classify_blockers_local(
            ["T-9999"], tickets_dir
        )
        assert open_ids == []
        assert unresolved_ids == ["T-9999"]


# frob:ticket T-2179
class TestWorktreesTouchingTicket:
    """`fleet_status.worktrees_touching_ticket` (T-2133, scope-aware per
    T-draft-05563e8d)."""

    # frob:ticket T-2179
    def test_finds_a_branch_with_unlanded_commits(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A worktree whose branch has a `main..HEAD` commit that -- in
        that SAME commit's own diff -- touches BOTH `tickets/<id>/` and a
        declared-scope file is reported by name (T-2181: correlation is
        per commit, not per whole branch)."""
        worktrees_dir = tmp_path / "worktrees"
        (worktrees_dir / "one").mkdir(parents=True)
        (worktrees_dir / "two").mkdir(parents=True)
        monkeypatch.setattr(fleet_status, "WORKTREES", worktrees_dir)

        def fake_git(args: list[str], cwd: Path) -> str:
            if cwd.name != "one":
                return ""
            if args[0] == "log":
                return "abc123"
            return "src/a.py\ntickets/T-2114/ticket.md"

        monkeypatch.setattr(fleet_status, "_git", fake_git)
        assert fleet_status.worktrees_touching_ticket("T-2114", ["src/a.py"]) == ["one"]

    # frob:ticket T-2179
    def test_empty_when_nothing_touches_it(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """No worktree with matching commits returns an empty list."""
        worktrees_dir = tmp_path / "worktrees"
        (worktrees_dir / "one").mkdir(parents=True)
        monkeypatch.setattr(fleet_status, "WORKTREES", worktrees_dir)
        monkeypatch.setattr(fleet_status, "_git", lambda args, cwd: "")
        assert fleet_status.worktrees_touching_ticket("T-2114", ["src/a.py"]) == []

    # frob:ticket T-2179
    def test_ledger_only_churn_is_not_reported(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2172 follow-up (the coordinator's own T-2114 incident): a
        branch that touched `tickets/<id>/` (e.g. id-collision-recovery
        renumbering) but NEVER touched a file in the ticket's own declared
        scope must NOT be reported as 'already implemented' -- the exact
        false-positive shape that printed seven unrelated branches for a
        ticket nobody had actually worked."""
        worktrees_dir = tmp_path / "worktrees"
        (worktrees_dir / "one").mkdir(parents=True)
        monkeypatch.setattr(fleet_status, "WORKTREES", worktrees_dir)

        def fake_git(args: list[str], cwd: Path) -> str:
            if args[0] == "log":
                return "abc123"
            # that commit's own diff touches ONLY the ticket's own ledger
            # path, never the declared scope glob below
            return "tickets/T-2114/ticket.md"

        monkeypatch.setattr(fleet_status, "_git", fake_git)
        assert (
            fleet_status.worktrees_touching_ticket(
                "T-2114", ["src/frob/app/ticket_runner/_land_cmd.py"]
            )
            == []
        )

    # frob:ticket T-2179
    def test_empty_scope_globs_never_reports(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """No known scope to check against (empty `scope_globs`) must read
        as 'cannot confirm implementation', never fall back to the old
        looser any-ticket-dir-commit behavior."""
        worktrees_dir = tmp_path / "worktrees"
        (worktrees_dir / "one").mkdir(parents=True)
        monkeypatch.setattr(fleet_status, "WORKTREES", worktrees_dir)
        monkeypatch.setattr(fleet_status, "_git", lambda args, cwd: "abc123")
        assert fleet_status.worktrees_touching_ticket("T-2114", []) == []

    # frob:ticket T-2181
    def test_scope_touch_in_a_different_commit_is_not_correlated(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2181 (T-2179 residue): a branch can have ONE commit that
        touches `tickets/<id>/` (pure ledger bookkeeping -- e.g. a
        `blocked_by` edit made while working a DIFFERENT ticket) and a
        SEPARATE, unrelated commit that touches a file matching this
        ticket's own scope globs (real work done for that OTHER ticket,
        which happens to share a scope-glob file). Measured for real:
        `--ticket T-2114` reported `t-2107` and `t2049-series`, neither of
        which had implemented T-2114 -- each had one commit touching
        `tickets/T-2114/` and a wholly separate commit touching
        `_land_cmd.py` for its own ticket (T-2108, T-2049). Correlating at
        the WHOLE-BRANCH level (the pre-fix behavior) reported the branch
        anyway, because it only asked "does any commit touch the ticket
        dir" and "does the whole diff touch scope" as two independent
        questions. Fixed behavior: correlation happens PER COMMIT (`git
        show --name-only` on each commit that itself touches
        `tickets/<id>/`), so the branch's OTHER commit -- which touches
        the scope file but never `tickets/T-2114/` -- is never seen by
        this function at all."""
        worktrees_dir = tmp_path / "worktrees"
        (worktrees_dir / "one").mkdir(parents=True)
        monkeypatch.setattr(fleet_status, "WORKTREES", worktrees_dir)

        def fake_git(args: list[str], cwd: Path) -> str:
            if args[0] == "log":
                # one commit touches only the ticket dir (bookkeeping)
                return "aaa111"
            if args[0] == "show":
                sha = args[-1]
                if sha == "aaa111":
                    return "tickets/T-2114/ticket.md"
                return ""
            return ""

        monkeypatch.setattr(fleet_status, "_git", fake_git)
        assert (
            fleet_status.worktrees_touching_ticket(
                "T-2114", ["src/frob/app/ticket_runner/_land_cmd.py"]
            )
            == []
        )

    # frob:ticket T-2747
    def test_non_conventionally_named_worktree_matches_via_start_transition(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2747 positive control 1: a worktree named after its SUBJECT
        (`waive-liveness`, the real T-2740 shape) rather than `t-<id>`
        still matches -- because its own `main..HEAD` history carries the
        start-transition commit `commit_start_transition` writes, the
        dispatch condition no longer depends on the directory name at
        all."""
        worktrees_dir = tmp_path / "worktrees"
        (worktrees_dir / "waive-liveness").mkdir(parents=True)
        monkeypatch.setattr(fleet_status, "WORKTREES", worktrees_dir)

        # Realistic per-commit shape (matches the real T-2740 measurement):
        # the start-transition commit and the real scope-touching commit
        # are TWO SEPARATE commits -- no single commit touches both
        # `tickets/T-2740/` and scope, so the OLD dual-correlation check
        # genuinely returns False here (proving this is a real repro, not
        # a mock coincidence): only the NEW started-ticket fast path can
        # see the scope-touching commit at all.
        def fake_git(args: list[str], cwd: Path) -> str:
            if args[0] == "log" and args[-1] == "--format=%s":
                return "chore(tickets): record T-2740 start transition"
            if args[0] == "log" and args[-1] == "tickets/T-2740/":
                return "aaa111"  # ledger-only bookkeeping commit
            if args[0] == "log":
                return "bbb222"  # the real, separate scope-touching commit
            if args[0] == "show":
                sha = args[-1]
                if sha == "aaa111":
                    return "tickets/T-2740/ticket.md"
                if sha == "bbb222":
                    return "src/a.py"
                return ""
            return ""

        monkeypatch.setattr(fleet_status, "_git", fake_git)
        assert fleet_status.worktrees_touching_ticket("T-2740", ["src/a.py"]) == [
            "waive-liveness"
        ]

    # frob:ticket T-2747
    def test_series_worktree_matches_sibling_ticket_via_start_transition(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2747 positive control 2: a worktree named for ticket A
        (`t2738-t2737`, named after T-2738) that ALSO started sibling
        ticket B (T-2737, the standard series-dispatch pattern) resolves
        B too -- the real shape the old `t-<id>`-regex fast path could
        never see, since the name only ever resolves to one id."""
        worktrees_dir = tmp_path / "worktrees"
        (worktrees_dir / "t2738-t2737").mkdir(parents=True)
        monkeypatch.setattr(fleet_status, "WORKTREES", worktrees_dir)

        # Same realistic per-commit split as the sibling test above: the
        # T-2737 start-transition commit and its own real scope-touching
        # commit are separate commits, so the OLD dual-correlation check
        # (which the worktree's NAME resolves to T-2738, never T-2737)
        # genuinely cannot see T-2737 as reached here either way -- this
        # proves the NEW started-ticket path is what recovers it.
        def fake_git(args: list[str], cwd: Path) -> str:
            if args[0] == "log" and args[-1] == "--format=%s":
                return (
                    "chore(tickets): record T-2738 start transition\n"
                    "chore(tickets): record T-2737 start transition"
                )
            if args[0] == "log" and args[-1] == "tickets/T-2737/":
                return "ccc333"  # ledger-only bookkeeping commit
            if args[0] == "log":
                return "ddd444"  # the real, separate scope-touching commit
            if args[0] == "show":
                sha = args[-1]
                if sha == "ccc333":
                    return "tickets/T-2737/ticket.md"
                if sha == "ddd444":
                    return "src/b.py"
                return ""
            return ""

        monkeypatch.setattr(fleet_status, "_git", fake_git)
        assert fleet_status.worktrees_touching_ticket("T-2737", ["src/b.py"]) == [
            "t2738-t2737"
        ]

    # frob:ticket T-2747
    def test_a_leaked_ticket_with_no_worktree_anywhere_still_reports_empty(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2747 positive control 3 (the detector's purpose must
        survive): a ticket genuinely abandoned -- no worktree started it,
        no worktree touches its scope -- must still resolve to no hits at
        all, i.e. still read as a leak. Without this, the fix would have
        traded a false LEAK for a false LIVE, which is the more dangerous
        direction (a stranded lease would never get reclaimed)."""
        worktrees_dir = tmp_path / "worktrees"
        (worktrees_dir / "unrelated").mkdir(parents=True)
        monkeypatch.setattr(fleet_status, "WORKTREES", worktrees_dir)

        def fake_git(args: list[str], cwd: Path) -> str:
            if args[0] == "log" and args[-1] == "--format=%s":
                return "chore(tickets): record T-9999 start transition"
            if args[0] == "log":
                return ""
            return ""

        monkeypatch.setattr(fleet_status, "_git", fake_git)
        assert fleet_status.worktrees_touching_ticket("T-2114", ["src/a.py"]) == []


class TestWorktreeStartedTicket:
    """`fleet_status._worktree_started_ticket` (T-2747)."""

    def test_true_when_start_transition_commit_present(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """frob:tests scripts/fleet_status.py::_worktree_started_ticket"""

        def fake_git(args: list[str], cwd: Path) -> str:
            return "chore(tickets): record T-2740 start transition"

        monkeypatch.setattr(fleet_status, "_git", fake_git)
        assert fleet_status._worktree_started_ticket(tmp_path, "T-2740") is True

    def test_false_when_absent(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """frob:tests scripts/fleet_status.py::_worktree_started_ticket"""

        def fake_git(args: list[str], cwd: Path) -> str:
            return "some other commit subject"

        monkeypatch.setattr(fleet_status, "_git", fake_git)
        assert fleet_status._worktree_started_ticket(tmp_path, "T-2740") is False


class TestScopeIntersections:
    """`fleet_status.scope_intersections` (T-2180)."""

    def test_reports_overlapping_pair(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Two tickets whose effective scope shares a glob are reported as
        a colliding pair, with the overlapping glob(s) named -- the
        T-1748/T-1780 shape (a five-ticket docs series all scoped to the
        same file, then a sixth ticket claiming it again with no
        override)."""
        monkeypatch.setattr(
            fleet_status,
            "ticket_readiness",
            lambda tid: {
                "ticket_id": tid,
                "lease": None,
                "main": {
                    "state": "queued",
                    "scope": ["docs/modules/tickets.md"],
                },
            },
        )
        monkeypatch.setattr(fleet_status, "leases", lambda: [])
        collisions = fleet_status.scope_intersections(["T-1748", "T-1780"])
        assert len(collisions) == 1
        assert collisions[0]["a"] == "T-1748"
        assert collisions[0]["b"] == "T-1780"
        assert ("docs/modules/tickets.md", "docs/modules/tickets.md") in collisions[0][
            "overlapping_globs"
        ]

    def test_no_overlap_reports_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Disjoint declared scopes report no collisions at all."""

        def fake_readiness(tid: str) -> dict:
            scope = ["src/a.py"] if tid == "T-1" else ["src/b.py"]
            return {
                "ticket_id": tid,
                "lease": None,
                "main": {"state": "queued", "scope": scope},
            }

        monkeypatch.setattr(fleet_status, "ticket_readiness", fake_readiness)
        monkeypatch.setattr(fleet_status, "leases", lambda: [])
        assert fleet_status.scope_intersections(["T-1", "T-2"]) == []

    def test_checks_against_a_held_lease_outside_the_requested_set(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A requested ticket's effective scope is ALSO checked against
        every held lease not already in the requested set, so a
        coordinator sees external contention against an already in-flight
        lease, not just contention within the wave being vetted."""
        monkeypatch.setattr(
            fleet_status,
            "ticket_readiness",
            lambda tid: {
                "ticket_id": tid,
                "lease": None,
                "main": {"state": "queued", "scope": ["src/shared.py"]},
            },
        )
        monkeypatch.setattr(
            fleet_status,
            "leases",
            lambda: [{"ticket_id": "T-9999", "scope": ["src/shared.py"]}],
        )
        collisions = fleet_status.scope_intersections(["T-1"])
        assert len(collisions) == 1
        assert collisions[0] == {
            "a": "T-1",
            "b": "T-9999",
            "overlapping_globs": [("src/shared.py", "src/shared.py")],
        }


def _run_git(args: list[str], cwd: Path) -> str:
    """Run real `git` (no mock) for `TestWorktreeContentClassificationLiveGit`'s
    fixture setup, raising on any non-zero exit -- fixture-building code
    should fail loudly, unlike `fleet_status._git`'s own defensive `""`
    return."""
    done = subprocess.run(
        ["git", "-C", str(cwd), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return done.stdout.strip()


# frob:ticket T-2755
# frob:waive WIRE001 reason="private test-fixture helper used only by this file's own \
# tests -- no production caller to wire it to by design" permanent="true"
def _init_bare_repo(root: Path) -> None:
    """A bare `git init -b main` plus committer identity for `_run_git`-
    based live-git fixtures -- module-level, replacing THREE identical
    private per-class `_init_repo(self, root)` methods
    (`TestWorktreeContentClassificationLiveGit`, `TestInProgressTicket
    ScopeLeasesLiveGit`, and this ticket's own new `TestWorktreeStarted
    TicketIds`) that all carried the exact same 3-line body -- T-2755
    consolidates them into the one home NO DUPLICATION calls for, rather
    than adding a fourth copy alongside the other two. `TestResolveRepo
    Root._init_repo` is NOT one of the three: it also commits a README,
    a genuinely different fixture shape, so it stays its own method."""
    _run_git(["init", "-q", "-b", "main"], root)
    _run_git(["config", "user.email", "test@example.com"], root)
    _run_git(["config", "user.name", "Test"], root)


class TestResolveRepoRoot:
    """`fleet_status._resolve_repo_root` -- REPO must resolve to the SHARED
    primary checkout regardless of which linked worktree the script runs
    from (T-2677: `__file__`-derived resolution silently reported 0 live
    leases fleet-wide when run from inside a worktree, because a
    worktree's own `.git` is a FILE, not a directory)."""

    def _init_repo(self, root: Path) -> None:
        _run_git(["init", "-q", "-b", "main"], root)
        _run_git(["config", "user.email", "test@example.com"], root)
        _run_git(["config", "user.name", "Test"], root)
        (root / "README.md").write_text("x\n")
        _run_git(["add", "-A"], root)
        _run_git(["commit", "-q", "-m", "c1"], root)

    def test_positive_control_matches_primary_checkout(self, tmp_path: Path) -> None:
        """The exact real-world shape T-2677 measured: resolving from
        inside a linked worktree must return the SAME root as resolving
        from the primary checkout itself, for the same real repo.
        frob:tests scripts/fleet_status.py::_resolve_repo_root"""
        repo = tmp_path / "repo"
        repo.mkdir()
        self._init_repo(repo)
        worktree = tmp_path / "wt"
        _run_git(["worktree", "add", "-q", "-b", "wt-branch", str(worktree)], repo)

        from_primary = fleet_status._resolve_repo_root(repo)
        from_worktree = fleet_status._resolve_repo_root(worktree)

        assert from_primary.resolve() == repo.resolve()
        assert from_worktree.resolve() == repo.resolve()
        assert from_worktree.resolve() == from_primary.resolve()

    def test_falls_back_when_not_a_git_checkout(self, tmp_path: Path) -> None:
        """Outside any git checkout (git itself unavailable/refuses),
        the `__file__`-derived fallback is returned rather than raising.
        frob:tests scripts/fleet_status.py::_resolve_repo_root"""
        not_a_repo = tmp_path / "not-a-repo"
        not_a_repo.mkdir()
        result = fleet_status._resolve_repo_root(not_a_repo)
        assert result == not_a_repo


# frob:ticket T-2755
class TestWorktreeStartedTicketIds:
    """T-2755: `_worktree_started_ticket_ids` reads back EVERY ticket id
    a worktree's own unlanded history (`main..HEAD`) structurally
    started, with no assumption about the worktree's directory NAME --
    the reverse direction of T-2747's `_worktree_started_ticket` (which
    checks one candidate id) and the fix for `worktree_content_
    classification`'s own naming-convention short-circuit (T-2599's
    `_worktree_ticket_id`, a `t-<id>`-only match), which silently
    resolved to `None` for most of this fleet's real worktree names."""

    # frob:ticket T-2755
    def test_non_conventionally_named_worktree_resolves(self, tmp_path: Path) -> None:
        """T-2755 must-now-fire: a worktree named after its SUBJECT
        (`waive-liveness`, T-2740's own real name per T-2747's docstring)
        -- `_worktree_ticket_id("waive-liveness")` returns `None` (no
        `t-<id>` match), but the structural resolver still finds the
        started id from the worktree's own history.
        frob:tests scripts/fleet_status.py::_worktree_started_ticket_ids"""
        repo = tmp_path / "repo"
        repo.mkdir()
        _init_bare_repo(repo)
        (repo / "x.txt").write_text("x\n")
        _run_git(["add", "-A"], repo)
        _run_git(["commit", "-q", "-m", "c1"], repo)

        worktree = tmp_path / "waive-liveness"
        _run_git(["worktree", "add", "-q", "-b", "waive-liveness", str(worktree)], repo)
        (worktree / "x.txt").write_text("x\nchanged\n")
        _run_git(["add", "-A"], worktree)
        _run_git(
            ["commit", "-q", "-m", "chore(tickets): record T-2740 start transition"],
            worktree,
        )

        assert fleet_status._worktree_started_ticket_ids(worktree) == ["T-2740"]
        assert fleet_status._worktree_ticket_id("waive-liveness") is None

    # frob:ticket T-2755
    def test_no_start_transition_commits_resolves_empty(self, tmp_path: Path) -> None:
        """Negative control: a worktree with unlanded commits but NONE
        of them the canonical start-transition subject resolves to `[]`,
        never force-matched to a ticket id it never structurally started.
        frob:tests scripts/fleet_status.py::_worktree_started_ticket_ids"""
        repo = tmp_path / "repo"
        repo.mkdir()
        _init_bare_repo(repo)
        (repo / "x.txt").write_text("x\n")
        _run_git(["add", "-A"], repo)
        _run_git(["commit", "-q", "-m", "c1"], repo)

        worktree = tmp_path / "scratch-experiment"
        _run_git(
            ["worktree", "add", "-q", "-b", "scratch-experiment", str(worktree)], repo
        )
        (worktree / "x.txt").write_text("x\nchanged\n")
        _run_git(["add", "-A"], worktree)
        _run_git(["commit", "-q", "-m", "wt: unrelated change"], worktree)

        assert fleet_status._worktree_started_ticket_ids(worktree) == []

    # frob:ticket T-2755
    def test_series_worktree_resolves_every_started_id(self, tmp_path: Path) -> None:
        """T-2755 must-now-fire: a grouped-dispatch series worktree
        (`t2763-t2359`-shaped: named for one ticket, holding several)
        structurally started TWO ids -- both resolve, not just the one
        embedded in the directory name.
        frob:tests scripts/fleet_status.py::_worktree_started_ticket_ids"""
        repo = tmp_path / "repo"
        repo.mkdir()
        _init_bare_repo(repo)
        (repo / "x.txt").write_text("x\n")
        _run_git(["add", "-A"], repo)
        _run_git(["commit", "-q", "-m", "c1"], repo)

        worktree = tmp_path / "t2763-t2359"
        _run_git(["worktree", "add", "-q", "-b", "t2763-t2359", str(worktree)], repo)
        (worktree / "x.txt").write_text("x\nchanged once\n")
        _run_git(["add", "-A"], worktree)
        _run_git(
            ["commit", "-q", "-m", "chore(tickets): record T-2763 start transition"],
            worktree,
        )
        (worktree / "x.txt").write_text("x\nchanged once\nchanged twice\n")
        _run_git(["add", "-A"], worktree)
        _run_git(
            ["commit", "-q", "-m", "chore(tickets): record T-2359 start transition"],
            worktree,
        )

        assert fleet_status._worktree_started_ticket_ids(worktree) == [
            "T-2359",
            "T-2763",
        ]

# frob:ticket T-2755
class TestWorktreeContentClassificationLiveGit:
    """T-2617: `worktree_content_classification` run UNMOCKED against a
    real git repository built from real commits -- `_git` itself is not
    monkeypatched here, only `fleet_status.REPO` (so `ticket_frontmatter_
    on_main`'s ticket-ledger lookups resolve against the fixture repo
    instead of this actual project). T-2617's own root cause was that
    `TestWorktreeContentClassification`'s string-fixture mocks never
    constructed the SUPERSEDED-symbol case (a function renamed by the
    code that replaced it has no byte-identical counterpart line, so the
    old exact-line-text check misread real landed work as stranded) --
    these tests reproduce that shape with genuine `git diff`/`git show`/
    `git merge-base` output, not hand-written diff text, closing exactly
    the gap T-2617 found."""

    # frob:ticket T-2755
    def test_superseded_symbol_with_landed_terminal_ticket_is_stale(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The exact real-data shape T-2617 measured: `t-2576`'s worktree
        carries `_write_baseline(...)`, main's current file carries
        `_write_baseline_cas(...)` instead -- no byte-identical line in
        common, but the ticket is `done` and its `land_commit` IS an
        ancestor of main, so the correct verdict is STALE.
        frob:tests scripts/fleet_status.py::worktree_content_classification"""
        repo = tmp_path / "repo"
        repo.mkdir()
        _init_bare_repo(repo)
        src = repo / "src"
        src.mkdir()
        (src / "x.py").write_text(
            "def _write_baseline(root, fresh, actual_head):\n    pass\n"
        )
        tdir = repo / "tickets" / "T-9001"
        tdir.mkdir(parents=True)
        (tdir / "ticket.md").write_text("---\nid: T-9001\nstate: queued\n---\n")
        _run_git(["add", "-A"], repo)
        _run_git(["commit", "-q", "-m", "c1: original _write_baseline"], repo)

        worktree = tmp_path / "t-9001"
        _run_git(["worktree", "add", "-q", "-b", "t-9001", str(worktree)], repo)

        (src / "x.py").write_text(
            "def _write_baseline_cas(root, fresh, actual_head):\n    pass\n"
        )
        _run_git(["add", "-A"], repo)
        _run_git(["commit", "-q", "-m", "c2: supersede with _write_baseline_cas"], repo)
        land_sha = _run_git(["rev-parse", "HEAD"], repo)

        (tdir / "ticket.md").write_text(
            f"---\nid: T-9001\nstate: done\nland_commit: {land_sha}\n---\n"
        )
        _run_git(["add", "-A"], repo)
        _run_git(["commit", "-q", "-m", "c3: mark T-9001 done"], repo)

        monkeypatch.setattr(fleet_status, "REPO", repo)
        verdict, samples = fleet_status.worktree_content_classification(
            worktree, ticket_ids=["T-9001"]
        )
        assert verdict == "STALE"
        assert samples == []

    def test_genuinely_new_symbol_absent_from_main_is_stranded(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2617's mandatory deliberately-constructed positive control:
        an ad-hoc-named worktree (no resolvable ticket) holding a symbol
        that never existed on main at all, with a mostly-additive diff
        (no deletion-dominant shape to short-circuit on), is STRANDED --
        proves the T-2617 fix does not degrade into labelling everything
        STALE. frob:tests scripts/fleet_status.py::worktree_content_classification"""
        repo = tmp_path / "repo"
        repo.mkdir()
        _init_bare_repo(repo)
        src = repo / "src"
        src.mkdir()
        (src / "x.py").write_text("def existing():\n    pass\n")
        _run_git(["add", "-A"], repo)
        _run_git(["commit", "-q", "-m", "c1: existing() only"], repo)

        worktree = tmp_path / "adhoc-experiment"
        _run_git(
            ["worktree", "add", "-q", "-b", "adhoc-experiment", str(worktree)], repo
        )
        (worktree / "src" / "x.py").write_text(
            "def existing():\n    pass\n\n\ndef never_landed_anywhere():\n    return 1\n"
        )
        _run_git(["add", "-A"], worktree)
        _run_git(["commit", "-q", "-m", "wt: add never_landed_anywhere"], worktree)

        monkeypatch.setattr(fleet_status, "REPO", repo)
        verdict, samples = fleet_status.worktree_content_classification(worktree)
        assert verdict == "STRANDED"
        assert any("never_landed_anywhere" in s for s in samples)

    def test_far_behind_main_with_no_ticket_is_stale(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2617's other real-data shape: `gate-internals` -- an ad-hoc
        long-idle worktree with no resolvable ticket, whose diff is
        overwhelmingly deletion-dominated because main simply moved on.
        frob:tests scripts/fleet_status.py::worktree_content_classification"""
        repo = tmp_path / "repo"
        repo.mkdir()
        _init_bare_repo(repo)
        src = repo / "src"
        src.mkdir()
        original = "\n".join(f"def fn_{i}():\n    pass\n" for i in range(40))
        (src / "x.py").write_text(original)
        _run_git(["add", "-A"], repo)
        _run_git(["commit", "-q", "-m", "c1: 40 functions"], repo)

        worktree = tmp_path / "gate-internals"
        _run_git(["worktree", "add", "-q", "-b", "gate-internals", str(worktree)], repo)
        # worktree adds one small tweak of its own and never syncs again
        (worktree / "src" / "x.py").write_text(
            original + "\ndef fn_extra_local():\n    pass\n"
        )
        _run_git(["add", "-A"], worktree)
        _run_git(["commit", "-q", "-m", "wt: small local addition"], worktree)

        # main meanwhile grows a lot (the original 40 functions are left
        # untouched -- deletions here come from NEW main-side content the
        # worktree never picked up, the real "far behind" shape, not a
        # rename/rewrite of shared content)
        grown = (
            original
            + "\n"
            + "\n".join(
                f"def fn_new_{i}():\n    pass\n    pass\n    pass\n" for i in range(60)
            )
        )
        (src / "x.py").write_text(grown)
        _run_git(["add", "-A"], repo)
        _run_git(["commit", "-q", "-m", "c2: main grows a lot"], repo)

        monkeypatch.setattr(fleet_status, "REPO", repo)
        verdict, samples = fleet_status.worktree_content_classification(worktree)
        assert verdict == "STALE"
        assert samples == []

    # frob:ticket T-2625
    # frob:ticket T-2755
    def test_queued_ticket_no_lease_falls_through_to_real_content_test(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2625's own measured shape, reproduced with real git state
        (not a string-fixture mock, per the T-2617 precedent this test
        class exists to hold to): a `queued` ticket with genuinely
        stranded content and NO lease file anywhere falls through the
        (now-conditional) ACTIVE short-circuit into the real, unmocked
        `git diff`/`git show` content test below it, which correctly
        reports STRANDED for content absent from main -- proving the fix
        does not just change a state-comparison in isolation, it changes
        what the REAL classifier does end to end for T-1599's exact
        shape (queued, no lease, some local diff)."""
        repo = tmp_path / "repo"
        repo.mkdir()
        _init_bare_repo(repo)
        src = repo / "src"
        src.mkdir()
        (src / "x.py").write_text("def existing():\n    pass\n")
        tdir = repo / "tickets" / "T-1599"
        tdir.mkdir(parents=True)
        (tdir / "ticket.md").write_text("---\nid: T-1599\nstate: queued\n---\n")
        _run_git(["add", "-A"], repo)
        _run_git(["commit", "-q", "-m", "c1: existing() plus queued ticket"], repo)

        worktree = tmp_path / "t-1599"
        _run_git(["worktree", "add", "-q", "-b", "t-1599", str(worktree)], repo)
        (worktree / "src" / "x.py").write_text(
            "def existing():\n    pass\n\n\ndef never_landed_anywhere():\n    return 1\n"
        )
        _run_git(["add", "-A"], worktree)
        _run_git(["commit", "-q", "-m", "wt: add never_landed_anywhere"], worktree)

        monkeypatch.setattr(fleet_status, "REPO", repo)
        # No lease file anywhere for T-1599 -- point LEASES at an empty
        # directory so this does not accidentally read this actual
        # project's own real .git/frob-leases/ (LEASES is a module-level
        # constant fixed at import time from the REAL REPO, not
        # re-derived from the patched REPO above).
        monkeypatch.setattr(fleet_status, "LEASES", tmp_path / "no-leases")
        verdict, samples = fleet_status.worktree_content_classification(
            worktree, ticket_ids=["T-1599"]
        )
        assert verdict == "STRANDED"
        assert any("never_landed_anywhere" in s for s in samples)

    # frob:ticket T-2755
    def test_non_conventionally_named_worktree_classifies_active_via_structural_ids(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2755 must-now-fire, end to end: a subject-named worktree
        (`waive-liveness`-shaped) holding an in-progress ticket must
        classify ACTIVE when its ids are resolved structurally
        (`_worktree_started_ticket_ids`) instead of via the old `t-<id>`
        naming convention (`_worktree_ticket_id("waive-liveness")` is
        `None`, which is exactly why this used to fall through to the
        raw content diff and could misreport STRANDED/STALE for
        genuinely active work).
        frob:tests scripts/fleet_status.py::worktree_content_classification"""
        repo = tmp_path / "repo"
        repo.mkdir()
        _init_bare_repo(repo)
        src = repo / "src"
        src.mkdir()
        (src / "x.py").write_text("def existing():\n    pass\n")
        tdir = repo / "tickets" / "T-2740"
        tdir.mkdir(parents=True)
        (tdir / "ticket.md").write_text("---\nid: T-2740\nstate: in-progress\n---\n")
        _run_git(["add", "-A"], repo)
        _run_git(["commit", "-q", "-m", "c1: existing() plus in-progress ticket"], repo)

        worktree = tmp_path / "waive-liveness"
        _run_git(["worktree", "add", "-q", "-b", "waive-liveness", str(worktree)], repo)
        _run_git(
            [
                "commit",
                "-q",
                "--allow-empty",
                "-m",
                "chore(tickets): record T-2740 start transition",
            ],
            worktree,
        )
        (worktree / "src" / "x.py").write_text(
            "def existing():\n    pass\n\n\ndef in_progress_work():\n    return 1\n"
        )
        _run_git(["add", "-A"], worktree)
        _run_git(["commit", "-q", "-m", "wt: work in progress on T-2740"], worktree)

        monkeypatch.setattr(fleet_status, "REPO", repo)
        verdict, samples = fleet_status.worktree_content_classification(
            worktree,
            ticket_ids=fleet_status._worktree_started_ticket_ids(worktree),
        )
        assert verdict == "ACTIVE"
        assert samples == []

    # frob:ticket T-2755
    def test_worktree_with_genuinely_no_ticket_is_not_force_matched(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2755 negative control: a worktree that never ran `frob
        ticket start`/`work` at all (no start-transition commit anywhere
        in its history) must resolve `ticket_ids=[]` from the structural
        scan and fall through to the ordinary content test -- never
        force-matched to a ticket it never started, and never crashes on
        an empty id list.
        frob:tests scripts/fleet_status.py::worktree_content_classification"""
        repo = tmp_path / "repo"
        repo.mkdir()
        _init_bare_repo(repo)
        src = repo / "src"
        src.mkdir()
        (src / "x.py").write_text("def existing():\n    pass\n")
        _run_git(["add", "-A"], repo)
        _run_git(["commit", "-q", "-m", "c1: existing() only"], repo)

        worktree = tmp_path / "no-ticket-scratch"
        _run_git(
            ["worktree", "add", "-q", "-b", "no-ticket-scratch", str(worktree)], repo
        )
        (worktree / "src" / "x.py").write_text(
            "def existing():\n    pass\n\n\ndef scratch_only():\n    return 1\n"
        )
        _run_git(["add", "-A"], worktree)
        _run_git(["commit", "-q", "-m", "wt: scratch change, no ticket"], worktree)

        monkeypatch.setattr(fleet_status, "REPO", repo)
        started = fleet_status._worktree_started_ticket_ids(worktree)
        assert started == []
        verdict, samples = fleet_status.worktree_content_classification(
            worktree, ticket_ids=started
        )
        assert verdict == "STRANDED"
        assert any("scratch_only" in s for s in samples)

# frob:ticket T-2665
class TestInProgressTicketScopeLeasesLiveGit:
    """T-2665: `in_progress_ticket_scope_leases`'s fallback (`_resolve_
    worktree_for_in_progress_ticket`'s `worktrees_touching_ticket` scan)
    run against a REAL `git worktree add`, not a string/JSON fixture --
    the T-2617 precedent this class follows: the measured incident was a
    ticket whose LEASE FILE had been removed (`.git/frob-leases/*.json`
    is unlinked opportunistically, per T-2651's own docstring) while a
    real `git worktree` for it still existed on disk with an unlanded
    commit. `TestInProgressTicketScopeLeases`'s own mocked tests cover
    the lease-file-present path faithfully, but never construct a real
    worktree at all, so they cannot tell a genuine fallback-scan success
    apart from a fixture that merely looks right."""

    def test_live_worktree_with_lease_file_removed_is_not_leaked(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2665's own measured shape: T-2583 was `in-progress` with a
        real `git worktree` on branch `t-2583` and an unlanded commit
        touching its declared scope, but NO `.git/frob-leases/T-2583.json`
        (removed, whether by the T-2651-documented opportunistic unlink
        or by hand) -- the detector reported `[LEAK]` anyway. This
        reproduces that exact combination with real git state: a real
        worktree, a real commit inside it that touches the ticket's own
        scope file, and an EMPTY leases directory (no lease file for this
        ticket at all, not even a stale one)."""
        repo = tmp_path / "repo"
        repo.mkdir()
        _init_bare_repo(repo)
        src = repo / "src"
        src.mkdir()
        (src / "a.py").write_text("def existing():\n    pass\n")
        tdir = repo / "tickets" / "T-2583"
        tdir.mkdir(parents=True)
        (tdir / "ticket.md").write_text(
            "---\nid: T-2583\nstate: in-progress\nscope:\n- src/a.py\n---\n"
        )
        _run_git(["add", "-A"], repo)
        _run_git(["commit", "-q", "-m", "c1: existing() plus in-progress ticket"], repo)

        worktree = tmp_path / "t-2583"
        _run_git(["worktree", "add", "-q", "-b", "t-2583", str(worktree)], repo)
        (worktree / "src" / "a.py").write_text(
            "def existing():\n    pass\n\n\ndef fix_applied():\n    return 1\n"
        )
        _run_git(["add", "-A"], worktree)
        _run_git(["commit", "-q", "-m", "wt: work in progress on T-2583"], worktree)

        monkeypatch.setattr(fleet_status, "REPO", repo)
        monkeypatch.setattr(fleet_status, "TICKETS_DIR", repo / "tickets")
        monkeypatch.setattr(fleet_status, "WORKTREES", tmp_path)
        # No lease file anywhere for T-2583 -- the exact measured shape.
        monkeypatch.setattr(fleet_status, "LEASES", tmp_path / "no-leases")

        entries = fleet_status.in_progress_ticket_scope_leases()
        assert entries == [
            {
                "ticket_id": "T-2583",
                "scope": ["src/a.py"],
                "worktree": "t-2583",
                "leaked": False,
            }
        ], (
            "a live worktree with an unlanded commit touching the "
            "ticket's own scope must resolve via the fallback scan and "
            "must NOT report leaked=True, even with no lease file at all"
        )

    def test_no_worktree_and_no_lease_is_still_leaked(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Positive control (must-still-pass direction), same real-git
        harness: an in-progress ticket with NEITHER a lease file NOR any
        worktree at all is still reported `leaked=True` -- T-2377's own
        original shape, the reason this detector exists. Without this, a
        fix for the false-LEAK direction could silently regress into
        never reporting a real leak again."""
        repo = tmp_path / "repo"
        repo.mkdir()
        _init_bare_repo(repo)
        src = repo / "src"
        src.mkdir()
        (src / "a.py").write_text("def existing():\n    pass\n")
        tdir = repo / "tickets" / "T-2377"
        tdir.mkdir(parents=True)
        (tdir / "ticket.md").write_text(
            "---\nid: T-2377\nstate: in-progress\nscope:\n- src/a.py\n---\n"
        )
        _run_git(["add", "-A"], repo)
        _run_git(["commit", "-q", "-m", "c1: existing() plus in-progress ticket"], repo)

        monkeypatch.setattr(fleet_status, "REPO", repo)
        monkeypatch.setattr(fleet_status, "TICKETS_DIR", repo / "tickets")
        monkeypatch.setattr(fleet_status, "WORKTREES", tmp_path / "no-worktrees")
        monkeypatch.setattr(fleet_status, "LEASES", tmp_path / "no-leases")

        entries = fleet_status.in_progress_ticket_scope_leases()
        assert entries == [
            {
                "ticket_id": "T-2377",
                "scope": ["src/a.py"],
                "worktree": None,
                "leaked": True,
            }
        ]

    # frob:ticket T-3403
    def test_freshly_started_worktree_with_no_scope_commit_yet_is_not_leaked(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """MUST-FIRE (T-3403's own measured shape): T-3394 was `in-
        progress` with a real, live `git worktree` -- WORKTREES listed it
        with a 7-minute-old commit -- but LEASES reported it `[LEAK]` in
        the SAME invocation. Reproduced here with the two disagreeing
        code paths named: `worktrees()` (line ~448) unconditionally lists
        every directory under `WORKTREES`, with no ticket correlation at
        all, so a worktree that has done nothing but `frob ticket start`
        (one commit: the start-transition ledger commit,
        `chore(tickets): record <id> start transition`) still appears.
        `_resolve_worktree_for_in_progress_ticket` (line ~422), by
        contrast, falls back to `worktrees_touching_ticket` (line ~1207)
        when no lease file exists -- and THAT requires an unlanded commit
        that touches the ticket's own declared SCOPE files, which a
        just-started worktree with only its start-transition commit does
        not have yet. The two paths disagree because one asks "does a
        directory exist" and the other asks "has real implementation
        work landed" -- a freshly-started, genuinely-live worktree
        satisfies the first and fails the second, and only the second
        drives the leak verdict."""
        repo = tmp_path / "repo"
        repo.mkdir()
        _init_bare_repo(repo)
        src = repo / "src"
        src.mkdir()
        (src / "a.py").write_text("def existing():\n    pass\n")
        tdir = repo / "tickets" / "T-3394"
        tdir.mkdir(parents=True)
        (tdir / "ticket.md").write_text(
            "---\nid: T-3394\nstate: in-progress\nscope:\n- src/a.py\n---\n"
        )
        _run_git(["add", "-A"], repo)
        _run_git(["commit", "-q", "-m", "c1: existing() plus in-progress ticket"], repo)

        worktree = tmp_path / "t-3394"
        _run_git(["worktree", "add", "-q", "-b", "t-3394", str(worktree)], repo)
        # The ONLY commit in this worktree so far is the start-transition
        # commit `frob ticket start`/`work` writes unconditionally --
        # T-3394's own measured state (7 minutes old, no scope-touching
        # commit yet). Deliberately does NOT touch src/a.py.
        _run_git(
            [
                "commit",
                "-q",
                "--allow-empty",
                "-m",
                "chore(tickets): record T-3394 start transition",
            ],
            worktree,
        )

        monkeypatch.setattr(fleet_status, "REPO", repo)
        monkeypatch.setattr(fleet_status, "TICKETS_DIR", repo / "tickets")
        monkeypatch.setattr(fleet_status, "WORKTREES", tmp_path)
        # No lease file -- the common real-world case this repo's own
        # LEASES section shows (most in-progress tickets right now have
        # no lease file at all), and the shape that forces the fallback
        # path this test targets.
        monkeypatch.setattr(fleet_status, "LEASES", tmp_path / "no-leases")

        entries = fleet_status.in_progress_ticket_scope_leases()
        assert entries == [
            {
                "ticket_id": "T-3394",
                "scope": ["src/a.py"],
                "worktree": "t-3394",
                "leaked": False,
            }
        ], (
            "a worktree that has structurally STARTED this ticket (its "
            "own start-transition commit) is unambiguous, genuinely-live "
            "evidence and must not be reported as leaked merely because "
            "no SCOPE-touching commit has landed yet"
        )
