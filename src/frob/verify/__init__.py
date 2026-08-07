"""The T-1686 verification-watermark epic: making landing independent of
synchronously verifying in every profile (docs/modules/tickets.md).

`frob.verify._watermark` (T-1687) is the durable foundation this package
starts from: a persisted, append-only VERIFY QUEUE (one intent record per
land, keyed by commit sha and touched SYMBOL ids) and a persisted
WATERMARK ("main is verified through commit X"). Later leaves in the epic
(the daemon-side coalescing worker, tier-2/tier-3 attribution, the
profile-to-queue-depth dial) build on this record; this package does not
yet contain them.
"""
# frob:waive INV006 preset="split-carried-prose"
# frob:waive TEST003 reason="unit-tested exhaustively via tests/unit/verify/test_watermark.py; no CLI/subprocess integration entrypoint exists yet -- T-1687 is a data-model-only foundation ticket, not wired into frob.__main__ (that wiring is a later leaf in the T-1686 epic)"  # noqa: E501

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

__all__ = [
    "SCHEMA_VERSION",
    "VerifyQueueEntry",
    "Watermark",
    "WatermarkError",
    "advance_watermark",
    "compact_queue",
    "load_watermark",
    "queue_status",
    "record_intent",
]
