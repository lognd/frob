"""T-4572: the ledger-only CAS-retry fast path -- `frob.tickets._land_
compose.commits_touch_only_ledger_paths`/`rebase_composed_commit_onto` and
their wiring into `frob.tickets._land_squash._fold_publish_and_resync`.

Repro this closes: a land composes for 10+ minutes, a sibling agent's
`chore(tickets): mirror ...` ledger-only commit advances the main branch
in the meantime, the CAS publish loses the race, and the land refuses with
DirtyMain even though nothing but the ledger moved -- and the refusal used
to leave `root` dirty. These tests prove: (1) a pure ledger/CHANGELOG
advance is classified ledger-only and a code-touching one is not, (2) the
rebase primitive re-parents the land's own diff without losing the
sibling's ledger content, and (3) `_fold_publish_and_resync` takes the
fast path (no extra gate work) on a ledger-only advance, falls back to the
ordinary `DirtyMain` refusal on a code-touching one, and leaves `root`
clean either way.
"""

from __future__ import annotations

import subprocess
from datetime import date
from pathlib import Path

import pytest
from typani.result import Err, Ok

from frob.tickets._land_compose import (
    LandComposeError,
    commits_touch_only_ledger_paths,
    rebase_composed_commit_onto,
)
from frob.tickets._land_squash import (
    _attempt_ledger_only_rebase,
    _fold_publish_and_resync,
)
from frob.tickets._models import LandError, Origin, Ticket, TicketKind, TicketState


def _run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess:
    """Run a git command in `cwd`, asserting success -- test-only helper."""
    return subprocess.run(
        argv, cwd=str(cwd), check=True, capture_output=True, text=True
    )


