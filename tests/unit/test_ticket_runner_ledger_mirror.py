"""T-2563: a ledger-only ticket edit made from a worktree must be visible
on the PRIMARY checkout immediately, not only if some later land happens
to carry it.

The controls here are written to fail against the pre-T-2563 behaviour:
before the mirror existed, every `_visible_on_primary` assertion below
read `False` while the verb itself reported success -- the silent-zero
shape this ticket closes.
"""
# frob:ticket T-2563

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from frob.app.ticket_runner._ledger_mirror import (
    LEDGER_VERB_STRATEGY,
    MIRRORED_LEDGER_VERBS,
    OWN_TRANSACTION_VERBS,
    LedgerWriteStrategy,
    ledger_write_strategy_for,
    mirror_ledger_change_to_primary,
    mirror_promote_to_primary,
)


def _git(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=False
    )


def _ticket_text(ticket_id: str) -> str:
    return f"---\nid: {ticket_id}\nstate: queued\n---\nbody\n"


# frob:ticket T-2563
def _setup(tmp_path: Path, ticket_id: str = "T-0001") -> tuple[Path, Path]:
    """A primary checkout carrying `ticket_id`, plus a linked worktree.

    Returns `(primary, worktree)`.
    """
    primary = tmp_path / "primary"
    primary.mkdir()
    _git("init", "-q", "-b", "main", cwd=primary)
    _git("config", "user.email", "t@example.com", cwd=primary)
    _git("config", "user.name", "T", cwd=primary)
    # Every real frob repo gitignores .frob/ (the lock/cache dir); without
    # it the mirror's own ledger_lock file reads as untracked noise and the
    # cleanliness control below would fail on a fixture artefact rather
    # than on anything the mirror did.
    (primary / ".gitignore").write_text(".frob/\n")
    ticket_dir = primary / "tickets" / ticket_id
    ticket_dir.mkdir(parents=True)
    (ticket_dir / "ticket.md").write_text(_ticket_text(ticket_id))
    _git("add", "-A", cwd=primary)
    _git("commit", "-q", "-m", "init", cwd=primary)

    worktree = tmp_path / "wt"
    added = _git(
        "worktree", "add", "-q", "-b", "t-branch", str(worktree), "main", cwd=primary
    )
    assert added.returncode == 0, added.stdout + added.stderr
    return primary, worktree


def _visible_on_primary(primary: Path, needle: str, ticket_id: str = "T-0001") -> bool:
    """Does the PRIMARY checkout's committed ledger carry `needle`?

    Reads the committed tree (`git show HEAD:...`), never the working
    tree -- the whole defect was an edit that existed somewhere other
    than where the fleet looks, so an assertion that reads a loose file
    would not distinguish the fixed case from the broken one.
    """
    shown = _git("show", f"HEAD:tickets/{ticket_id}/ticket.md", cwd=primary)
    return shown.returncode == 0 and needle in shown.stdout


