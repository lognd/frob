"""T-3126: `_record_land_commit` composes its follow-up bookkeeping commit
out of tree and publishes it by compare-and-swap, instead of writing,
staging and committing it inside the shared root checkout.

T-3121 closed the PRE-publish dirty window (the whole squash-apply
transaction moved to a disposable worktree). This module covers the
remaining POST-publish one: the `land_commit` record commit, which used to
dirty root for its duration and advance `refs/heads/<branch>` by plain
fast-forward with no compare-and-swap at all.

Deliberately a SEPARATE module from tests/test_ticket_land.py for the same
reason tests/unit/test_land_stage_flip.py is: that file's `land()`-driven
tests leak `FROB_WORKTREE` in-process (T-3123), so anything running after
them in the same worker refuses with `TicketError.WorktreeLeaseViolation`.
Evidence that has to RESOLVE cannot live behind that, so these build their
own fixture repo from git plumbing.
"""

from __future__ import annotations

import subprocess
import threading
import time
from pathlib import Path

import pytest

import frob.tickets._land_squash as _land_squash_mod
from frob.tickets import _load_one
from frob.tickets._models import Origin, Ticket, TicketKind, TicketSpec
from frob.tickets._new_renumber import _ticket_from_spec
from frob.tickets._store import (
    _serialize_ticket,
    atomic_write,
    v2_ticket_path,
    write_ticket,
)

TICKET_ID = "T-3000"


def _run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess:
    """`subprocess.run` with `check=True` against `cwd` -- this module's
    only way of talking to git, kept identical in shape to the helper
    tests/unit/test_land_stage_flip.py uses."""
    return subprocess.run(
        argv, cwd=str(cwd), check=True, capture_output=True, text=True
    )


