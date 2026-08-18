---
id: T-2465
title: declare fs.read capability for src/frob/release/_fragments.py in design/frob.strata
  (SELFAUDIT001, from T-2445)
state: done
kind: bug
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- design/frob.strata
- docs/design/registry/capability-via-ratchet.lock.json
- tests/system/test_frob_self_model.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/design/registry/capability-via-ratchet.lock.json
  reason: ratchet ceiling must bump alongside the new fs.read via-list declaration
    in the same diff, per SYS111's own enforced pairing
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/system/test_frob_self_model.py
  reason: narrow regression test proving the fs.read declaration fix, isolated from
    unrelated pre-existing SYS101/GATERULE001 findings the file's other test also
    trips on
  actor: logan
  at: '2026-08-18'
evidence:
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_fragments_module_fs_read_is_declared_not_selfaudit001
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: cae6baf6bd7d50d32162c3f903c41f2c7d4e2f3d
---
T-2445 landed src/frob/release/_fragments.py, which reads changelog.d/*.md fragments via Path.exists()/Path.read_text() (lines ~169, ~294) -- this is an fs.read capability observed by SELFAUDIT001's SYS100 self-audit but not declared for it in design/frob.strata's core node (the may "fs.read" via [...] list around design/frob.strata:406 lists gates/ files; _fragments.py needs adding to whichever via-list covers frob.release, or a new declaration if none currently covers that package).

Measured via 'frob check --json' unscoped after T-2445 landed:
  error SELFAUDIT001 self-audit family SYS100 node=core: capability 'fs.read' observed at src/frob/release/_fragments.py:169 but not declared
  error SELFAUDIT001 self-audit family SYS100 node=core: capability 'fs.read' observed at src/frob/release/_fragments.py:294 but not declared

Two ERROR-severity findings, both attributable to this one file. Not fixed inline by T-2445's own author: design/frob.strata is a trusted-component declaration file outside T-2445's declared scope, and the T-2445 land's own deferred rapid-sweep had not yet (as of this ticket's filing) surfaced it as a filed finding, so filing directly rather than assuming the sweep will catch it.