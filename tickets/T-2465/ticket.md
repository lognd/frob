---
id: T-2465
title: declare fs.read capability for src/frob/release/_fragments.py in design/frob.strata
  (SELFAUDIT001, from T-2445)
state: queued
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
T-2445 landed src/frob/release/_fragments.py, which reads changelog.d/*.md fragments via Path.exists()/Path.read_text() (lines ~169, ~294) -- this is an fs.read capability observed by SELFAUDIT001's SYS100 self-audit but not declared for it in design/frob.strata's core node (the may "fs.read" via [...] list around design/frob.strata:406 lists gates/ files; _fragments.py needs adding to whichever via-list covers frob.release, or a new declaration if none currently covers that package).

Measured via 'frob check --json' unscoped after T-2445 landed:
  error SELFAUDIT001 self-audit family SYS100 node=core: capability 'fs.read' observed at src/frob/release/_fragments.py:169 but not declared
  error SELFAUDIT001 self-audit family SYS100 node=core: capability 'fs.read' observed at src/frob/release/_fragments.py:294 but not declared

Two ERROR-severity findings, both attributable to this one file. Not fixed inline by T-2445's own author: design/frob.strata is a trusted-component declaration file outside T-2445's declared scope, and the T-2445 land's own deferred rapid-sweep had not yet (as of this ticket's filing) surfaced it as a filed finding, so filing directly rather than assuming the sweep will catch it.