class TestLedgerMirrorReachesMain:
    # frob:ticket T-2563
    def test_scope_edit_from_worktree_is_visible_on_primary(
        self, tmp_path: Path
    ) -> None:
        """The headline control: the edit must be readable on the primary
        checkout the moment the verb returns."""
        primary, worktree = _setup(tmp_path)
        path = worktree / "tickets" / "T-0001" / "ticket.md"
        path.write_text(path.read_text() + "scope:\n- src/mine.py\n")
        _git("commit", "-q", "-am", "scope edit", cwd=worktree)

        mirror_ledger_change_to_primary(worktree, "T-0001", "scope")

        assert _visible_on_primary(primary, "src/mine.py")

    # frob:ticket T-2563
    def test_block_edit_from_worktree_is_visible_on_primary(
        self, tmp_path: Path
    ) -> None:
        """`block` is the verb whose invisibility left T-2374 looking
        like it had simply stopped for no reason."""
        primary, worktree = _setup(tmp_path)
        path = worktree / "tickets" / "T-0001" / "ticket.md"
        path.write_text(path.read_text() + "blocked_by:\n- T-9999\n")
        _git("commit", "-q", "-am", "block edit", cwd=worktree)

        mirror_ledger_change_to_primary(worktree, "T-0001", "block")

        assert _visible_on_primary(primary, "T-9999")

    # frob:ticket T-2616
    def test_milestone_edit_from_worktree_is_visible_on_primary(
        self, tmp_path: Path
    ) -> None:
        """T-2616: `milestone` writes through `_set_ticket_field`, the
        same primitive `priority`/`kind`/`tier` use, but was left
        classified `GENERIC_COMMIT_UNMIRRORED` when T-2603 unified the
        two legacy sets -- a worktree agent's `frob ticket milestone`
        committed locally but was never mirrored to the primary
        checkout, invisible to the fleet until the ticket landed."""
        assert "milestone" in MIRRORED_LEDGER_VERBS
        primary, worktree = _setup(tmp_path)
        path = worktree / "tickets" / "T-0001" / "ticket.md"
        path.write_text(path.read_text() + "milestone: 0.1.0\n")
        _git("commit", "-q", "-am", "milestone edit", cwd=worktree)

        mirror_ledger_change_to_primary(worktree, "T-0001", "milestone")

        assert _visible_on_primary(primary, "milestone: 0.1.0")

    # frob:ticket T-2840
    def test_requeue_edit_from_worktree_is_visible_on_primary(
        self, tmp_path: Path
    ) -> None:
        """T-2840: a requeue's `IN_PROGRESS -> QUEUED` transition IS the
        lease release (see `_requeue`'s own docstring) -- unlike
        close/drop/fail, no future `land` ever carries a requeued
        ticket's state to main, so unlike those verbs `requeue` must be
        mirrored immediately or the lease it claims to release stays
        held on main forever. This is the measured incident this ticket
        closes: the command reported success while main kept reading
        `in-progress`.

        Primary starts at `in-progress` (simulating the ticket having
        been started, unmirrored, exactly like `start` still is today)
        and a unique marker distinguishes "mirror actually ran" from
        "the field already happened to read right" -- without it, a
        no-op mirror and a working one would be indistinguishable since
        both begin and end reading `queued`-shaped text somewhere."""
        assert "requeue" in MIRRORED_LEDGER_VERBS
        primary, worktree = _setup(tmp_path)
        for root in (primary, worktree):
            path = root / "tickets" / "T-0001" / "ticket.md"
            path.write_text(path.read_text().replace("queued", "in-progress"))
        _git("commit", "-q", "-am", "start", cwd=primary)
        _git("commit", "-q", "-am", "start", cwd=worktree)

        path = worktree / "tickets" / "T-0001" / "ticket.md"
        path.write_text(
            path.read_text().replace("in-progress", "queued") + "requeue-marker-t2840\n"
        )
        _git("commit", "-q", "-am", "requeue edit", cwd=worktree)

        mirror_ledger_change_to_primary(worktree, "T-0001", "requeue")

        assert _visible_on_primary(primary, "requeue-marker-t2840")
        assert _visible_on_primary(primary, "state: queued")
        assert not _visible_on_primary(primary, "in-progress")

    # frob:ticket T-3162
    def test_reopen_edit_from_worktree_is_visible_on_primary(
        self, tmp_path: Path
    ) -> None:
        """T-3162: `frob ticket reopen`'s DONE -> QUEUED write is real and
        committed in the worktree, but with no `LEDGER_VERB_STRATEGY`
        entry `ledger_write_strategy_for("reopen")` raised `KeyError`
        instead of mirroring -- crashing the command outright rather
        than the requeue-shaped silent-invisibility bug T-2840 fixed.
        Same fixture shape as requeue's own test just above: a unique
        marker distinguishes "mirror actually ran" from "the field
        already happened to read right"."""
        assert "reopen" in MIRRORED_LEDGER_VERBS
        primary, worktree = _setup(tmp_path)
        for root in (primary, worktree):
            path = root / "tickets" / "T-0001" / "ticket.md"
            path.write_text(path.read_text().replace("queued", "done"))
        _git("commit", "-q", "-am", "close", cwd=primary)
        _git("commit", "-q", "-am", "close", cwd=worktree)

        path = worktree / "tickets" / "T-0001" / "ticket.md"
        path.write_text(
            path.read_text().replace("done", "queued") + "reopen-marker-t3162\n"
        )
        _git("commit", "-q", "-am", "reopen edit", cwd=worktree)

        mirror_ledger_change_to_primary(worktree, "T-0001", "reopen")

        assert _visible_on_primary(primary, "reopen-marker-t3162")
        assert _visible_on_primary(primary, "state: queued")
        assert not _visible_on_primary(primary, "state: done")

    # frob:ticket T-2563
    def test_attachment_file_reaches_primary(self, tmp_path: Path) -> None:
        """`attach` writes a NEW file inside the ticket directory, so the
        mirror has to carry whole directories, not just ticket.md."""
        primary, worktree = _setup(tmp_path)
        attachments = worktree / "tickets" / "T-0001" / "attachments"
        attachments.mkdir(parents=True)
        (attachments / "01-analysis.md").write_text("findings\n")
        _git("add", "-A", cwd=worktree)
        _git("commit", "-q", "-m", "attach", cwd=worktree)

        mirror_ledger_change_to_primary(worktree, "T-0001", "attach")

        shown = _git(
            "show", "HEAD:tickets/T-0001/attachments/01-analysis.md", cwd=primary
        )
        assert shown.returncode == 0, shown.stdout + shown.stderr
        assert "findings" in shown.stdout


