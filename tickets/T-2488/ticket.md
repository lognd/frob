---
id: T-2488
title: Bump capability-via-ratchet.lock.json ceilings for T-2482/T-2464 (SELFAUDIT001
  SYS111)
state: done
kind: docs
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/design/registry/capability-via-ratchet.lock.json
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: kind
  old_value: bug
  new_value: docs
  reason: data-only ratchet-ceiling JSON bump, no code change -- same kind as T-2460's
    own precedent for this identical class of fix
  actor: logan
  at: '2026-08-18'
evidence:
- cmd:bash /tmp/t2488_verify.sh exit=0 sha256=df7a93730321
kind_history:
- 2026-08-18 bug->docs evidence=0 done_report=yes
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: e60364488d161b64ed4d78ea9e0dfbb2155c8821
---
## Description

SELFAUDIT001/SYS111 fires 6 times: the capability ratchet lock fell
behind 6 already-landed via-list declarations across two tickets that
each declared new capability grants in design/frob.strata but did not
bump docs/design/registry/capability-via-ratchet.lock.json in the same
diff (the same "ratchet fell behind" pattern T-2460 fixed once before).

Traced by diffing design/frob.strata's via-list sets across git history
(git log -S<filename> -- design/frob.strata), not assumed:

- gates::fs.read 47->48: T-2482 added src/frob/gates/_waive_audit_watermark.py
- testsuite::exec 186->188: T-2482 added tests/unit/gates/test_rel001_deferred_bump.py, tests/unit/test_waive_audit_runner.py
- testsuite::fs.read 132->134: T-2482 added tests/unit/test_waive_audit_runner.py, tests/unit/test_waive_audit_watermark.py
- testsuite::fs.write 348->351: T-2482 added tests/unit/gates/test_rel001_deferred_bump.py, tests/unit/test_waive_audit_runner.py, tests/unit/test_waive_audit_watermark.py
- stratamod::net.connect 0->1 (brand-new capability kind, no prior lock entry): T-2482 added src/frob/strata/_threat_catalog_benign.py
- testsuite::net-mutate 0->1 (brand-new capability kind, no prior lock entry): T-2464 added tests/test_capability_registry.py

All six additions are genuine, already-reviewed, reasoned declarations
in already-landed tickets (T-2482's own commit message: "Declare
fs.read/fs.write/exec for T-2467's waive-audit module+tests"; T-2464's
own in-file comment: "TestNetMutateVerbSplit's own fire fixtures
contain real requests.post(/httpx.delete( needle literals, proving the
new net-mutate split actually fires"). Not new scope -- bumping the
stale ceilings to match measured reality, same posture T-2460/T-2407
already established.

## Plan

Edit docs/design/registry/capability-via-ratchet.lock.json: bump the
four existing entries' accepted_count and reason, add two brand-new
entries for stratamod::net.connect and testsuite::net-mutate (both
accepted_count=1, each with its own contributing-file+ticket reason).
Verify SELFAUDIT001/SYS111 clears to zero afterward.