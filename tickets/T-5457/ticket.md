---
id: T-5457
title: 'post-land sweep regression from an unattributed source (sweep spawned by T-5339):
  17 new (rule, file) identit(ies) (COV001, COV002, DOC006, DUP002)'
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
- docs/modules/webapp-a11y-interaction.md
- docs/modules/webapp-websec-deser.md
- src/frob/gates/_sql_explain_obligation.py
- src/frob/webapp/_a11y_forms_contrast.py
- src/frob/webapp/_a11y_statement.py
- src/frob/webapp/_websec_deser.py
- src/frob/webapp/_websec_xss.py
- tests/fixtures/webapp/websec1xx/deser/webesc110_negative/app.py
- tests/fixtures/webapp/websec1xx/deser/webesc110_positive/app.py
- tests/unit/test_webapp_a11y_forms_contrast.py
- tests/unit/test_webapp_a11y_statement.py
- tests/unit/test_websec_deser.py
- tests/unit/test_websec_sinks.py
findings:
- - COV001
  - src/frob/gates/_sql_explain_obligation.py
- - COV002
  - src/frob/webapp/_a11y_forms_contrast.py
- - COV002
  - src/frob/webapp/_a11y_statement.py
- - COV002
  - src/frob/webapp/_websec_xss.py
- - COV002
  - tests/unit/test_webapp_a11y_forms_contrast.py
- - COV002
  - tests/unit/test_webapp_a11y_statement.py
- - COV002
  - tests/unit/test_websec_sinks.py
- - DOC006
  - docs/modules/webapp-a11y-interaction.md
- - DUP002
  - tests/unit/test_websec_deser.py
- - INV003
  - docs/modules/webapp-websec-deser.md
- - OPAQUE001
  - src/frob/gates/_sql_explain_obligation.py
- - OPAQUE001
  - tests/fixtures/webapp/websec1xx/deser/webesc110_negative/app.py
- - OPAQUE001
  - tests/fixtures/webapp/websec1xx/deser/webesc110_positive/app.py
- - OPAQUE001
  - tests/unit/test_websec_deser.py
- - PERF002
  - src/frob/webapp/_websec_deser.py
- - REF002
  - docs/modules/webapp-websec-deser.md
- - WIRE001
  - src/frob/gates/_sql_explain_obligation.py
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
The deferred post-land unscoped sweep (T-1684) for an unattributed source (sweep spawned by T-5339) at commit ce5745c0d28a10ab98b4c5948c224f4bcbbdadab found 17 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES, not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). The true per-finding count could not be independently re-measured this run (spawn refused/timeout/unparsable) -- re-run `frob check` unscoped against the file(s) below for the exact count before treating this identity count as a completeness claim.

New (rule, file) identit(ies) filed here:

- COV001  src/frob/gates/_sql_explain_obligation.py
- COV002  src/frob/webapp/_a11y_forms_contrast.py
- COV002  src/frob/webapp/_a11y_statement.py
- COV002  src/frob/webapp/_websec_xss.py
- COV002  tests/unit/test_webapp_a11y_forms_contrast.py
- COV002  tests/unit/test_webapp_a11y_statement.py
- COV002  tests/unit/test_websec_sinks.py
- DOC006  docs/modules/webapp-a11y-interaction.md
- DUP002  tests/unit/test_websec_deser.py
- INV003  docs/modules/webapp-websec-deser.md
- OPAQUE001  src/frob/gates/_sql_explain_obligation.py
- OPAQUE001  tests/fixtures/webapp/websec1xx/deser/webesc110_negative/app.py
- OPAQUE001  tests/fixtures/webapp/websec1xx/deser/webesc110_positive/app.py
- OPAQUE001  tests/unit/test_websec_deser.py
- PERF002  src/frob/webapp/_websec_deser.py
- REF002  docs/modules/webapp-websec-deser.md
- WIRE001  src/frob/gates/_sql_explain_obligation.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- COV001  src/frob/gates/_sql_explain_obligation.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  src/frob/webapp/_a11y_forms_contrast.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  src/frob/webapp/_a11y_statement.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  src/frob/webapp/_websec_xss.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/test_webapp_a11y_forms_contrast.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/test_webapp_a11y_statement.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/test_websec_sinks.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DOC006  docs/modules/webapp-a11y-interaction.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DUP002  tests/unit/test_websec_deser.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- INV003  docs/modules/webapp-websec-deser.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- OPAQUE001  src/frob/gates/_sql_explain_obligation.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- OPAQUE001  tests/fixtures/webapp/websec1xx/deser/webesc110_negative/app.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- OPAQUE001  tests/fixtures/webapp/websec1xx/deser/webesc110_positive/app.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- OPAQUE001  tests/unit/test_websec_deser.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF002  src/frob/webapp/_websec_deser.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- REF002  docs/modules/webapp-websec-deser.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- WIRE001  src/frob/gates/_sql_explain_obligation.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.