class TestLedgerMirrorCarriesNothingElse:
    # frob:ticket T-2563
    def test_worktree_source_changes_do_not_leak_to_primary(
        self, tmp_path: Path
    ) -> None:
        """The must-NOT-fire control. An agent's in-progress source edits
        are the reason ledger edits were stranded in the first place;
        fixing that must not start publishing unlanded code as a side
        effect."""
        primary, worktree = _setup(tmp_path)
        (worktree / "src_secret.py").write_text("UNLANDED = True\n")
        _git("add", "-A", cwd=worktree)
        _git("commit", "-q", "-m", "unlanded source", cwd=worktree)
        path = worktree / "tickets" / "T-0001" / "ticket.md"
        path.write_text(path.read_text() + "priority: high\n")
        _git("commit", "-q", "-am", "priority", cwd=worktree)

        mirror_ledger_change_to_primary(worktree, "T-0001", "priority")

        assert _visible_on_primary(primary, "priority: high")
        assert not (primary / "src_secret.py").exists()
        listed = _git("show", "--stat", "--name-only", "HEAD", cwd=primary)
        assert "src_secret.py" not in listed.stdout

    # frob:ticket T-2570
    def test_mirror_does_not_clobber_primarys_own_done_report(
        self, tmp_path: Path
    ) -> None:
        """T-2570: `done-report` is `GENERIC_COMMIT_UNMIRRORED` (its OWN
        write never mirrors) and `land` is `OWN_TRANSACTION` (it owns
        `done-report.md` too) -- but `_ledger_pathspecs` returns the whole
        `tickets/T-####` DIRECTORY, so a `scope`/`block`/... mirror's
        `shutil.copytree(..., dirs_exist_ok=True)` silently drags
        `done-report.md` along and overwrites whatever main independently
        wrote there (e.g. a land's `error-findings:` claims), even though
        no mirrored verb ever intended to touch that file. Reproduces the
        real incident: a worktree's stale local draft clobbering main's
        freshly land-written done report the moment an unrelated `scope`
        edit mirrors."""
        primary, worktree = _setup(tmp_path)
        (primary / "tickets" / "T-0001" / "done-report.md").write_text(
            "## Done report\n\nerror-findings: []\n"
        )
        _git("add", "-A", cwd=primary)
        _git("commit", "-q", "-m", "land: write done-report.md", cwd=primary)

        # The worktree still carries its OWN, older/different draft of the
        # same file, uncommitted-on-main -- e.g. left over from before the
        # land above ever happened.
        (worktree / "tickets" / "T-0001" / "done-report.md").write_text(
            "## Done report\n\nstale worktree narrative, no error-findings\n"
        )
        path = worktree / "tickets" / "T-0001" / "ticket.md"
        path.write_text(path.read_text() + "scope:\n- src/mine.py\n")
        _git("add", "-A", cwd=worktree)
        _git("commit", "-q", "-am", "scope edit", cwd=worktree)

        mirror_ledger_change_to_primary(worktree, "T-0001", "scope")

        # The unrelated `scope` mirror must still land.
        assert _visible_on_primary(primary, "src/mine.py")
        # But it must NOT have clobbered main's own done-report.md.
        shown = _git("show", "HEAD:tickets/T-0001/done-report.md", cwd=primary)
        assert shown.returncode == 0, shown.stdout + shown.stderr
        assert "error-findings" in shown.stdout
        assert "stale worktree narrative" not in shown.stdout

    # frob:ticket T-2563
    def test_primary_worktree_is_left_clean(self, tmp_path: Path) -> None:
        """A mirror that dirtied the shared root would DirtyMain-block
        every concurrent land -- the failure this repo pays for most
        often. The write must be committed, not left loose."""
        primary, worktree = _setup(tmp_path)
        path = worktree / "tickets" / "T-0001" / "ticket.md"
        path.write_text(path.read_text() + "kind: bug\n")
        _git("commit", "-q", "-am", "kind", cwd=worktree)

        mirror_ledger_change_to_primary(worktree, "T-0001", "kind")

        status = _git("status", "--porcelain", cwd=primary)
        assert status.stdout.strip() == "", status.stdout


class TestLedgerMirrorScope:
    # frob:ticket T-2563
    @pytest.mark.parametrize("verb", ["start", "close", "done-report", "evidence"])
    def test_state_machine_verbs_are_not_mirrored(
        self, tmp_path: Path, verb: str
    ) -> None:
        """State transitions describe work that is still worktree-local
        and land carries them atomically with the code. Mirroring one
        would advance main's state machine ahead of the work itself."""
        assert verb not in MIRRORED_LEDGER_VERBS
        primary, worktree = _setup(tmp_path)
        path = worktree / "tickets" / "T-0001" / "ticket.md"
        path.write_text(path.read_text().replace("queued", "in-progress"))
        _git("commit", "-q", "-am", "state", cwd=worktree)

        mirror_ledger_change_to_primary(worktree, "T-0001", verb)

        assert not _visible_on_primary(primary, "in-progress")

    # frob:ticket T-2563
    def test_running_in_the_primary_checkout_is_a_no_op(self, tmp_path: Path) -> None:
        """The coordinator's own path must cost nothing: when the verb
        already ran in the primary checkout there is no second root to
        mirror onto, and no commit may be invented."""
        primary, _worktree = _setup(tmp_path)
        before = _git("rev-parse", "HEAD", cwd=primary).stdout.strip()

        mirror_ledger_change_to_primary(primary, "T-0001", "scope")

        assert _git("rev-parse", "HEAD", cwd=primary).stdout.strip() == before
        assert _git("status", "--porcelain", cwd=primary).stdout.strip() == ""

    # frob:ticket T-2840
    def test_requeue_running_in_the_primary_checkout_is_a_no_op(
        self, tmp_path: Path
    ) -> None:
        """Positive control, the other direction: reclassifying `requeue`
        must not change its behaviour for the coordinator's own
        already-on-main path -- `requeue` issued from the primary
        checkout still works exactly as before this ticket."""
        primary, _worktree = _setup(tmp_path)
        before = _git("rev-parse", "HEAD", cwd=primary).stdout.strip()

        mirror_ledger_change_to_primary(primary, "T-0001", "requeue")

        assert _git("rev-parse", "HEAD", cwd=primary).stdout.strip() == before
        assert _git("status", "--porcelain", cwd=primary).stdout.strip() == ""


