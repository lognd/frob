---
id: T-1803
title: Detect a frob:waive whose suppressed finding no longer fires, not just an orphaned
  follow_up citation
state: queued
kind: bug
origin: human
created: '2026-08-07'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_waive.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
Two confirmed instances found while working T-1534 (WIRE001
false-positives on autouse pytest fixtures): `frob:waive WIRE001 ...
follow_up="T-1534"` on `tests/test_ticket_land.py::_isolate_from_host_git_config`
and `tests/unit/test_ticket_store.py::_pin_v1_mode_on_bare_tmp_path` both
suppressed a WIRE001 finding that T-1510 had ALREADY made structurally
impossible to fire, before T-1534 itself was ever worked. T-1510 added
`frob.gates._dead_symbols._is_autouse_pytest_fixture`, an exemption
`_new_callable_records` (WIRE001's own search-space construction) applies
BEFORE the case-1 unwired-symbol check ever runs -- so neither waiver had
suppressed anything for as long as T-1510 has been on main. Both were
silent, permanent no-ops: dead weight nobody noticed until an unrelated
ticket (T-1534) happened to investigate the exact symbols they sat on.

This is a DIFFERENT shape from T-1751 (a waiver's `follow_up="T-####"`
citation orphaned because that specific ticket closed without touching
the waived site) -- T-1751 is about the CITATION going stale; this is
about the underlying CONDITION the waiver suppresses going stale. A
waiver can have a perfectly live, open `follow_up` ticket and still be
pure noise, because the gate finding it once suppressed no longer fires
at all under current code -- confirmed here by directly testing the
exemption function against both symbols.

Both classes are instances of the same broader signal: a stale waiver in
the corpus reads as "this is still a known, accepted gap" when it is
not, and (per T-1744's framing) costs a future agent real budget
investigating a condition that was already resolved. T-1763 (closed)
found the same rot at a different granularity: three rules at a 100%
waive rate, 406 waivers against zero real findings.

Work direction (not yet designed in detail): a periodic or dispatch-time
check that, for every `frob:waive RULE reason="..."` in the corpus,
either (a) re-evaluates whether `RULE` still fires at that exact site
under the CURRENT gate implementation (the T-1534 shape -- the
suppressed condition itself is gone), or (b) confirms any cited
`follow_up="T-####"` still names an open ticket (the T-1751 shape --
already partially covered by WIRE002 for WIRE001 specifically, but WIRE002
only checks the follow_up is OPEN, never whether the waived finding
still fires at all). Bonus: report is nearly free for any waiver on a
rule the gate can re-run standalone against the exact (file, line) --
most gates already support point evaluation for `--delta`/incremental
checks.

Filed with T-1534's own two instances as evidence rather than fixing
them silently -- exactly the false-queue-signal class T-1744 exists to
catch, one layer down (in the waiver corpus, not the ticket ledger).
