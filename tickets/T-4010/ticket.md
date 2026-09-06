---
id: T-4010
title: 'docs/guides/release.md scope closure debt: scoping it pulls in doctor.py/verify_release_ci_status.py
  and cascades'
state: queued
kind: docs
origin: human
created: '2026-09-06'
priority: low
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/guides/release.md
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
Discovered while working T-3980: any ticket that scopes docs/guides/release.md gets 2 pre-existing SCOPE002 findings (doc anchors describing scripts/verify_release_ci_status.py and src/frob/doctor.py symbols, neither in scope). Adding those two files to scope in turn cascades into ~99 further scope-closure warnings (docs/guides/install.md, docs/modules/cli.md, tests/test_doctor.py, tests/unit/test_doctor.py, tests/unit/test_verify_release_ci_status.py) via doctor.py's own extensive doc/test surface. This shared doc file's scope-closure debt is out of proportion for any narrowly-scoped ticket to fix; needs either splitting release.md's Decision sections into per-topic docs, or a scope-closure escape hatch for large shared reference docs. Not fixed by T-3980 (its own scope stayed narrow).