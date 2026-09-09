---
id: T-4347
title: Declare tests/unit/test_land_stranding_t4312.py exec/fs.write capabilities
  in design/frob.strata
state: dropped
kind: docs
origin: human
created: '2026-09-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- design/frob.strata
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
T-4312's new test file (tests/unit/test_land_stranding_t4312.py) spawns git subprocesses (exec) and writes fixture files (fs.write) under a real tmp_path git repo, the same fixture shape tests/unit/test_land_root_resolution.py and siblings already use -- but SELFAUDIT001 flags it as undeclared since design/frob.strata's testsuite node lists exec/fs.write via a narrow per-file allowlist and this is a brand-new file. design/frob.strata is out of T-4312's declared scope (src/frob/tickets/_land.py, src/frob/gates/_wire.py, src/frob/tickets/_evidence.py, tests/unit/test_land_stranding_t4312.py), so T-4312 waives SELFAUDIT001 at each site with this ticket as follow_up rather than editing the shared strata file. Add tests/unit/test_land_stranding_t4312.py to the testsuite node's 'may "exec"' and 'may "fs.write"' via-lists in design/frob.strata (mirroring the existing entries for tests/unit/test_land_root_resolution.py-shaped fixtures) and delete the SELFAUDIT001 waivers this leaves behind.

## Drop reason
- 2026-09-08: moot: T-4312's test file was rewritten to reuse tests/unit/test_land_root_resolution.py's already-declared git-fixture helpers (import, not a fresh copy) and frob.tickets._store.atomic_write in place of raw Path.write_text, so it introduces zero new exec/fs.write capability sites -- no design/frob.strata via-list update needed
