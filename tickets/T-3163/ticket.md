---
id: T-3163
title: 'T-1036 ledger-splice regression under T-3121 disposable-stage: concurrent
  sibling write can silently drop the just-landed ticket''s own record'
state: queued
kind: bug
origin: human
created: '2026-08-27'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_land_squash.py
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
MEASURED 2026-08-27, while fixing T-3144's stale test-infra (tests/test_ticket_land.py::TestSquashSpliceLedgerChurn::test_concurrent_write_between_squash_and_splice_survives_land).

That test's own monkeypatch was stale (patched _land_squash_mod.run_argv,
but T-3121's disposable-stage flip moved the actual `git merge --squash`
call into _land_compose's own module-level run_argv, called directly
from _land.py -- the old patch target never fired the test's injection
hook at all). After retargeting the patch to _land_compose_mod.run_argv
(the genuinely correct call site) and fixing a second, related test-infra
gap (the forked child inherits the parent test process's os.environ,
which by fork time already carries FROB_WORKTREE set by land()'s own
in-process evidence re-verify -- popped in the child to mirror a real
independent process), the test's land() call itself now succeeds
(result.is_ok), but the FINAL ledger on root after land contains ONLY
the concurrent sibling's own new ticket -- the just-landed ticket's OWN
record (finalized as result.danger_ok.final_id) is completely absent
from load_all(repo).danger_ok, not merely stale.

This is exactly the class of defect T-1036 was filed to prevent (a
concurrent single-ticket write racing the land window must never silently
clobber ledger content), just manifesting as the INVERSE of the original
symptom: instead of the concurrent write being discarded, the just-landed
ticket's own entry is discarded and the concurrent write survives alone.

REPRO: fix the test's monkeypatch target as described above and run
tests/test_ticket_land.py::TestSquashSpliceLedgerChurn::test_concurrent_write_between_squash_and_splice_survives_land
-- landed.danger_ok contains only the sibling id, result.danger_ok.final_id
(the original ticket) raises KeyError.

HYPOTHESIS (unconfirmed, needs investigation): the concurrent sibling's own
new_ticket() call, once it acquires the ticket ledger lock after land()
releases it, may read/merge against a STALE in-memory or on-disk base
snapshot of root's tickets.md that predates the squash-fold's CAS
publish, then writes back a REPLACEMENT tickets.md rather than an
appending merge -- losing the freshly-published squash content. This
needs tracing through new_ticket's own ledger-write path and/or the
splice/fold pipeline (_squash_and_splice_ledger_v2 under
merge_already_composed=True) to confirm.

NOT fixed by T-3144: T-3144's scope is tests/test_ticket_land.py only, and
this is a genuine production correctness bug (silent ledger data loss)
requiring its own investigation and fix in src/frob/tickets/_land_squash.py
and/or wherever new_ticket's ledger merge lives -- out of proportion for a
test-file ticket to absorb.
