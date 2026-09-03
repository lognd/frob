---
id: T-3715
title: vet hook exits blocking in advisory-only mode
state: in-progress
kind: bug
origin: human
created: '2026-09-03'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/vet/_hook.py
- docs/modules/vet.md
- tests/vet_suite/test_lockfile.py
- src/frob/vet/_allow.py
- src/frob/vet/_registry.py
- src/frob/vet/_typosquat.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/modules/vet.md
  reason: 'SCOPE002 closure: check_package''s frob:doc target, test file, and the
    private helpers it already called before this fix (_load_vet_config, _fetch_publish_date,
    _find_typosquat)'
  actor: logan
  at: '2026-09-03'
- op: add
  glob: tests/vet_suite/test_lockfile.py
  reason: 'SCOPE002 closure: check_package''s frob:doc target, test file, and the
    private helpers it already called before this fix (_load_vet_config, _fetch_publish_date,
    _find_typosquat)'
  actor: logan
  at: '2026-09-03'
- op: add
  glob: src/frob/vet/_allow.py
  reason: 'SCOPE002 closure: check_package''s frob:doc target, test file, and the
    private helpers it already called before this fix (_load_vet_config, _fetch_publish_date,
    _find_typosquat)'
  actor: logan
  at: '2026-09-03'
- op: add
  glob: src/frob/vet/_registry.py
  reason: 'SCOPE002 closure: check_package''s frob:doc target, test file, and the
    private helpers it already called before this fix (_load_vet_config, _fetch_publish_date,
    _find_typosquat)'
  actor: logan
  at: '2026-09-03'
- op: add
  glob: src/frob/vet/_typosquat.py
  reason: 'SCOPE002 closure: check_package''s frob:doc target, test file, and the
    private helpers it already called before this fix (_load_vet_config, _fetch_publish_date,
    _find_typosquat)'
  actor: logan
  at: '2026-09-03'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
apollo FROBLEMS.md 2026-09-03: the vet hook printed 'advisory-only mode' (no [vet] section existed yet) but still exited 2 and blocked the install. Advisory mode that blocks is not advisory; with no [vet]/[vet.allow] config the hook should warn and exit 0.