@pytest.fixture
def scratch_repo(tmp_path: Path) -> Path:
    """A minimal git repo on `main` with a ticket ledger and one code file
    committed -- the base fixture every test in this module builds a
    land's compose-then-CAS-miss scenario against. Gitignores `.frob/`
    (mirrors `tests/unit/test_land_compose.py::scratch_repo`'s own
    established T-3163 pattern) since `_fold_publish_and_resync`'s own
    callees take `root`'s `ledger_lock`."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _run(["git", "init", "-q", "-b", "main"], repo)
    _run(["git", "config", "user.email", "test@example.com"], repo)
    _run(["git", "config", "user.name", "Test"], repo)
    (repo / ".gitignore").write_text(".frob/\n")
    _run(["git", "add", ".gitignore"], repo)
    _run(["git", "commit", "-q", "-m", "gitignore .frob/"], repo)
    (repo / "tickets.md").write_text("# tickets\n")
    (repo / "code.py").write_text("x = 1\n")
    _run(["git", "add", "tickets.md", "code.py"], repo)
    _run(["git", "commit", "-q", "-m", "base"], repo)
    return repo


def _commit_file(repo: Path, path: str, content: str, message: str) -> str:
    """Write `content` to `path` in `repo` (creating parent directories as
    needed, for the v2 `tickets/T-####/ticket.md` ledger layout), commit
    it on the current branch, and return the new commit's sha -- test-only
    helper shared by every "sibling advance" fixture below."""
    target = repo / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)
    _run(["git", "add", path], repo)
    _run(["git", "commit", "-q", "-m", message], repo)
    return _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()


class TestLedgerOnlyAdvance:
    """`commits_touch_only_ledger_paths` classifies the commits between two
    tips as ledger-only (safe to rebase onto) or not (must fall back)."""

    # frob:tests src/frob/tickets/_land_compose.py::commits_touch_only_ledger_paths
    def test_pure_ledger_advance_is_ledger_only(self, scratch_repo: Path) -> None:
        """Given two sibling commits touching only tickets/T-0001/ticket.md
        and CHANGELOG.md, when classified, then it reports ledger_only=True
        (acceptance [0])."""
        old_tip = _run(["git", "rev-parse", "HEAD"], scratch_repo).stdout.strip()
        _commit_file(
            scratch_repo,
            "tickets/T-0001/ticket.md",
            "id: T-0001\n",
            "chore(tickets): mirror",
        )
        new_tip = _commit_file(
            scratch_repo, "CHANGELOG.md", "## Unreleased\n", "chore(tickets): mirror"
        )

        result = commits_touch_only_ledger_paths(scratch_repo, old_tip, new_tip)

        assert result.is_ok
        assert result.danger_ok is True

    # frob:tests src/frob/tickets/_land_compose.py::commits_touch_only_ledger_paths
    def test_a_single_code_touching_commit_is_not_ledger_only(
        self, scratch_repo: Path
    ) -> None:
        """Given a ledger commit followed by one that also touches a code
        file, when classified, then it reports ledger_only=False --
        mixing in even one non-ledger commit must fall back to the full
        recompose (acceptance [1])."""
        old_tip = _run(["git", "rev-parse", "HEAD"], scratch_repo).stdout.strip()
        _commit_file(
            scratch_repo,
            "tickets/T-0001/ticket.md",
            "id: T-0001\n",
            "chore(tickets): mirror",
        )
        new_tip = _commit_file(scratch_repo, "code.py", "x = 2\n", "fix: bump x")

        result = commits_touch_only_ledger_paths(scratch_repo, old_tip, new_tip)

        assert result.is_ok
        assert result.danger_ok is False


class TestRebaseComposedCommitOnto:
    """`rebase_composed_commit_onto` re-parents a composed commit's OWN
    diff onto a fresh base without losing either side's content."""

    # frob:tests src/frob/tickets/_land_compose.py::rebase_composed_commit_onto
    def test_rebased_commit_carries_the_same_content_change(
        self, scratch_repo: Path
    ) -> None:
        """Given a composed commit built from `pre_land_tip`, when a
        sibling ledger-only commit has since advanced main and the
        composed commit is rebased onto it, then the rebased commit's
        tree contains BOTH the land's own change and the sibling's
        ledger advance (acceptance [0])."""
        pre_land_tip = _run(["git", "rev-parse", "HEAD"], scratch_repo).stdout.strip()

        _run(["git", "checkout", "-q", "-b", "landing"], scratch_repo)
        (scratch_repo / "code.py").write_text("x = 42\n")
        _run(["git", "add", "code.py"], scratch_repo)
        _run(["git", "commit", "-q", "-m", "land: T-9999"], scratch_repo)
        composed = _run(["git", "rev-parse", "landing"], scratch_repo).stdout.strip()
        _run(["git", "checkout", "-q", "main"], scratch_repo)

        new_base = _commit_file(
            scratch_repo,
            "tickets/T-0001/ticket.md",
            "id: T-0001\n",
            "chore(tickets): mirror",
        )

        rebased = rebase_composed_commit_onto(
            scratch_repo, pre_land_tip, composed, new_base
        )

        assert rebased.is_ok
        show = _run(
            ["git", "show", f"{rebased.danger_ok}:code.py"], scratch_repo
        ).stdout
        assert show == "x = 42\n"
        show_ledger = _run(
            ["git", "show", f"{rebased.danger_ok}:tickets/T-0001/ticket.md"],
            scratch_repo,
        ).stdout
        assert show_ledger == "id: T-0001\n"
        parents = _run(
            ["git", "rev-parse", f"{rebased.danger_ok}^"], scratch_repo
        ).stdout.strip()
        assert parents == new_base

    # frob:tests src/frob/tickets/_land_compose.py::rebase_composed_commit_onto
    def test_rebase_failure_returns_err(self, scratch_repo: Path) -> None:
        """Given a composed commit whose own diff conflicts with the new
        base (the same path changed both ways), when rebased, then it
        returns `Err` rather than silently dropping either side
        (acceptance [1])."""
        pre_land_tip = _run(["git", "rev-parse", "HEAD"], scratch_repo).stdout.strip()

        _run(["git", "checkout", "-q", "-b", "landing"], scratch_repo)
        (scratch_repo / "code.py").write_text("x = 42\n")
        _run(["git", "add", "code.py"], scratch_repo)
        _run(["git", "commit", "-q", "-m", "land: T-9999"], scratch_repo)
        composed = _run(["git", "rev-parse", "landing"], scratch_repo).stdout.strip()
        _run(["git", "checkout", "-q", "main"], scratch_repo)

        new_base = _commit_file(
            scratch_repo, "code.py", "x = 99\n", "fix: conflicting bump"
        )

        rebased = rebase_composed_commit_onto(
            scratch_repo, pre_land_tip, composed, new_base
        )

        assert rebased.is_err


