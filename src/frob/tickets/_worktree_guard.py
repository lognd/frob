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


# frob:doc docs/modules/tickets-data-storage.md#worktree-lease-guard-t-0431
# frob:ticket T-3094
# frob:tests tests/test_worktree_guard.py::TestApplyAgentEnv.test_mutates_current_process_env_under_fleet_context  # noqa: E501
# frob:tests tests/test_worktree_guard.py::TestApplyAgentEnv.test_must_stay_quiet_no_fleet_context_leaves_env_unset  # noqa: E501
# frob:tests tests/test_worktree_guard.py::TestApplyAgentEnv.test_child_subprocess_inherits_the_bound  # noqa: E501
def apply_agent_env(root: Path) -> Result[dict[str, str], GitError]:
    """`agent_env_exports(root)`, ALSO applied to this process's own
    `os.environ` (T-3094): the delivery-gap fix for the T-2221 fleet-aware
    xdist bound.

    T-2221/T-0574 shipped `agent_env_exports` and a CLI (`frob agent env`)
    that PRINTS its result as `export KEY=VALUE` lines for a human/agent to
    `eval` into the shell that later runs pytest. Measured 2026-08-27 under
    a live three-agent fleet: 0 of 40 running pytest workers carried
    `PYTEST_XDIST_AUTO_NUM_WORKERS` despite 3 live leases satisfying the
    precondition. Root cause, established by evidence before this function
    was written: `agent_env_exports` is correct (a fleet context computes a
    real bound -- ruling out a detection bug) and its ONLY consumers in the
    codebase (`frob.app.agent_runner`, `_lifecycle._print_agent_env_hint`)
    both only ever PRINT it. Nothing anywhere calls
    `os.environ[...] = ...` with the result, so the bound survives only as
    long as the one shell that ran `eval` -- and a dispatched agent's
    tool-driven shell does not persist state between separate command
    invocations, so even a compliant `eval` is typically gone before the
    next command (the one that actually runs pytest) starts. This is
    failure mode (b) in T-3094's diagnosis: invoked and printed, but never
    actually sourced into the environment of the process tree that spawns
    pytest.

    `apply_agent_env` closes that gap for any caller running IN-PROCESS
    before it spawns pytest: `subprocess.run`/`Popen` inherit the parent's
    `os.environ` by default, so mutating the CURRENT process's environment
    here reaches a child pytest with no shell `eval` hop at all. This does
    NOT retroactively fix a raw shell invocation of `pytest` typed by an
    agent in a later, unrelated command -- that class of gap needs the
    caller to invoke this (or the CLI's export text) in the SAME process
    tree as the pytest call, which is wiring work outside this ticket's
    single-file scope (residue ticket filed).

    On `Err` (root does not resolve to a git worktree), nothing is
    mutated -- identical to `agent_env_exports`'s own error behavior."""
    exports = agent_env_exports(root)
    if exports.is_err:
        return exports
    os.environ.update(exports.danger_ok)
    return exports


# frob:doc docs/modules/tickets-data-storage.md#worktree-lease-guard-t-0431
# frob:ticket T-3094
# frob:tests tests/test_worktree_guard.py::TestWarnIfXdistBoundMissing.test_must_fire_fleet_context_with_bound_missing_logs_error  # noqa: E501
# frob:tests tests/test_worktree_guard.py::TestWarnIfXdistBoundMissing.test_must_stay_quiet_bound_present_no_log  # noqa: E501
# frob:tests tests/test_worktree_guard.py::TestWarnIfXdistBoundMissing.test_must_stay_quiet_no_fleet_context_no_log  # noqa: E501
def warn_if_xdist_bound_missing(root: Path) -> None:
    """LOUD half of the T-3094 fix: logs ERROR when `root` has a fleet
    context (`_bounded_xdist_workers` returns non-`None`) but this
    process's CURRENT `os.environ` does not actually carry
    `PYTEST_XDIST_AUTO_NUM_WORKERS` -- the exact silent-fallback-to-`-n
    auto` condition T-3094 measured (0 of 40 running workers bounded
    despite 3 live leases).

    Call this immediately before spawning a pytest subprocess so the gap
    is visible in THAT process's own log, rather than only discoverable
    after the fact via a live `/proc/<pid>/environ` fleet scan. Declaring
    the boundary loudly rather than degrading silently is the standing
    doctrine this repo has hit repeatedly (T-2221's own docstring already
    names this class).

    Best-effort diagnostic, never raises: an unresolvable `root` (not a
    git worktree) degrades to a DEBUG log and returns, matching
    `enforce_worktree_lease`'s "cannot resolve a root" posture -- this is
    not a gate. No fleet context (`_bounded_xdist_workers` is `None`) is
    silent by design -- the must-still-pass single-developer control, the
    same one `agent_env_exports` itself protects."""
    actual = repo_root(root)
    if actual.is_err:
        _log.debug(
            "xdist-bound check: %s unresolvable as a repo (%s), skipping",
            root,
            actual.danger_err,
        )
        return
    resolved = actual.danger_ok.resolve()
    expected = _bounded_xdist_workers(resolved)
    if expected is None:
        return
    if PYTEST_XDIST_AUTO_NUM_WORKERS_ENV in os.environ:
        return
    _log.error(
        "xdist-bound: fleet context detected for %s (bound would be %d) but "
        "%s is NOT set in this process's environment -- a pytest spawned "
        "here falls back to xdist's plain -n auto (full CPU count) instead "
        "of the fleet-aware bound (T-3094); call apply_agent_env(%s) before "
        "spawning pytest to fix this in-process",
        resolved,
        expected,
        PYTEST_XDIST_AUTO_NUM_WORKERS_ENV,
        resolved,
    )


__all__ = [
    "FROB_AGENT_ENV",
    "FROB_WORKTREE_ENV",
    "PYTEST_XDIST_AUTO_NUM_WORKERS_ENV",
    "agent_env_exports",
    "apply_agent_env",
    "enforce_worktree_lease",
    "warn_if_xdist_bound_missing",
]
