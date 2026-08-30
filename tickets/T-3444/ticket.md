---
id: T-3444
title: 'REF001 missing tickets-archive.md exemption: T-3249 fixed tickets.md, sibling
  ledger file still fails clean'
state: queued
kind: bug
origin: agent
created: '2026-08-29'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_refs.py
- tests/test_refs_gate.py
- tests/test_ticket_work_and_land_finish.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_ticket_work_and_land_finish.py
  reason: the T-3442 xfail(strict=True) this ticket must remove lives here
  actor: logan
  at: '2026-08-29'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED locally (T-3442 investigation, 2026-08-30): tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish::test_cli_land_invoked_with_root_equal_to_worktree_still_verifies fails deterministically because the T-1514 pre-commit unscoped sweep (now actually measurable against T-3135's warm-sweep-stage, where it used to report "unmeasurable" on a cold disposable stage and silently skip) finds a genuine new REF001 finding: tickets-archive.md has no inbound references from any other tracked file -- likely dead or silently unreachable.

ROOT CAUSE: src/frob/gates/_refs.py's _DEFAULT_ROOT_MANIFEST_EXEMPT frozenset exempts root tickets.md from REF001 (T-3249: ledger-v1's own universal, exactly-one-per-repo ticket ledger, read only by frob ticket/frob check tooling -- never referenced from other tracked source files ... a plain frob-enabled project's root tickets.md failed REF001 on first clean run), but does NOT exempt its sibling ledger file tickets-archive.md, which _land_squash.py's T-0959 splice creates/updates in the SAME commit the first time any ticket in a project completes. This is the exact same "clean project fails clean" shape T-3249 fixed for tickets.md, just missing the second ledger file.

IMPACT: any frob-enabled project's first frob ticket land that completes a ticket (thus spliced into tickets-archive.md) trips REF001 on tickets-archive.md, which the pre-commit sweep's Tier-A auto-fix cannot resolve (it's a structural "add tickets-archive.md to the same exemption list" fix, not a per-file annotation) -- so land refuses it as a new, unresolvable finding.

FIX: add "tickets-archive.md" to _DEFAULT_ROOT_MANIFEST_EXEMPT in src/frob/gates/_refs.py, alongside "tickets.md", with a comment mirroring T-3249's. Add/extend a REF001 test (see tests/test_refs_gate.py's existing T-3249 coverage for tickets.md) asserting tickets-archive.md is exempt the same way.

Filed while working T-3442 (out of scope for that ticket -- T-3442's scope does not include src/frob/gates/_refs.py). T-3442's own affected test currently fails on this REF001 finding and cannot be made to pass without this fix landing first; do not treat that as T-3442's own defect.
