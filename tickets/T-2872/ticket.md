---
id: T-2872
title: 'Fix COV003: 12 tickets cite renamed test_large_file_fires_large001_warn'
state: queued
kind: bug
origin: human
created: '2026-08-22'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tickets/T-1102
- tickets/T-1651
- tickets/T-1656
- tickets/T-2375
- tickets/T-2822
- tickets/T-2823
- tickets/T-2824
- tickets/T-2825
- tickets/T-2826
- tickets/T-2829
- tickets/T-2830
- tickets/T-2839
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Re-measured 2026-08-22 via unbudgeted 'frob check --json' (gate-summary
present): main carries 12 COV003 findings, all citing the identical
now-dead node id

    tests/test_arch_gate.py::TestArchGateLargeFile::test_large_file_fires_large001_warn

across 12 closed LARGE001-family tickets (T-1102, T-1651, T-1656,
T-2375, T-2822, T-2823, T-2824, T-2825, T-2826, T-2829, T-2830, T-2839).

## Root cause (verified, not assumed)

'git log -S' on the old node id shows exactly one hit besides the
original add: T-2831 ("LARGE001: promote large-file from WARN to
ERROR in _arch.py (T-2375 successor)"). The test was RENAMED in that
land to 'test_large_file_fires_large001_error', in the same class,
same file, same assertion shape (LARGE001 fires on an oversized
production file) -- only the asserted severity changed from WARN to
ERROR, matching the documented, intentional promotion. This is not 12
independent situations: every citing ticket points at the SAME dead
id, and the SAME single successor genuinely proves the same property
each of them relied on (that the LARGE001 gate fires for oversized
files) -- none of them assert anything about WARN specifically as
their own claim; they cite this test as general LARGE001-gate-exists
evidence.

## Disposition

All 12: RENAME. Re-point each ticket's evidence citation from
'test_large_file_fires_large001_warn' to
'test_large_file_fires_large001_error' via
'frob ticket evidence <id> --replace OLD NEW --reason "..."'
(supported path per T-2850 precedent) -- do NOT hand-edit any archived
ticket.md, several of these are archived/done and archived-ticket body
writes have a documented DuplicateId corruption hazard.

Verify with a re-measured 'frob check --json' (unbudgeted,
gate-summary present) showing zero COV003 findings after the 12
replacements, before landing.