# frob:ticket T-2603
class TestVerbStrategy:
    """T-2603: one `LEDGER_VERB_STRATEGY` table replaces
    `_LEDGER_TRANSACTIONAL_VERBS` + `MIRRORED_LEDGER_VERBS` + `promote`'s
    special case -- these assert the unification changed NOTHING about
    which verbs land in which bucket, and that the new failure-mode this
    ticket asked for (an unclassified verb fails loudly, not silently)
    actually fires."""

    # frob:ticket T-2603
    def test_all_classified(self) -> None:
        from frob.app.ticket_runner import _ticket_dispatch_table

        table_verbs = frozenset(_ticket_dispatch_table().keys())
        assert table_verbs == frozenset(LEDGER_VERB_STRATEGY)

    # frob:ticket T-2603
    # frob:ticket T-2675
    def test_derived_sets_track_the_live_strategy_table(self) -> None:
        """T-2675: this used to be `test_derived_match`, hardcoding
        T-2603 migration-day's verb membership as two literal frozensets
        (`OWN_TRANSACTION_VERBS == frozenset({"land", "merge-driver", ...})`,
        `MIRRORED_LEDGER_VERBS == frozenset({"accept", "anchor", ...})`) --
        a snapshot valid only at T-2603 landing time, guaranteed to go
        stale on every later verb addition, and it DID: T-2624 added
        `"runs-last-parallel-safe"` to `LEDGER_VERB_STRATEGY` and this
        test silently kept asserting the pre-T-2624 15-verb list, catching
        nothing, until T-2675 found it.

        `OWN_TRANSACTION_VERBS`/`MIRRORED_LEDGER_VERBS` are already
        DERIVED filters over `LEDGER_VERB_STRATEGY` (see those constants'
        own docstrings just above their definitions) -- there was never a
        reason to also hand-maintain their CURRENT contents as a second
        literal in this test; that duplication is exactly the "must be
        hand-updated on every verb addition" failure shape this repo's
        own doctrine calls a bug waiting to recur (NO DUPLICATION: config/
        constants included, not just code). This recomputes the identical
        filter fresh from the LIVE table on every run instead of a frozen
        list, so it can never desync from a real verb addition/removal
        again -- it protects the ALIASING invariant (these two exported
        names really do stay a live filter over `LEDGER_VERB_STRATEGY`,
        not a name that quietly regresses back to a hand-maintained set,
        and any future `LedgerWriteStrategy` member missing from the
        `OWN_TRANSACTION`/`OWN_TRANSACTION_LEDGER_MIRROR` filter tuple
        below would show up as a mismatch here too), not a fixed verb
        count."""
        assert OWN_TRANSACTION_VERBS == frozenset(
            verb
            for verb, strategy in LEDGER_VERB_STRATEGY.items()
            if strategy
            in (
                LedgerWriteStrategy.OWN_TRANSACTION,
                LedgerWriteStrategy.OWN_TRANSACTION_LEDGER_MIRROR,
            )
        )
        assert MIRRORED_LEDGER_VERBS == frozenset(
            verb
            for verb, strategy in LEDGER_VERB_STRATEGY.items()
            if strategy is LedgerWriteStrategy.GENERIC_COMMIT_MIRRORED
        )

    # frob:ticket T-2603
    def test_missing_raises(self) -> None:
        """The whole point: a verb `_ticket_dispatch_table()` knows about
        but `LEDGER_VERB_STRATEGY` does not raises `KeyError` naming the
        gap, rather than silently taking the old code's implicit default
        (generic-commit-but-never-mirror) -- the exact quiet-default shape
        that produced the T-2197 bug this ticket cites."""
        with pytest.raises(KeyError, match="hypothetical-new-verb"):
            ledger_write_strategy_for("hypothetical-new-verb")

    # frob:ticket T-2603
    def test_promote_kind(self) -> None:
        """`promote` is neither a plain `OWN_TRANSACTION` verb nor a
        `GENERIC_COMMIT_MIRRORED` one -- it gets its own enum value,
        proving the unification did not have to flatten a genuinely
        different write shape into one of the other two to succeed."""
        assert (
            ledger_write_strategy_for("promote")
            is LedgerWriteStrategy.OWN_TRANSACTION_LEDGER_MIRROR
        )
        assert "promote" in OWN_TRANSACTION_VERBS
        assert "promote" not in MIRRORED_LEDGER_VERBS


