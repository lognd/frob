---
id: T-5449
title: 'post-land sweep regression from an unattributed source (sweep spawned by T-5337):
  29 new (rule, file) identit(ies) (COV001, COV002, COV007, DOC002)'
state: queued
kind: bug
origin: agent
created: '2026-09-23'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .claude/hooks/pgrep-self-match-guard.py
- docs/modules/webapp-a11y-forms-contrast.md
- src/frob/gates/_a11y_gate.py
- src/frob/sql/_extract.py
- src/frob/sql/_orm_rules.py
- src/frob/webapp/_a11y_forms_contrast.py
- src/frob/webapp/_a11y_statement.py
- src/frob/webapp/_comply_substrate.py
- src/frob/webapp/_seo_substrate.py
- src/frob/webapp/_websec_authz_substrate.py
- src/frob/webapp/_websec_bounds.py
- src/frob/webapp/_websec_sinks.py
- tests/unit/sql/test_orm_rules.py
- tests/unit/test_webapp_a11y_forms_contrast.py
- tests/unit/test_webapp_comply_substrate.py
- tests/unit/test_websec_bounds.py
- tests/unit/test_websec_headers_log.py
findings:
- - COV001
  - src/frob/sql/_orm_rules.py
- - COV001
  - src/frob/webapp/_a11y_statement.py
- - COV002
  - .claude/hooks/pgrep-self-match-guard.py
- - COV002
  - src/frob/gates/_a11y_gate.py
- - COV002
  - src/frob/sql/_extract.py
- - COV002
  - src/frob/sql/_orm_rules.py
- - COV002
  - src/frob/webapp/_comply_substrate.py
- - COV002
  - src/frob/webapp/_seo_substrate.py
- - COV002
  - src/frob/webapp/_websec_authz_substrate.py
- - COV002
  - src/frob/webapp/_websec_bounds.py
- - COV002
  - src/frob/webapp/_websec_sinks.py
- - COV002
  - tests/unit/test_webapp_comply_substrate.py
- - COV002
  - tests/unit/test_websec_bounds.py
- - COV002
  - tests/unit/test_websec_headers_log.py
- - COV007
  - src/frob/webapp/_a11y_forms_contrast.py
- - COV007
  - src/frob/webapp/_a11y_statement.py
- - DOC002
  - src/frob/sql/_orm_rules.py
- - DOC002
  - src/frob/webapp/_a11y_forms_contrast.py
- - DOC002
  - src/frob/webapp/_a11y_statement.py
- - DUP001
  - src/frob/webapp/_a11y_forms_contrast.py
- - DUP001
  - tests/unit/test_webapp_a11y_forms_contrast.py
- - DUP002
  - src/frob/webapp/_a11y_forms_contrast.py
- - DUP002
  - tests/unit/sql/test_orm_rules.py
- - DUP002
  - tests/unit/test_webapp_a11y_forms_contrast.py
- - INV003
  - docs/modules/webapp-a11y-forms-contrast.md
- - PII012
  - src/frob/webapp/_a11y_forms_contrast.py
- - REF002
  - docs/modules/webapp-a11y-forms-contrast.md
- - REF002
  - src/frob/webapp/_a11y_forms_contrast.py
- - WIRE001
  - src/frob/sql/_orm_rules.py
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
The deferred post-land unscoped sweep (T-1684) for an unattributed source (sweep spawned by T-5337) at commit 805886c4abb538b257ecd1b4a8287c8bb3825333 found 29 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES, not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). The true per-finding count could not be independently re-measured this run (spawn refused/timeout/unparsable) -- re-run `frob check` unscoped against the file(s) below for the exact count before treating this identity count as a completeness claim.

New (rule, file) identit(ies) filed here:

- COV001  src/frob/sql/_orm_rules.py
- COV001  src/frob/webapp/_a11y_statement.py
- COV002  .claude/hooks/pgrep-self-match-guard.py
- COV002  src/frob/gates/_a11y_gate.py
- COV002  src/frob/sql/_extract.py
- COV002  src/frob/sql/_orm_rules.py
- COV002  src/frob/webapp/_comply_substrate.py
- COV002  src/frob/webapp/_seo_substrate.py
- COV002  src/frob/webapp/_websec_authz_substrate.py
- COV002  src/frob/webapp/_websec_bounds.py
- COV002  src/frob/webapp/_websec_sinks.py
- COV002  tests/unit/test_webapp_comply_substrate.py
- COV002  tests/unit/test_websec_bounds.py
- COV002  tests/unit/test_websec_headers_log.py
- COV007  src/frob/webapp/_a11y_forms_contrast.py
- COV007  src/frob/webapp/_a11y_statement.py
- DOC002  src/frob/sql/_orm_rules.py
- DOC002  src/frob/webapp/_a11y_forms_contrast.py
- DOC002  src/frob/webapp/_a11y_statement.py
- DUP001  src/frob/webapp/_a11y_forms_contrast.py
- DUP001  tests/unit/test_webapp_a11y_forms_contrast.py
- DUP002  src/frob/webapp/_a11y_forms_contrast.py
- DUP002  tests/unit/sql/test_orm_rules.py
- DUP002  tests/unit/test_webapp_a11y_forms_contrast.py
- INV003  docs/modules/webapp-a11y-forms-contrast.md
- PII012  src/frob/webapp/_a11y_forms_contrast.py
- REF002  docs/modules/webapp-a11y-forms-contrast.md
- REF002  src/frob/webapp/_a11y_forms_contrast.py
- WIRE001  src/frob/sql/_orm_rules.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- COV001  src/frob/sql/_orm_rules.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV001  src/frob/webapp/_a11y_statement.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  .claude/hooks/pgrep-self-match-guard.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  src/frob/gates/_a11y_gate.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  src/frob/sql/_extract.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  src/frob/sql/_orm_rules.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  src/frob/webapp/_comply_substrate.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  src/frob/webapp/_seo_substrate.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  src/frob/webapp/_websec_authz_substrate.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  src/frob/webapp/_websec_bounds.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  src/frob/webapp/_websec_sinks.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/test_webapp_comply_substrate.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/test_websec_bounds.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/test_websec_headers_log.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV007  src/frob/webapp/_a11y_forms_contrast.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV007  src/frob/webapp/_a11y_statement.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DOC002  src/frob/sql/_orm_rules.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DOC002  src/frob/webapp/_a11y_forms_contrast.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DOC002  src/frob/webapp/_a11y_statement.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DUP001  src/frob/webapp/_a11y_forms_contrast.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DUP001  tests/unit/test_webapp_a11y_forms_contrast.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DUP002  src/frob/webapp/_a11y_forms_contrast.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DUP002  tests/unit/sql/test_orm_rules.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DUP002  tests/unit/test_webapp_a11y_forms_contrast.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- INV003  docs/modules/webapp-a11y-forms-contrast.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PII012  src/frob/webapp/_a11y_forms_contrast.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- REF002  docs/modules/webapp-a11y-forms-contrast.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- REF002  src/frob/webapp/_a11y_forms_contrast.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- WIRE001  src/frob/sql/_orm_rules.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.