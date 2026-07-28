"""Named resource leases/semaphores owned by the T-1092 socket daemon
(T-1097, docs/modules/serve.md#resource-leasessemaphores-t-1097).

T-0322 shipped `run_coverage_wait`'s coverage single-flight as a plain
per-worktree `fcntl.flock` -- OS-level blocking only, no visibility into
who holds it, and no daemon-mediated release-on-crash semantics. T-1095
moved that arbitration cross-worktree (a shared lock/cache keyed by tree
content digest). This ticket generalizes the UNDERLYING primitive one
step further: a named resource lease/semaphore the DAEMON itself owns and
arbitrates over its own JSON-RPC connections, starting with `coverage`
(capacity 1, i.e. a writer lock) so any future contended resource can
register the same way instead of each caller inventing its own flock
convention.

The daemon-arbitration property this module exists for: a lease is bound
to the JSON-RPC CONNECTION that acquired it, not to an explicit release
call the client must remember to make. `ResourceLeaseManager.release_
holder` is called from `_RequestHandler.handle`'s `finally` block (T-1092
precedent: `subscribe`'s per-connection unsubscribe already works this
way) -- a crashed or disconnected client's lease is freed the moment the
daemon notices the connection is gone, satisfying T-0321 requirement 3
("killing a client loses nothing, nothing to clean up") without a daemon
restart.
"""
# frob:waive INV006 reason="T-1097 INV006 calibration-batch disposition: this file's \
# exclusivity-vocabulary hits ('only', 'no-op') are source-level design-rationale \
# prose describing already-implemented internal behavior (verifiable by reading \
# ResourceLeaseManager.acquire/release/release_holder themselves), not a separate \
# cross-module contract needing its own tracked invariant -- same disposition this \
# repo already applies to src/frob/serve/_socketd.py and src/frob/app/_daemon_proxy.py \
# (T-0585/T-1023/T-1093/T-1095)"

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field

from frob.logging import get_logger

_log = get_logger(__name__)

# frob:doc docs/modules/serve.md#resource-leasessemaphores-t-1097
DEFAULT_LEASE_CAPACITY = 1


@dataclass
class _ResourceState:
    """Internal per-resource bookkeeping: `capacity` slots, and the
    ordered list of holder ids currently occupying one."""

    capacity: int
    holders: list[str] = field(default_factory=list)


