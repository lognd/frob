"""The T-1686 verification-watermark epic: making landing independent of
synchronously verifying in every profile (docs/modules/tickets.md).

`frob.verify._watermark` (T-1687) is the durable foundation this package
starts from: a persisted, append-only VERIFY QUEUE (one intent record per
land, keyed by commit sha and touched SYMBOL ids) and a persisted
WATERMARK ("main is verified through commit X"). `frob.verify._worker`
(T-1688) is the daemon-side coalescing worker that consumes it: on wake,
verify ONCE at the queue's tip and advance the watermark past every
entry it covers, never once per queued entry. Tier-2/3 attribution and
the profile-to-queue-depth dial are still later leaves this package does
not yet contain.
"""
# frob:waive INV006 preset="split-carried-prose"
# frob:waive TEST003 reason="unit-tested exhaustively via tests/unit/verify/test_watermark.py and tests/unit/verify/test_worker.py; no CLI/subprocess integration entrypoint exists yet -- both T-1687 and T-1688 are data-model/worker-only tickets, not wired into frob.__main__ (that wiring is a later leaf in the T-1686 epic)"  # noqa: E501

from __future__ import annotations

from frob.verify._watermark import (
    SCHEMA_VERSION,
    VerifyQueueEntry,
    Watermark,
    WatermarkError,
    advance_watermark,
    compact_queue,
    load_watermark,
    queue_status,
    record_intent,
)
from frob.verify._worker import (
    DEFAULT_DEBOUNCE_WINDOW_S,
    DEFAULT_PERIODIC_FLOOR_S,
    CoalescingWorker,
    VerifyFn,
    WorkerError,
    WorkerOutcome,
    run_coalesced_verification,
)

__all__ = [
    "DEFAULT_DEBOUNCE_WINDOW_S",
    "DEFAULT_PERIODIC_FLOOR_S",
    "SCHEMA_VERSION",
    "CoalescingWorker",
    "VerifyFn",
    "VerifyQueueEntry",
    "Watermark",
    "WatermarkError",
    "WorkerError",
    "WorkerOutcome",
    "advance_watermark",
    "compact_queue",
    "load_watermark",
    "queue_status",
    "record_intent",
    "run_coalesced_verification",
]
