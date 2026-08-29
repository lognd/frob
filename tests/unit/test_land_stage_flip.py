"""T-3121: the flip that runs the whole squash-apply transaction in a
DISPOSABLE worktree and publishes the result onto `main` by
compare-and-swap, instead of building it in the shared root checkout.

Deliberately a SEPARATE module from tests/test_ticket_land.py for the same
reason tests/unit/test_land_squash_stage.py is: that file's `land()`-driven
tests leak `FROB_WORKTREE` in-process (T-3123), so anything running after
them in the same worker refuses with `TicketError.WorktreeLeaseViolation`.
Evidence that has to RESOLVE cannot live behind that, so these build their
own fixture repo from git plumbing and touch no ticket-mutating verb.
"""

from __future__ import annotations

import subprocess
import threading
from pathlib import Path

import pytest

import frob.tickets._land as _land_mod
from frob.tickets._models import (
    LandError,
    Origin,
    Ticket,
    TicketKind,
    TicketSpec,
)
from frob.tickets._new_renumber import _ticket_from_spec
from frob.tickets._store import _serialize_ticket, atomic_write, v2_ticket_path


def _run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess:
    """`subprocess.run` with `check=True` against `cwd` -- this module's
    only way of talking to git, kept identical in shape to the helper
    tests/unit/test_land_squash_stage.py uses."""
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