# frob:ticket T-3303
class TestAutoCommitDispatchCoversEveryStrategy:
    """T-3303 (F-024): `_auto_commit_ledger_after_dispatch`'s own
    dispatcher must have an explicit, early-returning branch for EVERY
    `LedgerWriteStrategy` member -- keyed to the ENUM, never to a
    hardcoded verb name -- so no strategy can ever fall through into the
    generic `commit_ticket_ledger_change` path by accident.

    Root cause this guards against: `NOT_TICKET_SCOPED` had no branch of
    its own and instead relied on the generic `cfg.ticket_id is None`
    check below it -- true for most `NOT_TICKET_SCOPED` verbs
    (`list`/`doable`/`board`/...) but FALSE for `show <id>`, which takes
    a ticket id while still being a pure read verb. `frob ticket show`
    fell through and produced a real, silent
    `chore(tickets): show <id>` commit (confirmed live, diax FROBLEMS.md
    F-024).

    Deliberately NOT scoped to `"show"`: these tests drive
    `_auto_commit_ledger_after_dispatch` for a FAKE command whose
    strategy is monkeypatched to each `LedgerWriteStrategy` member in
    turn (never resolved by real verb name), with `cfg.ticket_id` always
    set to a non-`None` value -- the exact condition that let `show`
    slip through. A future `LedgerWriteStrategy` member with no matching
    branch reopens this class's `test_every_strategy_member_is_covered`
    on the day it is added, not only whichever verb happens to expose it
    first."""

    # frob:ticket T-3303
    def test_every_strategy_member_is_covered(self) -> None:
        """No `LedgerWriteStrategy` member may be silently unhandled:
        every member is exercised below, so a new member added to the
        enum without a matching branch in `_auto_commit_ledger_after_
        dispatch` fails THIS assertion, not just an unlucky verb's own
        regression test."""
        from frob.app.ticket_runner._ledger_mirror import LedgerWriteStrategy

        exercised = {
            LedgerWriteStrategy.OWN_TRANSACTION,
            LedgerWriteStrategy.OWN_TRANSACTION_LEDGER_MIRROR,
            LedgerWriteStrategy.GENERIC_COMMIT_MIRRORED,
            LedgerWriteStrategy.GENERIC_COMMIT_UNMIRRORED,
            LedgerWriteStrategy.NOT_TICKET_SCOPED,
        }
        assert exercised == set(LedgerWriteStrategy)

    # frob:ticket T-3303
    @pytest.mark.parametrize(
        "strategy",
        [
            LedgerWriteStrategy.OWN_TRANSACTION,
            LedgerWriteStrategy.OWN_TRANSACTION_LEDGER_MIRROR,
            LedgerWriteStrategy.NOT_TICKET_SCOPED,
        ],
    )
    def test_never_reaches_generic_commit_regardless_of_ticket_id(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        strategy: LedgerWriteStrategy,
    ) -> None:
        """The three strategies that must NEVER reach the generic
        `commit_ticket_ledger_change` path -- with `cfg.ticket_id` set
        to a non-`None` value, the exact shape that let `show` (`NOT_
        TICKET_SCOPED`, but takes an id) slip through when this
        strategy had no branch of its own."""
        from frob.app.config import AppConfig
        from frob.app.ticket_runner import _auto_commit_ledger_after_dispatch
        from frob.app.ticket_runner import _ledger_mirror as _lm

        monkeypatch.setattr(_lm, "ledger_write_strategy_for", lambda _command: strategy)

        committed_calls: list[object] = []
        monkeypatch.setattr(
            "frob.tickets._leases.commit_ticket_ledger_change",
            lambda *a, **k: committed_calls.append((a, k)),
        )
        mirrored_calls: list[object] = []
        monkeypatch.setattr(
            _lm,
            "mirror_ledger_change_to_primary",
            lambda *a, **k: mirrored_calls.append((a, k)),
        )
        promoted_calls: list[object] = []
        monkeypatch.setattr(
            _lm,
            "mirror_promote_to_primary",
            lambda *a, **k: promoted_calls.append((a, k)),
        )

        cfg = AppConfig(ticket_command="fake-verb", ticket_id="T-0001")
        _auto_commit_ledger_after_dispatch(tmp_path, cfg, "fake-verb")

        assert committed_calls == []
        assert mirrored_calls == []
        # OWN_TRANSACTION_LEDGER_MIRROR is the sole exception that DOES
        # call mirror_promote_to_primary -- everything else must call
        # neither mirror function.
        if strategy is _lm.LedgerWriteStrategy.OWN_TRANSACTION_LEDGER_MIRROR:
            assert promoted_calls == [((tmp_path, "T-0001"), {})]
        else:
            assert promoted_calls == []

    # frob:ticket T-3303
    @pytest.mark.parametrize(
        "strategy",
        [
            LedgerWriteStrategy.GENERIC_COMMIT_MIRRORED,
            LedgerWriteStrategy.GENERIC_COMMIT_UNMIRRORED,
        ],
    )
    def test_generic_strategies_still_reach_the_generic_commit(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        strategy: LedgerWriteStrategy,
    ) -> None:
        """The other side of the same invariant: a strategy that IS meant
        to reach the generic commit path still does, so the new
        `NOT_TICKET_SCOPED` branch above did not accidentally swallow
        these two as well."""
        from typani import Ok

        from frob.app.config import AppConfig
        from frob.app.ticket_runner import _auto_commit_ledger_after_dispatch
        from frob.app.ticket_runner import _ledger_mirror as _lm

        monkeypatch.setattr(_lm, "ledger_write_strategy_for", lambda _command: strategy)

        committed_calls: list[object] = []
        monkeypatch.setattr(
            "frob.tickets._leases.commit_ticket_ledger_change",
            lambda *a, **k: (committed_calls.append((a, k)), Ok(None))[1],
        )
        monkeypatch.setattr(
            _lm, "mirror_ledger_change_to_primary", lambda *a, **k: None
        )

        cfg = AppConfig(ticket_command="fake-verb", ticket_id="T-0001")
        _auto_commit_ledger_after_dispatch(tmp_path, cfg, "fake-verb")

        assert len(committed_calls) == 1


