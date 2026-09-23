---
id: T-4735
title: 'Ledger cut-over: direct tickets/*/ticket.md access outside _store_api.py is
  an ARCH finding, ratcheted and burned to zero'
state: queued
kind: feature
origin: human
created: '2026-09-19'
priority: critical
blocked_by:
- T-4657
parent: T-4652
tier: ticket
sprint: null
runs_last: false
milestone: 0.535.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_store.py
- tests/unit/test_ledger_cutover_ratchet.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: Given a frob module outside src/frob/tickets/_store_api.py, when it reads
    or writes a tickets/<id>/ticket.md path directly, then `frob check` reports an
    ARCH finding against it.
  evidence: []
- text: 'POSITIVE CONTROL: a planted direct open() of a tickets/<id>/ticket.md inside
    a tickets module is reported RED by `frob check`. The test plants the call, asserts
    the finding, and removes it. It FAILS on dev today (nothing reports such a call)
    and passes after this leaf.'
  evidence: []
- text: Given the ratchet, when this leaf closes, then the counted direct-access sites
    are ZERO and the old access paths are deleted from the tree, not merely unused
    -- proven by the ratchet lock file reading 0 and by the deletion appearing in
    the diff.
  evidence: []
- text: Given the cut-over, when the existing ticket test suite runs, then it passes
    unchanged -- the file format and CLI are frozen contract.
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
LEDGER cut-over leaf (story T-4652), owner-approved amendment 2026-09-19. ~3 points.

T-4657 builds the seam (src/frob/tickets/_store_api.py). This leaf CLOSES it: every direct
tickets/<id>/ticket.md read or write outside _store_api.py becomes an ARCH finding,
ratcheted at today's count and burned to zero, and the old access paths are DELETED rather
than left as a second way in.

A seam with two doors is not a seam. Until the old paths are gone, the ledger boundary is a
convention and the coupling grows back.

Method: ratchet-today-burn-to-zero, the same posture the repo already uses for its other
arch ratchets. Record the starting count in the done report. Log every removed access site.