# frob:doc docs/modules/serve.md#resource-leasessemaphores-t-1097
# frob:tests tests/test_serve_leases.py::TestResourceLeaseManager.test_second_acquire_blocks_until_first_releases kind="unit"  # noqa: E501
# frob:tests tests/test_serve_leases.py::TestResourceLeaseManager.test_release_holder_frees_every_resource_that_holder_held kind="unit"  # noqa: E501
# frob:tests tests/test_serve_leases.py::TestResourceLeaseManager.test_distinct_resources_do_not_contend kind="unit"  # noqa: E501
class ResourceLeaseManager:
    """Daemon-owned arbitrator for named resource leases (T-1097): each
    named resource has a fixed capacity (default `DEFAULT_LEASE_CAPACITY`
    = 1, i.e. an exclusive writer lock, matching `coverage`'s own
    contract); `acquire` blocks the calling thread until a slot is free
    (or `timeout_s` elapses), `release` frees one slot, and `release_
    holder` frees every slot a given holder currently occupies in one
    call -- the operation `_RequestHandler.handle`'s connection-teardown
    path needs, since a single client connection may hold several
    resources' leases at once."""

    def __init__(self) -> None:
        """One manager per daemon process -- `_DaemonServer` constructs
        exactly one and shares it across every connection-handling
        thread, guarded throughout by `self._lock`/`self._condition`."""
        self._lock = threading.Lock()
        self._condition = threading.Condition(self._lock)
        self._resources: dict[str, _ResourceState] = {}

    def _state_for(self, resource: str, capacity: int) -> _ResourceState:
        """The `_ResourceState` for `resource`, creating it (with
        `capacity`) on first mention -- MUST be called with `self._lock`
        already held."""
        state = self._resources.get(resource)
        if state is None:
            state = _ResourceState(capacity=capacity)
            self._resources[resource] = state
        return state

    # frob:doc docs/modules/serve.md#resource-leasessemaphores-t-1097
    def acquire(
        self,
        resource: str,
        holder_id: str,
        *,
        capacity: int = DEFAULT_LEASE_CAPACITY,
        timeout_s: float | None = None,
    ) -> bool:
        """Block `holder_id` until a slot of `resource` (capacity
        `capacity`, only consulted the FIRST time this resource name is
        seen) is free, then occupy it and return `True`; returns `False`
        if `timeout_s` elapses first without ever occupying a slot (the
        caller acquired nothing, holds nothing to release). Re-entrant
        for the SAME holder_id already holding a slot -- calling `acquire`
        again just re-confirms it without consuming a second slot, since
        one JSON-RPC connection making a redundant `frob_lease_acquire`
        call should not deadlock itself waiting for its own held slot."""
        deadline = None if timeout_s is None else time.monotonic() + timeout_s
        with self._condition:
            state = self._state_for(resource, capacity)
            if holder_id in state.holders:
                _log.debug(
                    "serve: leases: %s already held by %s (re-entrant acquire)",
                    resource,
                    holder_id,
                )
                return True

            def _slot_free() -> bool:
                return len(state.holders) < state.capacity

            while not _slot_free():
                remaining = None
                if deadline is not None:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        _log.info(
                            "serve: leases: %s acquire by %s timed out",
                            resource,
                            holder_id,
                        )
                        return False
                if not self._condition.wait(timeout=remaining):
                    if deadline is not None and time.monotonic() >= deadline:
                        _log.info(
                            "serve: leases: %s acquire by %s timed out",
                            resource,
                            holder_id,
                        )
                        return False
            state.holders.append(holder_id)
            _log.info(
                "serve: leases: %s acquired by %s (%d/%d held)",
                resource,
                holder_id,
                len(state.holders),
                state.capacity,
            )
            return True

    # frob:doc docs/modules/serve.md#resource-leasessemaphores-t-1097
    def release(self, resource: str, holder_id: str) -> bool:
        """Free `holder_id`'s slot of `resource` if it holds one,
        notifying any blocked `acquire` waiters -- `False` (a no-op) if
        `holder_id` did not hold `resource`, e.g. a client releasing
        twice or releasing a resource it never acquired."""
        with self._condition:
            state = self._resources.get(resource)
            if state is None or holder_id not in state.holders:
                return False
            state.holders.remove(holder_id)
            _log.info(
                "serve: leases: %s released by %s (%d/%d held)",
                resource,
                holder_id,
                len(state.holders),
                state.capacity,
            )
            self._condition.notify_all()
            return True

    # frob:doc docs/modules/serve.md#resource-leasessemaphores-t-1097
    # frob:tests tests/test_serve_leases.py::TestConnectionCrashReleasesLease.test_closing_connection_without_explicit_release_frees_the_lease kind="unit"  # noqa: E501
    def release_holder(self, holder_id: str) -> list[str]:
        """Free EVERY resource `holder_id` currently holds in one call --
        the connection-teardown primitive (T-1097 acceptance [1]): called
        from `_RequestHandler.handle`'s `finally` block so a crashed or
        disconnected client's leases are freed the moment the daemon
        notices, with no explicit `frob_lease_release` required. Returns
        the resource names actually freed, purely for logging -- an empty
        list (holder held nothing) is not an error."""
        freed: list[str] = []
        with self._condition:
            for name, state in self._resources.items():
                if holder_id in state.holders:
                    state.holders.remove(holder_id)
                    freed.append(name)
            if freed:
                self._condition.notify_all()
        if freed:
            _log.info(
                "serve: leases: connection %s torn down, released %s",
                holder_id,
                freed,
            )
        return freed


__all__ = [
    "DEFAULT_LEASE_CAPACITY",
    "ResourceLeaseManager",
]
