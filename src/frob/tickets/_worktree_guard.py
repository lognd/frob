"""Worktree-lease guard (T-0431): fail LOUDLY when a dispatched agent's
shell operates outside the worktree it was leased to.

Incident this closes: a dispatched worktree agent ran `git merge main`,
`make core`, and `frob ticket new` (minting T-0427) directly against the
SHARED main checkout instead of its own worktree -- the harness's Edit
tool scopes file edits, but a stray bash command is not caught by
anything. `FROB_WORKTREE=<abs path>` is the dispatcher-set env var naming
the ONE worktree an agent's shell is authorized to mutate frob's tracked
state in; every mutating `frob.tickets` entry point calls
`enforce_worktree_lease` first and refuses (`Err(WorktreeLeaseViolation)`)
if the cwd's actual git top-level is not that worktree. A coordinator
process (no `FROB_WORKTREE` set) is unaffected -- landing worktree changes
onto main, or any other coordinator-run mutation, has no lease to violate.
"""

from __future__ import annotations

import os
from pathlib import Path

from typani.result import Err, Ok, Result

from frob.gitio import repo_root
from frob.logging import get_logger
from frob.tickets._models import TicketError

_log = get_logger(__name__)

# frob:doc docs/modules/tickets.md#worktree-lease-guard-t-0431
FROB_WORKTREE_ENV = "FROB_WORKTREE"


# frob:doc docs/modules/tickets.md#worktree-lease-guard-t-0431
# frob:tests tests/test_worktree_guard.py::TestEnforceWorktreeLease::test_no_env_var_is_unrestricted  # noqa: E501
# frob:tests tests/test_worktree_guard.py::TestEnforceWorktreeLease::test_matching_worktree_passes  # noqa: E501
# frob:tests tests/test_worktree_guard.py::TestEnforceWorktreeLease::test_mismatched_worktree_refuses  # noqa: E501
def enforce_worktree_lease(root: Path) -> Result[None, TicketError]:
    """`Err(WorktreeLeaseViolation)` if the `FROB_WORKTREE` env var is set
    AND `root`'s actual git top-level (`git rev-parse --show-toplevel`,
    worktree-correct) does not match it -- the core check every mutating
    `frob.tickets` entry point runs first (T-0431).

    `FROB_WORKTREE` unset (the default, coordinator-run commands, or any
    environment that never opted in) is `Ok(None)`: unrestricted, matching
    behavior before this ticket. A `root` that fails to resolve to a repo
    at all (`repo_root` errors) also passes through as `Ok(None)` --
    "cannot resolve a git root" is `frob.gitio`'s own concern (every
    caller here already handles a non-repo `root` on its own terms); this
    guard only ever ADDS a refusal on top of an otherwise-successful
    resolution, it never invents a new failure mode for an already-broken
    `root`.
    """
    leased = os.environ.get(FROB_WORKTREE_ENV, "").strip()
    if not leased:
        return Ok(None)
    leased_path = Path(leased).resolve()

    actual = repo_root(root)
    if actual.is_err:
        _log.debug(
            "worktree-guard: %s unresolvable as a repo (%s), skipping lease check",
            root,
            actual.danger_err,
        )
        return Ok(None)
    actual_path = actual.danger_ok.resolve()

    if actual_path != leased_path:
        _log.error(
            "worktree-guard: agent leased to %s; refusing to mutate %s "
            "(cwd resolved to %s) -- cd into the leased worktree, or clear "
            "%s if this is deliberate",
            leased_path,
            actual_path,
            root,
            FROB_WORKTREE_ENV,
        )
        return Err(TicketError.WorktreeLeaseViolation)
    return Ok(None)


__all__ = ["FROB_WORKTREE_ENV", "enforce_worktree_lease"]
