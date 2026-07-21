"""Cross-worktree scope-lease side-channel under the git COMMON dir (T-0473).

`frob ticket start`'s in-progress scope-lease (T-0453) lives entirely in
`tickets.md`, a file that is per-branch: an isolated worktree's checkout of
`tickets.md` never sees another worktree's `IN_PROGRESS` transition until
one of them merges/lands into the other's view of the ledger. In a
multi-agent session where every agent works in its own worktree (this
repo's normal dispatch pattern), that makes the T-0453 collision-aware
`doable` filter INERT across worktrees -- two agents can be handed
overlapping-scope tickets and neither's local `tickets.md` shows the
other's lease.

`git rev-parse --git-common-dir` resolves to the ONE `.git` directory every
worktree of a repository shares (a linked worktree's own `.git` is just a
pointer file to it) -- unlike `.git` itself, which is per-worktree for a
linked worktree, `.git/frob-leases/` under the common dir is visible from
every worktree. One small JSON file per held ticket id there
(`<ticket-id>.json`) records which worktree/branch holds it and its scope,
independent of and in addition to the ledger -- `frob.tickets.transition`
writes/removes it exactly when a ticket enters/leaves `IN_PROGRESS`, and
`leased_by` (T-0453) reads every worktree's files, not just the local
ledger's own `IN_PROGRESS` rows, to compute collisions.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel
from typani.error_set import ErrorSet
from typani.result import Err, Ok, Result

from frob.gitio import run_argv
from frob.logging import get_logger

_log = get_logger(__name__)

# frob:doc docs/modules/tickets.md#cross-worktree-lease-side-channel-t-0473
LEASES_DIRNAME = "frob-leases"


# frob:doc docs/modules/tickets.md#cross-worktree-lease-side-channel-t-0473
class LeaseError(ErrorSet):
    """Fallible outcomes of the cross-worktree lease side-channel (T-0473)."""

    GitCommonDirUnavailable = "could not resolve the shared git common dir"
    WriteFailed = "writing the lease file failed"


# frob:doc docs/modules/tickets.md#cross-worktree-lease-side-channel-t-0473
class LeaseRecord(BaseModel):
    """One held cross-worktree scope-lease (T-0473): the ticket id, its
    declared scope at the moment the lease was (re)recorded, and which
    worktree/branch holds it -- read back by `leased_by` in every OTHER
    worktree of the same repository so collision-aware `doable` sees an
    in-progress ticket regardless of which worktree started it."""

    model_config = {}

    ticket_id: str
    scope: tuple[str, ...]
    worktree: str
    branch: str
    recorded_at: str


# frob:doc docs/modules/tickets.md#cross-worktree-lease-side-channel-t-0473
# frob:tests tests/test_ticket_leases_cross_worktree.py::TestGitCommonDir.test_shared_across_linked_worktrees kind="unit"  # noqa: E501
def git_common_dir(root: Path) -> Result[Path, LeaseError]:
    """The shared `.git` directory for `root`'s repository (`git rev-parse
    --git-common-dir`), resolved to an absolute path -- identical across
    every linked worktree of the same repo, unlike `root / ".git"` itself
    (a linked worktree's `.git` is a pointer file, not the shared
    directory). `Err(GitCommonDirUnavailable)` if `root` is not inside a
    git work tree or the git call fails."""
    spawned = run_argv(["git", "-C", str(root), "rev-parse", "--git-common-dir"])
    if spawned.is_err or spawned.danger_ok.returncode != 0:
        _log.warning("tickets: git-common-dir lookup failed under %s", root)
        return Err(LeaseError.GitCommonDirUnavailable)
    raw = spawned.danger_ok.stdout.strip()
    if not raw:
        return Err(LeaseError.GitCommonDirUnavailable)
    common_dir = Path(raw)
    if not common_dir.is_absolute():
        common_dir = (root / common_dir).resolve()
    return Ok(common_dir)


# frob:doc docs/modules/tickets.md#cross-worktree-lease-side-channel-t-0473
# frob:tests tests/test_ticket_leases_cross_worktree.py::TestCrossWorktreeLeaseVisibility.test_lease_written_in_one_worktree_seen_in_another kind="unit"  # noqa: E501
def leases_dir(root: Path) -> Result[Path, LeaseError]:
    """`<git-common-dir>/frob-leases`, the directory every worktree of
    `root`'s repository shares (T-0473) -- created on first write, not
    here, so a read-only caller (`read_all_leases`) never has the side
    effect of creating it."""
    common = git_common_dir(root)
    if common.is_err:
        return Err(common.danger_err)
    return Ok(common.danger_ok / LEASES_DIRNAME)


def _lease_path(leases_root: Path, ticket_id: str) -> Path:
    """The per-ticket lease file path under `leases_root`."""
    return leases_root / f"{ticket_id}.json"


# frob:doc docs/modules/tickets.md#cross-worktree-lease-side-channel-t-0473
# frob:tests tests/test_ticket_leases_cross_worktree.py::TestCrossWorktreeLeaseVisibility.test_lease_written_in_one_worktree_seen_in_another kind="unit"  # noqa: E501
def record_lease(
    root: Path, ticket_id: str, scope: tuple[str, ...]
) -> Result[None, LeaseError]:
    """Write (or overwrite) `ticket_id`'s cross-worktree lease file recording
    `scope` and this worktree's own path/branch (T-0473) -- called by
    `frob.tickets.transition` whenever a ticket enters `IN_PROGRESS`, and by
    `mutate_scope` when an in-progress ticket's scope changes, so the
    lease's recorded scope never drifts from the ledger's.

    Best-effort by design: a `root` that is not a git work tree (a test
    fixture with no `.git`, or a checkout that predates `git init`)
    degrades to a logged warning and `Ok(None)` rather than blocking the
    state transition it rides along with -- the ledger transition itself
    is the source of truth; this side-channel exists to make OTHER
    worktrees aware of it sooner; it is never allowed to be the thing that
    turns a same-worktree `start`/`scope` failure-mode into a NEW failure
    mode."""
    resolved = leases_dir(root)
    if resolved.is_err:
        _log.warning(
            "tickets: %s lease not recorded (no shared git dir under %s) -- "
            "cross-worktree collision detection degraded for this ticket",
            ticket_id,
            root,
        )
        return Ok(None)
    leases_root = resolved.danger_ok
    try:
        leases_root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        _log.warning("tickets: could not create %s: %s", leases_root, exc)
        return Ok(None)

    branch_result = run_argv(["git", "-C", str(root), "branch", "--show-current"])
    branch = (
        branch_result.danger_ok.stdout.strip()
        if branch_result.is_ok and branch_result.danger_ok.returncode == 0
        else ""
    )
    record = LeaseRecord(
        ticket_id=ticket_id,
        scope=scope,
        worktree=str(root.resolve()),
        branch=branch,
        recorded_at=datetime.now(UTC).isoformat(),
    )
    try:
        _lease_path(leases_root, ticket_id).write_text(
            record.model_dump_json(indent=2) + "\n", encoding="utf-8"
        )
    except OSError as exc:
        _log.warning("tickets: could not write lease for %s: %s", ticket_id, exc)
        return Ok(None)
    _log.info(
        "tickets: %s lease recorded (worktree=%s branch=%s)",
        ticket_id,
        record.worktree,
        record.branch,
    )
    return Ok(None)


# frob:doc docs/modules/tickets.md#cross-worktree-lease-side-channel-t-0473
# frob:tests tests/test_ticket_leases_cross_worktree.py::TestCrossWorktreeLeaseVisibility.test_release_on_close_removes_the_lease kind="unit"  # noqa: E501
def release_lease(root: Path, ticket_id: str) -> Result[None, LeaseError]:
    """Remove `ticket_id`'s cross-worktree lease file, if any (T-0473) --
    called by `frob.tickets.transition` whenever a ticket LEAVES
    `IN_PROGRESS` (closed, requeued, failed, blocked). A missing file (never
    recorded, or already removed) is not an error -- `release_lease` is
    always safe to call unconditionally on any exit from `IN_PROGRESS`."""
    resolved = leases_dir(root)
    if resolved.is_err:
        return Ok(None)
    path = _lease_path(resolved.danger_ok, ticket_id)
    try:
        path.unlink(missing_ok=True)
    except OSError as exc:
        _log.warning("tickets: could not remove lease for %s: %s", ticket_id, exc)
        return Ok(None)
    return Ok(None)


# frob:doc docs/modules/tickets.md#cross-worktree-lease-side-channel-t-0473
# frob:tests tests/test_ticket_leases_cross_worktree.py::TestCrossWorktreeLeaseVisibility.test_doable_in_second_worktree_hides_colliding_ticket kind="unit"  # noqa: E501
# frob:tests tests/test_ticket_leases_cross_worktree.py::TestCrossWorktreeLeaseVisibility.test_stale_lease_for_a_removed_worktree_is_skipped kind="unit"  # noqa: E501
def read_all_leases(root: Path) -> tuple[LeaseRecord, ...]:
    """Every currently-recorded cross-worktree lease visible from `root`'s
    repository (T-0473), id-ordered. Degrades to `()` if there is no shared
    git common dir, no leases directory yet (nothing has ever started a
    ticket), or a lease file is unreadable/malformed -- a corrupt or
    unreadable single lease file is logged and skipped rather than failing
    the whole read, since one bad file must never blind `doable` to every
    OTHER worktree's real leases."""
    resolved = leases_dir(root)
    if resolved.is_err:
        return ()
    leases_root = resolved.danger_ok
    if not leases_root.is_dir():
        return ()
    records: list[LeaseRecord] = []
    for path in sorted(leases_root.glob("*.json")):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            record = LeaseRecord.model_validate(raw)
        except (OSError, ValueError) as exc:
            _log.warning("tickets: could not parse lease file %s: %s", path, exc)
            continue
        if not Path(record.worktree).exists():
            # T-0473/T-0476: the worktree that recorded this lease is gone
            # (removed, never cleaned up after a crash) -- a dead
            # worktree's stale lease must never wedge `doable` for every
            # other worktree forever. Liveness is judged structurally, by
            # the worktree PATH still existing on disk, the same signal
            # T-0476's fuller reconcile is designed to build on; this read
            # path just skips it rather than surfacing it, since cleanup
            # itself is that ticket's job, not this one's.
            _log.info(
                "tickets: %s lease at %s references a worktree that no "
                "longer exists (%s) -- treating as stale, skipped",
                record.ticket_id,
                path,
                record.worktree,
            )
            continue
        records.append(record)
    return tuple(records)