# frob:ticket T-2587
def _promote_in_worktree(
    worktree: Path, draft_id: str, final_id: str, *, body: str = "body\n"
) -> None:
    """Simulate `frob ticket promote`'s already-tested outcome in
    `worktree`: `draft_id`'s ledger directory renamed to `final_id`, one
    commit, subject line matching `_commit_promote_rename`'s exact
    deterministic format -- the contract `_last_promote_rename` reads
    back. Real `finalize_draft` also rewrites code references
    (`renumber_one`); this fixture only needs the ledger half, since
    that is all `mirror_promote_to_primary` ever reads or mirrors."""
    draft_dir = worktree / "tickets" / draft_id
    final_dir = worktree / "tickets" / final_id
    draft_dir.mkdir(parents=True, exist_ok=True)
    (draft_dir / "ticket.md").write_text(_ticket_text(draft_id) + body)
    _git("add", "-A", cwd=worktree)
    _git("commit", "-q", "-m", "draft", cwd=worktree)

    _git("mv", f"tickets/{draft_id}", f"tickets/{final_id}", cwd=worktree)
    content = (final_dir / "ticket.md").read_text().replace(draft_id, final_id)
    (final_dir / "ticket.md").write_text(content)
    _git("add", "-A", cwd=worktree)
    _git(
        "commit",
        "-q",
        "-m",
        f"chore(tickets): promote {draft_id} -> {final_id}",
        cwd=worktree,
    )