def _ticket() -> Ticket:
    """A minimal `Ticket` -- only `_commit_message` reads its fields, and
    only for the commit message text, so the exact values are arbitrary
    but must satisfy the model's own validation."""
    return Ticket(
        id="T-9999",
        title="test",
        state=TicketState.IN_PROGRESS,
        kind=TicketKind.BUG,
        origin=Origin.HUMAN,
        created=date(2026, 9, 19),
    )


class TestFoldPublishAndResync:
    """`_fold_publish_and_resync`'s T-4572 CAS-retry fast path: a ledger-
    only sibling advance is rebased-and-retried in place; a code-touching
    one falls back to the ordinary DirtyMain refusal; either way `root`
    ends up clean."""

    def _stage_with_composed_change(self, scratch_repo: Path) -> tuple[Path, str]:
        """Build a disposable `stage` worktree, detached at `root`'s
        current tip, holding one staged content change ready to fold --
        shared setup for every `_fold_publish_and_resync` test below."""
        pre_land_tip = _run(["git", "rev-parse", "HEAD"], scratch_repo).stdout.strip()
        stage = scratch_repo.parent / "stage"
        _run(
            [
                "git",
                "worktree",
                "add",
                "--detach",
                "-q",
                str(stage),
                pre_land_tip,
            ],
            scratch_repo,
        )
        (stage / "code.py").write_text("x = 42\n")
        _run(["git", "add", "code.py"], stage)
        return stage, pre_land_tip

    # frob:tests src/frob/tickets/_land_squash.py::_fold_publish_and_resync
    def test_ledger_only_cas_miss_rebases_and_retries_without_regates(
        self, scratch_repo: Path
    ) -> None:
        """Given a lost CAS caused solely by a sibling ledger-only commit,
        when `_fold_publish_and_resync` runs, then it rebases the composed
        commit onto the new tip and publishes successfully -- the land
        does not refuse (acceptance [0])."""
        stage, pre_land_tip = self._stage_with_composed_change(scratch_repo)
        _commit_file(
            scratch_repo,
            "tickets/T-0001/ticket.md",
            "id: T-0001\n",
            "chore(tickets): mirror",
        )

        result = _fold_publish_and_resync(
            scratch_repo,
            stage,
            _ticket(),
            "T-9999",
            pre_land_tip=pre_land_tip,
            main_branch_name="main",
        )

        assert result.is_ok
        landed_code = _run(["git", "show", "main:code.py"], scratch_repo).stdout
        assert landed_code == "x = 42\n"
        landed_ledger = _run(
            ["git", "show", "main:tickets/T-0001/ticket.md"], scratch_repo
        ).stdout
        assert landed_ledger == "id: T-0001\n"

    # frob:tests src/frob/tickets/_land_squash.py::_fold_publish_and_resync
    def test_code_touching_cas_miss_falls_back_to_full_recompose(
        self, scratch_repo: Path
    ) -> None:
        """Given a lost CAS caused by a sibling commit that touches a code
        path, when `_fold_publish_and_resync` runs, then it refuses with
        `DirtyMain` rather than silently discarding the sibling's commit
        via a rebase (acceptance [1])."""
        stage, pre_land_tip = self._stage_with_composed_change(scratch_repo)
        _commit_file(scratch_repo, "code.py", "x = 7\n", "fix: sibling land")

        result = _fold_publish_and_resync(
            scratch_repo,
            stage,
            _ticket(),
            "T-9999",
            pre_land_tip=pre_land_tip,
            main_branch_name="main",
        )

        assert result.is_err
        assert result.danger_err is LandError.DirtyMain
        _run(["git", "worktree", "remove", "--force", str(stage)], scratch_repo)

    # frob:tests src/frob/tickets/_land_squash.py::_fold_publish_and_resync
    def test_refused_land_leaves_root_clean(self, scratch_repo: Path) -> None:
        """Given a refused land (the code-touching CAS-miss case above),
        when the refusal returns, then `git status --porcelain` in `root`
        is empty -- the T-4572 DirtyMain-residue bug this ticket also
        closes (acceptance [1] of T-4572's ticket body)."""
        stage, pre_land_tip = self._stage_with_composed_change(scratch_repo)
        _commit_file(scratch_repo, "code.py", "x = 7\n", "fix: sibling land")

        result = _fold_publish_and_resync(
            scratch_repo,
            stage,
            _ticket(),
            "T-9999",
            pre_land_tip=pre_land_tip,
            main_branch_name="main",
        )

        assert result.is_err
        porcelain = _run(["git", "status", "--porcelain"], scratch_repo).stdout
        assert porcelain == ""
        _run(["git", "worktree", "remove", "--force", str(stage)], scratch_repo)

    # frob:ticket T-5491
    # frob:tests src/frob/tickets/_land_squash.py::_publish_with_ledger_only_retry kind="unit"  # noqa: E501
    def test_apply_conflict_against_one_ledger_only_sibling_still_lands_after_a_second(
        self, scratch_repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """BUG002 repro (T-5491): the FIRST CAS-miss retry
        attempt's rebase fails to apply cleanly against a genuinely
        ledger-only sibling (a text conflict, not a code touch), and the
        SECOND attempt -- against a later sibling tip -- applies cleanly.
        At `dev` (before this fix), `_attempt_ledger_only_rebase`'s
        boolean/`None` return could not distinguish "apply conflict,
        worth retrying" from "not ledger-only, give up", so
        `_publish_with_ledger_only_retry` refused with `DirtyMain` after
        exactly the FIRST failed rebase, never reaching the second,
        applicable tip. At the fix, the apply conflict retries and the
        publish succeeds on the second attempt. Mocked at the
        `publish_ref_cas`/`rebase_composed_commit_onto`/`_rev_parse`
        boundary (not real git) so this test exercises the SAME
        orchestration code path `_fold_publish_and_resync` drives,
        deterministically, without depending on git's own conflict
        heuristics to reproduce a specific two-attempt sequence."""
        import frob.tickets._land_squash as land_squash

        old_tip = _run(["git", "rev-parse", "HEAD"], scratch_repo).stdout.strip()
        tip_after_sibling_one = "sibling1" * 5
        tip_after_sibling_two = "sibling2" * 5
        candidate_sha = "composed" * 5
        rebased_sha = "rebased0" * 5

        rev_parse_calls = iter([tip_after_sibling_one, tip_after_sibling_two])
        monkeypatch.setattr(
            land_squash,
            "_rev_parse",
            lambda root, ref: Ok(next(rev_parse_calls)),
        )
        # T-5491: bypass the drift-proportional bound's own
        # real `_rev_parse`/`rev-list` call entirely -- this test only
        # cares about the two-attempt apply-conflict-then-advance
        # sequence below, not the bound's own git-shelled-out logic
        # (covered separately).
        monkeypatch.setattr(
            land_squash,
            "_ledger_only_cas_retry_limit",
            lambda root, pre_land_tip, ref: land_squash._LEDGER_ONLY_CAS_RETRY_LIMIT,
        )
        monkeypatch.setattr(
            land_squash,
            "commits_touch_only_ledger_paths",
            lambda root, base, current: Ok(True),
        )
        rebase_calls = iter([Err(LandComposeError.ComposeFailed), Ok(rebased_sha)])
        monkeypatch.setattr(
            land_squash,
            "rebase_composed_commit_onto",
            lambda root, base, sha, new_base: next(rebase_calls),
        )
        publish_calls = iter(
            [
                Err(LandComposeError.ComposeFailed),
                Err(LandComposeError.ComposeFailed),
                Ok(None),
            ]
        )
        monkeypatch.setattr(
            land_squash,
            "publish_ref_cas",
            lambda root, ref, base, sha: next(publish_calls),
        )
        monkeypatch.setattr(land_squash.time, "sleep", lambda seconds: None)

        result = land_squash._publish_with_ledger_only_retry(
            scratch_repo,
            scratch_repo,
            "refs/heads/main",
            old_tip,
            candidate_sha,
            "T-9999",
            "main",
        )

        assert result.is_ok
        assert result.danger_ok == (tip_after_sibling_two, rebased_sha)

    # frob:ticket T-5491
    # frob:tests src/frob/tickets/_land_squash.py::_publish_with_ledger_only_retry kind="unit"  # noqa: E501
    def test_dev_advances_by_ledger_only_commit_between_compose_and_publish_lands(
        self, scratch_repo: Path
    ) -> None:
        """Positive control (T-5491 acceptance): dev advances by
        a `tickets/**`-only commit strictly BETWEEN this land's own
        compose and its publish attempt -- the exact T-5326/T-5324/
        T-5474/T-5475 shape (a `chore(tickets): points ...`/`mirror scope
        ...` sibling commit racing a land's own compose). The land must
        still publish on the first `_fold_publish_and_resync` call, never
        surfacing `DirtyMain` to the caller."""
        stage, pre_land_tip = self._stage_with_composed_change(scratch_repo)
        # Simulates a sibling agent's `frob ticket points`/`scope --add`
        # mirror commit landing on dev while THIS land's own compose was
        # still running in `stage` -- by the time `_fold_publish_and_
        # resync` runs, `scratch_repo` (dev) has already moved.
        _commit_file(
            scratch_repo,
            "tickets/T-5470/ticket.md",
            "id: T-5470\npoints: 5\n",
            "chore(tickets): points T-5470",
        )

        result = _fold_publish_and_resync(
            scratch_repo,
            stage,
            _ticket(),
            "T-9999",
            pre_land_tip=pre_land_tip,
            main_branch_name="main",
        )

        assert result.is_ok
        landed_code = _run(["git", "show", "main:code.py"], scratch_repo).stdout
        assert landed_code == "x = 42\n"
        landed_ledger = _run(
            ["git", "show", "main:tickets/T-5470/ticket.md"], scratch_repo
        ).stdout
        assert landed_ledger == "id: T-5470\npoints: 5\n"


class TestAttemptLedgerOnlyRebase:
    """`_attempt_ledger_only_rebase`'s three-way outcome (T-5491)
    -- `"advanced"`/`"apply_failed"`/`"not_ledger_only"` -- and, in
    particular, that a text-level apply conflict against a GENUINELY
    ledger-only sibling is reported as retryable (`"apply_failed"`), not
    collapsed into the same give-up outcome a real code-touching advance
    gets (`"not_ledger_only"`). This is the actual T-5326 defect: the
    prior boolean/`None` return could not tell these apart, so
    `_publish_with_ledger_only_retry` refused on the FIRST apply conflict
    even though its own log line claimed the attempt bound was exhausted."""

    # frob:tests src/frob/tickets/_land_squash.py::_attempt_ledger_only_rebase kind="unit"  # noqa: E501
    # frob:ticket T-5491
    def test_ledger_only_apply_conflict_is_retryable_not_a_hard_refusal(
        self, scratch_repo: Path
    ) -> None:
        """Given a composed commit whose OWN diff also touches
        `tickets/T-0001/ticket.md`, and a sibling commit that is STILL
        ledger-only but edits that same ticket file differently (a text
        conflict, not a code touch), when `_attempt_ledger_only_rebase`
        runs, then it reports `"apply_failed"` (retryable) rather than
        `"not_ledger_only"` (give up) -- `commits_touch_only_ledger_
        paths` alone would already say `True` here; only the apply
        itself fails."""
        pre_land_tip = _run(["git", "rev-parse", "HEAD"], scratch_repo).stdout.strip()

        _run(["git", "checkout", "-q", "-b", "landing"], scratch_repo)
        (scratch_repo / "code.py").write_text("x = 42\n")
        (scratch_repo / "tickets" / "T-0001").mkdir(parents=True)
        (scratch_repo / "tickets" / "T-0001" / "ticket.md").write_text(
            "id: T-0001\nfrom: land\n"
        )
        _run(["git", "add", "code.py", "tickets/T-0001/ticket.md"], scratch_repo)
        _run(["git", "commit", "-q", "-m", "land: T-9999"], scratch_repo)
        composed = _run(["git", "rev-parse", "landing"], scratch_repo).stdout.strip()
        _run(["git", "checkout", "-q", "main"], scratch_repo)

        new_base = _commit_file(
            scratch_repo,
            "tickets/T-0001/ticket.md",
            "id: T-0001\nfrom: sibling\n",
            "chore(tickets): mirror",
        )

        outcome, advanced = _attempt_ledger_only_rebase(
            scratch_repo, "main", pre_land_tip, composed, "T-9999", attempt=0
        )

        assert outcome == "apply_failed"
        assert advanced is None
        # `main` was not force-moved or corrupted by the failed attempt.
        current_tip = _run(["git", "rev-parse", "main"], scratch_repo).stdout.strip()
        assert current_tip == new_base

    # frob:ticket T-5522
    # frob:tests tests/unit/test_land_cas_ledger_retry.py::TestAttemptLedgerOnlyRebase.test_context_only_apply_conflict_recovers_via_full_recompose  # noqa: E501
    # frob:tests src/frob/tickets/_land_squash.py::_attempt_ledger_only_rebase kind="unit"  # noqa: E501
    def test_context_only_apply_conflict_recovers_via_full_recompose(
        self, scratch_repo: Path
    ) -> None:
        """Positive control (T-5522): the composed commit and the
        sibling ledger-only commit touch the SAME `tickets/**` file, but
        at DIFFERENT lines (a genuinely non-conflicting 3-way merge --
        `status` vs `notes`) -- a textual `git apply` still fails here
        because its context lines (the WHOLE 3-line file, no common-
        ancestor awareness) no longer match after the sibling's edit,
        exactly the measured T-5477 shape (`ComposeFailed: building the
        out-of-tree commit ...`). `_attempt_ledger_only_rebase` must
        recover via `_recompose_via_merge`'s real 3-way merge (which DOES
        know the common ancestor and sees the two edits do not overlap)
        and report `"advanced"`, not exhaust retries and refuse."""
        _commit_file(
            scratch_repo,
            "tickets/T-5522/ticket.md",
            "id: T-5522\nstatus: open\nowner: a\nkind: bug\nnotes: none\n",
            "chore(tickets): seed T-5522",
        )
        pre_land_tip = _run(["git", "rev-parse", "HEAD"], scratch_repo).stdout.strip()

        _run(["git", "checkout", "-q", "-b", "landing"], scratch_repo)
        (scratch_repo / "code.py").write_text("x = 42\n")
        (scratch_repo / "tickets" / "T-5522" / "ticket.md").write_text(
            "id: T-5522\nstatus: closed\nowner: a\nkind: bug\nnotes: none\n"
        )
        _run(["git", "add", "code.py", "tickets/T-5522/ticket.md"], scratch_repo)
        _run(["git", "commit", "-q", "-m", "land: T-5522"], scratch_repo)
        composed = _run(["git", "rev-parse", "landing"], scratch_repo).stdout.strip()
        _run(["git", "checkout", "-q", "main"], scratch_repo)

        new_base = _commit_file(
            scratch_repo,
            "tickets/T-5522/ticket.md",
            "id: T-5522\nstatus: open\nowner: a\nkind: bug\nnotes: mirrored\n",
            "chore(tickets): mirror scope T-5522 from worktree",
        )

        outcome, advanced = _attempt_ledger_only_rebase(
            scratch_repo, "main", pre_land_tip, composed, "T-5522", attempt=0
        )

        assert outcome == "advanced", outcome
        assert advanced is not None
        new_base_out, recomposed_sha = advanced
        assert new_base_out == new_base
        show_ledger = _run(
            ["git", "show", f"{recomposed_sha}:tickets/T-5522/ticket.md"],
            scratch_repo,
        ).stdout
        assert (
            show_ledger
            == "id: T-5522\nstatus: closed\nowner: a\nkind: bug\nnotes: mirrored\n"
        )
        show_code = _run(
            ["git", "show", f"{recomposed_sha}:code.py"], scratch_repo
        ).stdout
        assert show_code == "x = 42\n"
