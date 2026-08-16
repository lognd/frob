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

from frob.gitio import GitError, repo_root
from frob.logging import get_logger
from frob.tickets._leases import read_all_leases
from frob.tickets._models import TicketError

_log = get_logger(__name__)

# frob:doc docs/modules/tickets-data-storage.md#worktree-lease-guard-t-0431
FROB_WORKTREE_ENV = "FROB_WORKTREE"

# frob:doc docs/modules/tickets-data-storage.md#worktree-lease-guard-t-0431
#: T-0574: the flag `frob agent env` also exports, and the same flag
#: `frob.gates`/`release_gate`/the scaffold-managed hooks already read to
#: tell a dispatched worktree agent's shell apart from a coordinator's
#: (see `src/frob/gates/__init__.py`, `src/frob/scaffold/project.py`).
#: Defined once here rather than re-stringified at each call site.
FROB_AGENT_ENV = "FROB_AGENT"

# frob:doc docs/modules/tickets-data-storage.md#worktree-lease-guard-t-0431
#: T-2221: the env var `pytest-xdist` 3.8.0 reads when resolving `-n auto`
#: (`.venv/.../xdist/plugin.py`'s `env_var = os.environ.get(
#: "PYTEST_XDIST_AUTO_NUM_WORKERS")`). `agent_env_exports` sets this
#: alongside `FROB_WORKTREE`/`FROB_AGENT` -- the SAME env-injection choke
#: point, inherited by every downstream pytest spawn (a dispatched agent's
#: own raw shell invocation, and any frob-spawned subprocess that does not
#: override `addopts`) without duplicating the bound at each of the several
#: places in this codebase that spawn pytest.
PYTEST_XDIST_AUTO_NUM_WORKERS_ENV = "PYTEST_XDIST_AUTO_NUM_WORKERS"


# frob:doc docs/modules/tickets-data-storage.md#worktree-lease-guard-t-0431
# frob:tests tests/test_worktree_guard.py::TestEnforceWorktreeLease.test_no_env_var_is_unrestricted  # noqa: E501
# frob:tests tests/test_worktree_guard.py::TestEnforceWorktreeLease.test_matching_worktree_passes  # noqa: E501
# frob:tests tests/test_worktree_guard.py::TestEnforceWorktreeLease.test_mismatched_worktree_refuses  # noqa: E501
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
    # frob:waive SEC110 reason="worktree-lease path marker, not a secret"
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


# frob:ticket T-2221
def _bounded_xdist_workers(root: Path) -> int | None:
    """The `PYTEST_XDIST_AUTO_NUM_WORKERS` value `agent_env_exports` should
    export for `root`, or `None` to export nothing at all (T-2221).

    Derived from `read_all_leases(root)` -- the SAME real, cross-worktree
    concurrency signal `frob.tickets._doable.doable` already uses to detect
    other live agents, never a `ps`-parsed process count (this repo has
    already shipped a 4x miscount that way). `read_all_leases` degrades to
    `()` on anything it cannot resolve, so a non-repo `root` or a repo with
    no lease side-channel yet both fall out of `existing == 0` naturally.

    `existing = len(read_all_leases(root))` counts every OTHER
    currently-live ticket lease (this call's own ticket, if it has not
    `ticket start`ed yet, is deliberately not among them). `existing == 0`
    -- no fleet detected -- exports nothing, so a pytest spawned from this
    environment resolves `-n auto` against the plain xdist default (the
    full CPU count): the must-still-pass single-developer control. Only
    `existing >= 1` (this agent joining at least one other) computes a
    bound, treating itself as one more concurrent agent alongside
    `existing`: `max(1, cpu_count // (existing + 1))`, never a hardcoded
    constant."""
    existing = len(read_all_leases(root))
    if existing == 0:
        return None
    cpu_count = os.cpu_count() or 1
    return max(1, cpu_count // (existing + 1))


# frob:doc docs/modules/tickets-data-storage.md#worktree-lease-guard-t-0431
# frob:tests tests/test_worktree_guard.py::TestAgentEnvExports.test_resolves_worktree_root  # noqa: E501
# frob:tests tests/test_worktree_guard.py::TestAgentEnvExports.test_non_repo_root_errs  # noqa: E501
# frob:tests \
# tests/test_worktree_guard.py::TestAgentEnvExports.test_fleet_context_bounds_xdist_wor\
# kers
# frob:tests \
# tests/test_worktree_guard.py::TestAgentEnvExports.test_no_fleet_context_omits_xdist_b\
# ound
def agent_env_exports(root: Path) -> Result[dict[str, str], GitError]:
    """The `FROB_WORKTREE`/`FROB_AGENT`/`PYTEST_XDIST_AUTO_NUM_WORKERS`
    values `frob agent env` should export for `root`'s worktree (T-0574,
    T-2221): `FROB_WORKTREE` is the resolved git top-level (worktree-
    correct, the exact value `enforce_worktree_lease` checks a shell's env
    against), `FROB_AGENT` is always `"1"`.
    `PYTEST_XDIST_AUTO_NUM_WORKERS` (T-2221) is present, bounded, only when
    `_bounded_xdist_workers` detects other live agent leases -- see its
    docstring for the must-still-pass single-developer control -- so every
    pytest spawned from this exported environment (this agent's own raw
    shell invocation included, not just frob's internal subprocess calls)
    redefines what `-n auto` means instead of fighting `addopts`.
    `Err(GitError.NotARepo)` if `root` does not resolve to a git worktree
    at all -- `frob agent env` has nothing meaningful to export for a
    non-repo path, so this is a real failure here (unlike `enforce_
    worktree_lease`, which treats an unresolvable root as "nothing to
    guard" and passes through `Ok`)."""
    actual = repo_root(root)
    if actual.is_err:
        _log.warning("agent env: %s does not resolve to a git worktree", root)
        return Err(actual.danger_err)
    resolved = actual.danger_ok.resolve()
    _log.info("agent env: resolved %s -> FROB_WORKTREE=%s", root, resolved)
    exports = {FROB_WORKTREE_ENV: str(resolved), FROB_AGENT_ENV: "1"}
    workers = _bounded_xdist_workers(resolved)
    if workers is not None:
        _log.info(
            "agent env: fleet context detected for %s -> %s=%d",
            resolved,
            PYTEST_XDIST_AUTO_NUM_WORKERS_ENV,
            workers,
        )
        exports[PYTEST_XDIST_AUTO_NUM_WORKERS_ENV] = str(workers)
    return Ok(exports)


__all__ = [
    "FROB_AGENT_ENV",
    "FROB_WORKTREE_ENV",
    "PYTEST_XDIST_AUTO_NUM_WORKERS_ENV",
    "agent_env_exports",
    "enforce_worktree_lease",
]