def _seed(root: Path, ticket_id: str, scope: tuple[str, ...]) -> Ticket:
    """Write a QUEUED ticket into v2-mode storage (`tickets/<id>/
    ticket.md`), which is what flips `_store_mode(root)` to 'v2'."""
    ticket = _ticket_from_spec(
        ticket_id,
        TicketSpec(
            title="Disposable stage flip",
            kind=TicketKind.FEATURE,
            origin=Origin.AGENT,
            scope=scope,
        ),
        (),
    )
    path = v2_ticket_path(root, ticket_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    assert atomic_write(path, _serialize_ticket(ticket)).is_ok
    return ticket


@pytest.fixture
def v2_main(tmp_path: Path) -> Path:
    """A v2-mode main checkout with one committed ticket directory and one
    committed source file."""
    root = tmp_path / "v2main"
    root.mkdir(parents=True)
    _run(["git", "init", "-q", "-b", "main"], root)
    _run(["git", "config", "user.email", "test@example.com"], root)
    _run(["git", "config", "user.name", "Test"], root)
    (root / ".gitignore").write_text(".frob/\n")
    _seed(root, "T-3000", ("src/seed.py",))
    (root / "src").mkdir()
    (root / "src" / "feature.py").write_text("# landed feature\n")
    _run(["git", "add", "-A"], root)
    _run(["git", "commit", "-q", "-m", "init v2"], root)
    return root


def _prepare(
    v2_main: Path, slug: str, *, also_touch_feature: bool = False
) -> tuple[Path, Ticket, str, str]:
    """A finalized feature worktree branch plus root's pre-land tip -- the
    exact inputs `_land_locked` hands the squash-apply stage.
    `also_touch_feature` additionally edits `src/feature.py`, a path root's
    own checkout already has, so a test can make root's uncommitted edit
    collide with the landed changeset."""
    wt = v2_main.parent / f"wt-flip-{slug}"
    _run(["git", "worktree", "add", "-q", "-b", f"flip-{slug}", str(wt)], v2_main)
    ticket_id = f"T-31{slug}"
    ticket = _seed(wt, ticket_id, ("src/staged.py", "src/feature.py"))
    (wt / "src" / "staged.py").write_text("# staged by the disposable stage\n")
    if also_touch_feature:
        (wt / "src" / "feature.py").write_text("# landed feature, revised\n")
    _run(["git", "add", "-A"], wt)
    _run(["git", "commit", "-q", "-m", f"add staged.py for {ticket_id}"], wt)
    pre_land_tip = _run(["git", "rev-parse", "HEAD"], v2_main).stdout.strip()
    return wt, ticket, ticket_id, pre_land_tip


def _flip(v2_main: Path, prepared: tuple[Path, Ticket, str, str], **kwargs):  # noqa: ANN003, ANN201
    """Invoke the flip exactly as `_land_locked` does."""
    wt, ticket, ticket_id, pre_land_tip = prepared
    return _land_mod._squash_apply_on_disposable_stage(
        v2_main,
        wt,
        ticket,
        ticket_id,
        ticket_id,
        False,
        False,
        "main",
        pre_land_tip=pre_land_tip,
        **kwargs,
    )


# frob:ticket T-3121
# frob:ticket T-3135
class TestDisposableStageFlip:
    """The flip's must-fire / must-stay-quiet pair plus its refusal path.

    MUST FIRE: a land's entire staged-but-uncommitted window is invisible
    to a concurrent poll of root. MUST STAY QUIET: a profile that wires
    the T-1514 pre-commit sweep keeps the old in-root path rather than
    handing that sweep a checkout it cannot measure."""

    def test_root_never_goes_dirty_during_the_squash_apply(self, v2_main: Path) -> None:
        # frob:tests tests/unit/test_land_stage_flip.py::TestDisposableStageFlip.test_root_never_goes_dirty_during_the_squash_apply  # noqa: E501
        """MUST FIRE (acceptance 0): poll root's porcelain status
        continuously for the whole length of a real squash-apply and
        observe ZERO dirty samples -- the transaction is built in a
        disposable worktree and becomes visible only as one atomic ref
        move. Before this flip the same poll saw the full staged changeset
        for the entire duration of the merge, splice, bump and sweep."""
        prepared = _prepare(v2_main, "10")
        pre_land_tip = prepared[3]
        samples: list[tuple[str, str, str]] = []
        stop = threading.Event()

        def poll() -> None:
            # `_head` and `_porcelain` are two separate git spawns, so a
            # sample that straddles the publish would read an old HEAD and
            # a post-publish status. Bracketing the status with a HEAD read
            # on BOTH sides makes a torn sample identifiable rather than
            # silently miscounted as a pre-publish dirty observation.
            while not stop.is_set():
                before = _head(v2_main)
                porcelain = _porcelain(v2_main)
                samples.append((before, porcelain, _head(v2_main)))

        poller = threading.Thread(target=poll, daemon=True)
        poller.start()
        try:
            result = _flip(v2_main, prepared)
        finally:
            stop.set()
            poller.join(timeout=10)

        assert result.is_ok, result.err
        # Only the PRE-PUBLISH window is this ticket's claim: a sample
        # taken while root still names `pre_land_tip` is a sample taken
        # before the atomic ref move, and every one of those must be
        # clean. (`_record_land_commit`'s own follow-up write, which runs
        # in root AFTER the publish, is a separate and pre-existing
        # window -- see this ticket's Done report for the residue filed.)
        pre_publish = [
            porcelain
            for before, porcelain, after in samples
            if before == pre_land_tip and after == pre_land_tip
        ]
        assert pre_publish, "the poller never sampled -- the measurement is void"
        assert [p for p in pre_publish if p] == []
        assert _head(v2_main) != pre_land_tip
        assert (v2_main / "src" / "staged.py").exists()
        assert _porcelain(v2_main) == ""

    # frob:ticket T-3135
    def test_pre_commit_sweep_engages_the_warm_stage_not_root(
        self, v2_main: Path
    ) -> None:
        # frob:tests tests/unit/test_land_stage_flip.py::TestDisposableStageFlip.test_pre_commit_sweep_engages_the_warm_stage_not_root  # noqa: E501
        """MUST FIRE (T-3135): with a `pre_commit_sweep` supplied, the
        flip now hands it the PERSISTENT warm stage -- not `root` (T-3121's
        old carve-out) and not a bare disposable worktree (unmeasurable
        per T-3127's own measurement) -- holding the real staged
        changeset, with `root` itself untouched by the squash-apply."""
        prepared = _prepare(v2_main, "11")
        seen: list[Path] = []

        def sweep(path: Path, final_id: str) -> bool:
            del final_id
            seen.append(path)
            assert (path / "src" / "staged.py").exists(), (
                "the sweep was handed a checkout that does not hold the "
                "staged changeset -- it would measure the wrong tree"
            )
            return True

        result = _flip(v2_main, prepared, pre_commit_sweep=sweep)

        assert result.is_ok, result.err
        assert len(seen) == 1
        assert seen[0] != v2_main
        assert seen[0] == v2_main / ".frob" / "warm-sweep-stage"

    # frob:ticket T-3135
    def test_warm_stage_reused_across_lands(self, v2_main: Path) -> None:
        # frob:tests tests/unit/test_land_stage_flip.py::TestDisposableStageFlip.test_warm_stage_reused_across_lands  # noqa: E501
        """MUST FIRE (T-3135): a SECOND land reuses the exact same warm
        stage path a first land created -- the whole point of a
        PERSISTENT stage rather than a fresh disposable one per land."""
        seen: list[Path] = []

        def sweep(path: Path, final_id: str) -> bool:
            del final_id
            seen.append(path)
            return True

        first = _prepare(v2_main, "13")
        result_1 = _flip(v2_main, first, pre_commit_sweep=sweep)
        assert result_1.is_ok, result_1.err

        second = _prepare(v2_main, "14")
        result_2 = _flip(v2_main, second, pre_commit_sweep=sweep)
        assert result_2.is_ok, result_2.err

        assert len(seen) == 2
        assert seen[0] == seen[1]

    # frob:ticket T-3135
    def test_warm_stage_unavailable_falls_back_to_root(
        self, v2_main: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_land_stage_flip.py::TestDisposableStageFlip.test_warm_stage_unavailable_falls_back_to_root  # noqa: E501
        """MUST STAY QUIET (T-3135's own fallback): when the warm stage
        cannot be prepared at all, the sweep degrades to the pre-T-3135
        in-root path -- never a silently skipped sweep."""
        monkeypatch.setattr(
            _land_mod, "_ensure_warm_sweep_stage", lambda root, tip: None
        )
        prepared = _prepare(v2_main, "15")
        seen: list[Path] = []

        def sweep(path: Path, final_id: str) -> bool:
            del final_id
            seen.append(path)
            assert (path / "src" / "staged.py").exists()
            return True

        result = _flip(v2_main, prepared, pre_commit_sweep=sweep)

        assert result.is_ok, result.err
        assert seen == [v2_main]

    def test_worktree_setup_failure_refuses_without_touching_root(
        self, v2_main: Path
    ) -> None:
        # frob:tests tests/unit/test_land_stage_flip.py::TestDisposableStageFlip.test_worktree_setup_failure_refuses_without_touching_root  # noqa: E501
        """A disposable stage that cannot be cut at all is a hard refusal,
        not a silent fall-back into the shared root: root's tip and
        working tree are exactly as they were and nothing was published."""
        wt, ticket, ticket_id, real_tip = _prepare(v2_main, "12")

        result = _land_mod._squash_apply_on_disposable_stage(
            v2_main,
            wt,
            ticket,
            ticket_id,
            ticket_id,
            False,
            False,
            "main",
            pre_land_tip="0" * 40,
        )

        assert result.is_err
        assert result.danger_err is LandError.GitFailed
        assert _run(["git", "rev-parse", "HEAD"], v2_main).stdout.strip() == real_tip
        assert _porcelain(v2_main) == ""


# frob:ticket T-3121
class TestPublishSquashApply:
    """`_publish_squash_apply`'s three outcomes: a clean CAS publish plus
    resync, a lost CAS surfaced as the EXISTING `DirtyMain` refusal, and a
    blocked resync that is loudly reported but is NOT a land failure."""

    def test_clean_publish_advances_root_and_resyncs(self, v2_main: Path) -> None:
        # frob:tests tests/unit/test_land_stage_flip.py::TestPublishSquashApply.test_clean_publish_advances_root_and_resyncs  # noqa: E501
        """The published commit is parented on `pre_land_tip`, `main` names
        it, and root's index/working tree were advanced onto it -- so a
        following `git status` in root is clean rather than reporting the
        whole changeset as reverted local modifications."""
        prepared = _prepare(v2_main, "20")
        pre_land_tip = prepared[3]

        result = _flip(v2_main, prepared)

        assert result.is_ok, result.err
        report = result.danger_ok
        assert report.root_resync_failed is False
        landed = report.commit_sha
        assert landed is not None
        parent = _run(["git", "rev-parse", f"{landed}^"], v2_main).stdout.strip()
        assert parent == pre_land_tip
        assert (
            _run(
                ["git", "merge-base", "--is-ancestor", landed, "main"], v2_main
            ).returncode
            == 0
        )
        assert (v2_main / "src" / "staged.py").read_text().startswith("# staged")

    def test_racing_publish_surfaces_dirtymain(self, v2_main: Path) -> None:
        # frob:tests tests/unit/test_land_stage_flip.py::TestPublishSquashApply.test_racing_publish_surfaces_dirtymain  # noqa: E501
        """MUST FIRE (acceptance 1): when `main` moves after this land
        captured `pre_land_tip`, the compare-and-swap loses and the land
        gets the EXISTING `DirtyMain` refusal -- no new error class for an
        old condition, no corrupted ref, and no silent overwrite of the
        commit that won the race."""
        prepared = _prepare(v2_main, "21")
        pre_land_tip = prepared[3]
        (v2_main / "src" / "sibling.py").write_text("# a sibling landed first\n")
        _run(["git", "add", "-A"], v2_main)
        _run(["git", "commit", "-q", "-m", "sibling land"], v2_main)
        raced_tip = _run(["git", "rev-parse", "HEAD"], v2_main).stdout.strip()
        assert raced_tip != pre_land_tip

        result = _flip(v2_main, prepared)

        assert result.is_err
        assert result.danger_err is LandError.DirtyMain
        assert _run(["git", "rev-parse", "HEAD"], v2_main).stdout.strip() == raced_tip
        assert (v2_main / "src" / "sibling.py").exists()
        assert not (v2_main / "src" / "staged.py").exists()

    def test_blocked_resync_is_not_a_land_failure(self, v2_main: Path) -> None:
        # frob:tests tests/unit/test_land_stage_flip.py::TestPublishSquashApply.test_blocked_resync_is_not_a_land_failure  # noqa: E501
        """MUST FIRE (acceptance 2): a sibling holding an uncommitted edit
        to a path this land ALSO changed makes `read-tree -m -u` refuse
        atomically. The commit is already public and correct by then, so
        `land()` still returns Ok; the report carries
        `root_resync_failed=True` and the sibling's bytes are untouched.
        Reverting here would destroy a published commit to fix a local
        inconvenience."""
        prepared = _prepare(v2_main, "22", also_touch_feature=True)
        pre_land_tip = prepared[3]
        (v2_main / "src" / "feature.py").write_text("# SIBLING WORK IN PROGRESS\n")

        result = _flip(v2_main, prepared)

        assert result.is_ok, result.err
        assert result.danger_ok.root_resync_failed is True
        head = _run(["git", "rev-parse", "HEAD"], v2_main).stdout.strip()
        assert head != pre_land_tip
        assert (
            _run(["git", "show", "HEAD:src/feature.py"], v2_main).stdout
            == "# landed feature, revised\n"
        )
        assert (
            v2_main / "src" / "feature.py"
        ).read_text() == "# SIBLING WORK IN PROGRESS\n"