class TestPromoteMirror:
    # frob:ticket T-2587
    """T-2587: `frob ticket promote`'s own commit (T-2197) is durable in
    the worktree branch, but stays invisible to the fleet until this
    mirror runs -- the gap T-2197 could only warn about."""

    # frob:ticket T-2587
    def test_promote_from_worktree_is_visible_on_primary_without_a_land(
        self, tmp_path: Path
    ) -> None:
        """The headline positive control: a promote from a worktree must
        become visible on the primary checkout without requiring a
        land."""
        primary, worktree = _setup(tmp_path)
        _promote_in_worktree(worktree, "T-draft-abc123", "T-0099")

        mirrored = mirror_promote_to_primary(worktree, "T-draft-abc123")

        assert mirrored is True
        shown = _git("show", "HEAD:tickets/T-0099/ticket.md", cwd=primary)
        assert shown.returncode == 0, shown.stdout + shown.stderr
        assert "T-0099" in shown.stdout
        assert not (primary / "tickets" / "T-draft-abc123").exists()

    # frob:ticket T-2587
    def test_promote_mirror_does_not_leak_source_changes_or_duplicate_the_draft(
        self, tmp_path: Path
    ) -> None:
        """The must-NOT-fire control, doubled: an unrelated dirty source
        edit must not ride along, AND a stale draft directory that
        happened to already exist on primary must be removed rather than
        left sitting alongside the promoted final id (no duplicate ledger
        state)."""
        primary, worktree = _setup(tmp_path)
        stale_draft = primary / "tickets" / "T-draft-abc123"
        stale_draft.mkdir(parents=True)
        (stale_draft / "ticket.md").write_text(_ticket_text("T-draft-abc123"))
        _git("add", "-A", cwd=primary)
        _git("commit", "-q", "-m", "stale draft", cwd=primary)

        (worktree / "src_secret.py").write_text("UNLANDED = True\n")
        _git("add", "-A", cwd=worktree)
        _git("commit", "-q", "-m", "unlanded source", cwd=worktree)
        _promote_in_worktree(worktree, "T-draft-abc123", "T-0099")

        mirrored = mirror_promote_to_primary(worktree, "T-draft-abc123")

        assert mirrored is True
        assert not (primary / "tickets" / "T-draft-abc123").exists()
        shown = _git("show", "HEAD:tickets/T-0099/ticket.md", cwd=primary)
        assert shown.returncode == 0, shown.stdout + shown.stderr
        assert not (primary / "src_secret.py").exists()
        listed = _git("show", "--stat", "--name-only", "HEAD", cwd=primary)
        assert "src_secret.py" not in listed.stdout
        status = _git("status", "--porcelain", cwd=primary)
        assert status.stdout.strip() == "", status.stdout

    # frob:ticket T-2587
    def test_worktree_merging_main_afterward_does_not_conflict_on_the_ticket_file(
        self, tmp_path: Path
    ) -> None:
        """The mirror must narrow to a region the worktree branch does not
        itself keep touching: after the mirror runs, the worktree merging
        `main` (as its own later `frob ticket work` warm-up would) must
        not conflict on the very ticket file the promote rename just
        wrote in both places."""
        primary, worktree = _setup(tmp_path)
        _promote_in_worktree(worktree, "T-draft-abc123", "T-0099")

        assert mirror_promote_to_primary(worktree, "T-draft-abc123") is True

        merged = _git("merge", "--no-edit", "main", cwd=worktree)
        assert merged.returncode == 0, merged.stdout + merged.stderr
        conflicted = _git("diff", "--name-only", "--diff-filter=U", cwd=worktree)
        assert conflicted.stdout.strip() == ""

    # frob:ticket T-2587
    def test_head_not_a_promote_commit_is_a_no_op(self, tmp_path: Path) -> None:
        """A HEAD that is not the exact promote-rename commit must never
        be guessed at -- this must not fire off of some other worktree
        commit."""
        primary, worktree = _setup(tmp_path)
        (worktree / "unrelated.py").write_text("x = 1\n")
        _git("add", "-A", cwd=worktree)
        _git("commit", "-q", "-m", "unrelated", cwd=worktree)
        before = _git("rev-parse", "HEAD", cwd=primary).stdout.strip()

        mirrored = mirror_promote_to_primary(worktree, "T-draft-abc123")

        assert mirrored is False
        assert _git("rev-parse", "HEAD", cwd=primary).stdout.strip() == before

    # frob:ticket T-2587
    def test_running_in_the_primary_checkout_is_a_no_op(self, tmp_path: Path) -> None:
        """Same coordinator-cost-nothing contract as the generic mirror."""
        primary, _worktree = _setup(tmp_path)
        _promote_in_worktree(primary, "T-draft-abc123", "T-0099")
        before = _git("rev-parse", "HEAD", cwd=primary).stdout.strip()

        mirrored = mirror_promote_to_primary(primary, "T-draft-abc123")

        assert mirrored is False
        assert _git("rev-parse", "HEAD", cwd=primary).stdout.strip() == before


@pytest.fixture
def _fail_fixture(tmp_path: Path) -> tuple[Path, Path]:
    """A primary checkout plus linked worktree, both carrying a
    schema-VALID v2 ticket -- `fail`'s own `_load_ticket_for_fail`/
    `record_failure` need a real `Ticket`, unlike `_setup`'s minimal
    `MIRRORED_LEDGER_VERBS`-only frontmatter."""
    from frob.tickets._models import Origin, TicketKind, TicketSpec
    from frob.tickets._new_renumber import _ticket_from_spec
    from frob.tickets._store import _serialize_ticket

    ticket_id = "T-0001"
    primary = tmp_path / "primary"
    primary.mkdir()
    _git("init", "-q", "-b", "main", cwd=primary)
    _git("config", "user.email", "t@example.com", cwd=primary)
    _git("config", "user.name", "T", cwd=primary)
    (primary / ".gitignore").write_text(".frob/\n")
    ticket = _ticket_from_spec(
        ticket_id,
        TicketSpec(
            title="Fail visibility warning fixture",
            kind=TicketKind.BUG,
            origin=Origin.AGENT,
            scope=("src/seed.py",),
        ),
        (),
    )
    ticket_dir = primary / "tickets" / ticket_id
    ticket_dir.mkdir(parents=True)
    (ticket_dir / "ticket.md").write_text(_serialize_ticket(ticket))
    _git("add", "-A", cwd=primary)
    _git("commit", "-q", "-m", "init", cwd=primary)

    worktree = tmp_path / "wt"
    added = _git(
        "worktree", "add", "-q", "-b", "t-branch", str(worktree), "main", cwd=primary
    )
    assert added.returncode == 0, added.stdout + added.stderr
    return primary, worktree