def _porcelain(root: Path) -> str:
    """Root's `git status --porcelain` taken with `--no-optional-locks` --
    the only safe way to poll a checkout a land may be running against,
    since a plain `git status` takes `.git/index.lock` and has killed a
    real land."""
    done = subprocess.run(
        ["git", "--no-optional-locks", "-C", str(root), "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=False,
    )
    return done.stdout.strip()


def _head(root: Path) -> str:
    """Root's current `HEAD` sha, read with `--no-optional-locks` so it is
    safe to call from a poller running against a live land."""
    done = subprocess.run(
        ["git", "--no-optional-locks", "-C", str(root), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    return done.stdout.strip()


def _seed(root: Path, ticket_id: str) -> Ticket:
    """Write a ticket into v2-mode storage (`tickets/<id>/ticket.md`),
    which is what flips `_store_mode(root)` to 'v2'."""
    ticket = _ticket_from_spec(
        ticket_id,
        TicketSpec(
            title="Record the land commit out of tree",
            kind=TicketKind.BUG,
            origin=Origin.AGENT,
            scope=("src/feature.py",),
        ),
        (),
    )
    path = v2_ticket_path(root, ticket_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    assert atomic_write(path, _serialize_ticket(ticket)).is_ok
    return ticket


@pytest.fixture
def landed_root(tmp_path: Path) -> Path:
    """A v2-mode checkout whose HEAD is the just-published landing commit
    -- the exact state `_record_land_commit` is called against."""
    root = tmp_path / "root"
    root.mkdir(parents=True)
    _run(["git", "init", "-q", "-b", "main"], root)
    _run(["git", "config", "user.email", "test@example.com"], root)
    _run(["git", "config", "user.name", "Test"], root)
    (root / ".gitignore").write_text(".frob/\n")
    _seed(root, TICKET_ID)
    (root / "src").mkdir()
    (root / "src" / "feature.py").write_text("# landed feature\n")
    _run(["git", "add", "-A"], root)
    _run(["git", "commit", "-q", "-m", "the landing commit"], root)
    return root


class _Poller:
    """A background porcelain poll of `root`, each sample bracketed by a
    `HEAD` read on BOTH sides so a sample straddling a ref move is
    identifiable rather than silently miscounted as a dirty observation
    (the way a spurious dirty reading gets manufactured)."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.samples: list[tuple[str, str, str]] = []
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)

    def _loop(self) -> None:
        while not self._stop.is_set():
            before = _head(self.root)
            porcelain = _porcelain(self.root)
            self.samples.append((before, porcelain, _head(self.root)))

    def __enter__(self) -> _Poller:
        self._thread.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self._stop.set()
        self._thread.join(timeout=10)

    def untorn_dirty(self) -> list[str]:
        """Dirty porcelain samples whose bracketing HEAD reads AGREE --
        every torn sample (one that straddled a ref move) is discarded, so
        what remains is a genuine observation of a dirty root."""
        return [p for before, p, after in self.samples if p and before == after]


# frob:ticket T-3126
class TestRecordLandCommitOutOfTree:
    """The out-of-tree record's before/after pair, with the probe's own
    positive control, plus its compare-and-swap refusal path."""

    def test_probe_catches_the_in_root_write_positive_control(
        self, landed_root: Path
    ) -> None:
        # frob:tests tests/unit/test_land_record_commit.py::TestRecordLandCommitOutOfTree.test_probe_catches_the_in_root_write_positive_control  # noqa: E501
        """POSITIVE CONTROL / BEFORE arm: run the OLD shape by hand --
        `write_ticket` into root, then `git add`, then `git commit` -- and
        assert the poller observes at least one untorn dirty sample. A
        zero from the AFTER arm means nothing unless this arm proves the
        probe can see the state it claims is gone."""
        land_sha = _head(landed_root)
        loaded = _load_one(landed_root, TICKET_ID)
        assert loaded.is_ok
        updated = loaded.danger_ok.model_copy(update={"land_commit": land_sha})

        # T-3471: on CI, the OLD add-then-commit-immediately shape let the
        # commit complete before the poller thread's next porcelain sample --
        # a real scheduling race, not a bug in the probe itself, but the
        # positive control still needs to be deterministic (a control that
        # only sometimes fires proves nothing when it happens not to). Fix:
        # hold the dirty state open -- write + add, then spin-wait (bounded)
        # until the poller has actually recorded an untorn dirty sample --
        # before committing, so the control can never race the commit past
        # the sampler again.
        with _Poller(landed_root) as poller:
            assert write_ticket(landed_root, updated).is_ok
            rel = str(v2_ticket_path(landed_root, TICKET_ID).relative_to(landed_root))
            _run(["git", "add", "--", rel], landed_root)

            deadline = time.monotonic() + 10.0
            while not poller.untorn_dirty() and time.monotonic() < deadline:
                time.sleep(0.01)

            _run(
                ["git", "commit", "-q", "-m", f"record land commit for {TICKET_ID}"],
                landed_root,
            )

        assert poller.samples, "the poller never sampled -- the measurement is void"
        assert poller.untorn_dirty(), (
            "the probe saw a CLEAN root across an in-root write+add+commit -- "
            "it cannot detect the state the AFTER arm claims is gone, so a "
            "zero from that arm would prove nothing"
        )

    # frob:ticket T-3442
    def test_root_never_goes_dirty_while_the_record_is_made(
        self, landed_root: Path
    ) -> None:
        # frob:tests tests/unit/test_land_record_commit.py::TestRecordLandCommitOutOfTree.test_root_never_goes_dirty_while_the_record_is_made  # noqa: E501
        """AFTER arm (acceptance 0): the SAME probe, over the whole of
        `_record_land_commit`, observes ZERO untorn dirty samples BEFORE
        the record is composed and published -- the write itself always
        happens off-tree, in a disposable checkout, never touching
        `root`'s index or working tree.

        T-3442 investigation: `resync_root_to_published_tip`'s own docstring
        (`_land_compose.py`) is explicit that the CAS `update-ref` moves
        `HEAD` first, and ONLY THEN does `git read-tree -m -u` bring
        `root`'s index/working tree up to it -- "`git status` in root
        reports the whole landed changeset as reverted local
        modifications until this runs" is not a hypothetical, it is a
        real, acknowledged window between two separate git operations
        that cannot be merged into one atomic step without risking a
        `reset --hard` clobbering a sibling's uncommitted work (T-1740).
        A poller sampling exactly inside that window genuinely observes
        dirt -- confirmed by reproducing this locally (roughly 1 in
        5-15 runs) even outside CI, so this was never a CI-only
        artifact (hypothesis 1 did not hold). Excluding samples taken
        AFTER `HEAD` has already advanced to `new_sha` keeps the
        assertion's real teeth -- root must never carry uncommitted
        writes or a stale HEAD BEFORE the record publishes -- without
        failing on the acknowledged, self-resolving resync tail."""
        land_sha = _head(landed_root)

        with _Poller(landed_root) as poller:
            new_sha = _land_squash_mod._record_land_commit(
                landed_root, TICKET_ID, land_sha
            )

        assert new_sha is not None
        assert poller.samples, "the poller never sampled -- the measurement is void"
        pre_publish_dirty = [
            porcelain
            for before, porcelain, after in poller.samples
            if porcelain and before == after and before != new_sha
        ]
        assert pre_publish_dirty == []
        assert _porcelain(landed_root) == ""
        assert _head(landed_root) == new_sha
        parent = _run(["git", "rev-parse", f"{new_sha}^"], landed_root).stdout.strip()
        assert parent == land_sha
        reloaded = _load_one(landed_root, TICKET_ID)
        assert reloaded.is_ok
        assert reloaded.danger_ok.land_commit == land_sha

    def test_record_publishes_by_cas_and_refuses_a_moved_ref(
        self, landed_root: Path
    ) -> None:
        # frob:tests tests/unit/test_land_record_commit.py::TestRecordLandCommitOutOfTree.test_record_publishes_by_cas_and_refuses_a_moved_ref  # noqa: E501
        """MUST FIRE (the second half of this ticket): the record commit is
        published by compare-and-swap against the landing commit, so a
        sibling that published first is never clobbered by fast-forward.
        Advance the branch past `land_sha` before recording and assert the
        record makes no commit, leaves the sibling's tip exactly where it
        was, and never dirties root."""
        land_sha = _head(landed_root)
        (landed_root / "src" / "sibling.py").write_text("# a sibling's land\n")
        _run(["git", "add", "-A"], landed_root)
        _run(["git", "commit", "-q", "-m", "a sibling landed first"], landed_root)
        sibling_tip = _head(landed_root)
        assert sibling_tip != land_sha

        new_sha = _land_squash_mod._record_land_commit(landed_root, TICKET_ID, land_sha)

        assert new_sha is None
        assert _head(landed_root) == sibling_tip
        assert _porcelain(landed_root) == ""
