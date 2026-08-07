"""The T-1686 verification-watermark epic: making landing independent of
synchronously verifying in every profile (docs/modules/tickets.md).

`frob.verify._watermark` (T-1687) is the durable foundation this package
starts from: a persisted, append-only VERIFY QUEUE (one intent record per
land, keyed by commit sha and touched SYMBOL ids) and a persisted
WATERMARK ("main is verified through commit X"). `frob.verify._worker`
(T-1688) is the daemon-side coalescing worker that consumes it: on wake,
verify ONCE at the queue's tip and advance the watermark past every
entry it covers, never once per queued entry. `frob.verify._attribution`
(T-1690) is the tier-2 leaf: given a red batch's findings and the durable
queue entries that batch covers, decide which commit's touched symbol set
graph-reaches each finding -- exactly one reaching commit attributes,
zero or more than one is UNATTRIBUTED (a first-class outcome, never a
newest-commit tiebreak). `frob.verify._backpressure` (T-1692) bounds the
unverified window by DEPTH and AGE, either sufficient to trip, and blocks
the land at the ceiling rather than failing it -- actively draining the
queue to pay back the deferred cost rather than passively waiting. The
profile-to-queue-depth dial (collapsing `fortress`/`standard`/`rapid`
into one mechanism, T-1686's own "payoff" framing) is still a later leaf
this package does not yet contain.
"""
# frob:waive INV006 preset="split-carried-prose"
# frob:waive TEST003 reason="unit-tested exhaustively via tests/unit/verify/test_watermark.py, tests/unit/verify/test_worker.py, tests/unit/verify/test_attribution.py, and tests/unit/verify/test_backpressure.py; no CLI/subprocess integration entrypoint exists yet -- T-1687/T-1688/T-1690/T-1692 are data-model/worker/attribution/backpressure-only tickets, not wired into frob.__main__ (that wiring is a later leaf in the T-1686 epic)"  # noqa: E501

from __future__ import annotations

from frob.verify._attribution import (
    Attribution,
    AttributionError,
    attribute_batch,
)
from frob.verify._backpressure import (
    BackpressureCeilings,
    BackpressureError,
    BackpressureStatus,
    block_until_watermark_advances,
    ceilings_for_profile,
    current_status,
)
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
    "Attribution",
    "AttributionError",
    "BackpressureCeilings",
    "BackpressureError",
    "BackpressureStatus",
    "CoalescingWorker",
    "VerifyFn",
    "VerifyQueueEntry",
    "Watermark",
    "WatermarkError",
    "WorkerError",
    "WorkerOutcome",
    "advance_watermark",
    "attribute_batch",
    "block_until_watermark_advances",
    "ceilings_for_profile",
    "compact_queue",
    "current_status",
    "load_watermark",
    "queue_status",
    "record_intent",
    "run_coalesced_verification",
]