# frob:ticket T-3137
class TestFailNotVisibleOnPrimaryWarning:
    """`frob ticket fail` (unlike `promote`) commits its failure-log entry
    to a worktree's OWN branch only -- `LEDGER_VERB_STRATEGY["fail"]` is
    GENERIC_COMMIT_UNMIRRORED (T-2603), on the assumption a future land
    for THIS ticket always carries it. That assumption breaks once the
    ticket's own series has already landed: nothing ever carries the
    fail-log to main again. `_warn_if_fail_not_visible_on_primary` cannot
    fix the reachability gap itself (mirroring `fail` is real, separate
    work tracked as this ticket's own residue), but it must make the gap
    LOUD rather than let a caller believe a successful-looking `fail`
    reached the fleet."""

    def test_fail_from_worktree_warns_when_not_visible_on_primary(
        self,
        _fail_fixture: tuple[Path, Path],
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        # frob:tests tests/unit/test_ticket_runner_ledger_mirror.py::TestFailNotVisibleOnPrimaryWarning.test_fail_from_worktree_warns_when_not_visible_on_primary  # noqa: E501
        """MUST FIRE: `fail` run from a worktree logs a loud, greppable
        warning naming the primary checkout and the follow-up needed --
        the failure log is real (committed) but NOT yet visible to the
        fleet."""
        import logging

        from frob.app.config import AppConfig
        from frob.app.ticket_runner._close_cmd import _fail

        primary, worktree = _fail_fixture
        with caplog.at_level(logging.ERROR):
            cfg = AppConfig(
                ticket_command="fail",
                ticket_id="T-0001",
                ticket_path=worktree,
                ticket_summary="dead end, see T-9999",
            )
            _fail(worktree, cfg)

        assert any(
            "NOT yet visible" in r.message and str(primary) in r.message
            for r in caplog.records
        ), [r.message for r in caplog.records]
        # The failure log itself really did commit -- this is a visibility
        # warning, not a report of a failed write.
        shown = _git("log", "-1", "--format=%s", cwd=worktree)
        assert "fail-logged" in shown.stdout

    def test_fail_from_primary_is_quiet(
        self,
        _fail_fixture: tuple[Path, Path],
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        # frob:tests tests/unit/test_ticket_runner_ledger_mirror.py::TestFailNotVisibleOnPrimaryWarning.test_fail_from_primary_is_quiet  # noqa: E501
        """MUST STAY QUIET: `fail` run directly in the primary checkout
        (root IS primary, nothing invisible) never emits the warning."""
        import logging

        from frob.app.config import AppConfig
        from frob.app.ticket_runner._close_cmd import _fail

        primary, _worktree = _fail_fixture
        with caplog.at_level(logging.ERROR):
            cfg = AppConfig(
                ticket_command="fail",
                ticket_id="T-0001",
                ticket_path=primary,
                ticket_summary="dead end, see T-9999",
            )
            _fail(primary, cfg)

        assert not any("NOT yet visible" in r.message for r in caplog.records), [
            r.message for r in caplog.records
        ]


# frob:ticket T-3468
class TestDoneReportNotVisibleOnPrimaryWarning:
    """`frob ticket done-report` (like `fail`, T-3137) commits to the
    worktree's own branch ONLY -- `LEDGER_VERB_STRATEGY["done-report"]`
    stays deliberately GENERIC_COMMIT_UNMIRRORED (T-2603). T-3468 DEFECT
    2 was an agent silently believing a worktree-only `done-report` had
    reached main; `_warn_if_done_report_not_visible_on_primary` makes
    that gap loud instead."""

    def test_done_report_from_worktree_warns_when_not_visible_on_primary(
        self,
        _fail_fixture: tuple[Path, Path],
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        # frob:tests tests/unit/test_ticket_runner_ledger_mirror.py::TestDoneReportNotVisibleOnPrimaryWarning.test_done_report_from_worktree_warns_when_not_visible_on_primary  # noqa: E501
        """MUST FIRE: `done-report` run from a worktree logs a loud,
        greppable warning naming the primary checkout."""
        import logging

        from frob.app.ticket_runner._verify import (
            _warn_if_done_report_not_visible_on_primary,
        )

        primary, worktree = _fail_fixture
        with caplog.at_level(logging.ERROR):
            _warn_if_done_report_not_visible_on_primary(worktree, "T-0001")

        assert any(
            "NOT yet visible" in r.message and str(primary) in r.message
            for r in caplog.records
        ), [r.message for r in caplog.records]

    def test_done_report_from_primary_is_quiet(
        self,
        _fail_fixture: tuple[Path, Path],
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        # frob:tests tests/unit/test_ticket_runner_ledger_mirror.py::TestDoneReportNotVisibleOnPrimaryWarning.test_done_report_from_primary_is_quiet  # noqa: E501
        """MUST STAY QUIET: `done-report` run directly in the primary
        checkout (root IS primary, nothing invisible) never warns."""
        import logging

        from frob.app.ticket_runner._verify import (
            _warn_if_done_report_not_visible_on_primary,
        )

        primary, _worktree = _fail_fixture
        with caplog.at_level(logging.ERROR):
            _warn_if_done_report_not_visible_on_primary(primary, "T-0001")

        assert not any("NOT yet visible" in r.message for r in caplog.records), [
            r.message for r in caplog.records
        ]
