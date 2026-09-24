---
id: T-5442
title: 'post-land sweep regression from T-5436: 46 new (rule, file) identit(ies) (ARCH102,
  ARCH104, COV001, COV002)'
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
- .claude/hooks/sync-claude-config.py
- design/frob.strata
- docs/modules/sql.md
- docs/modules/webapp-comply.md
- docs/modules/webapp-seo.md
- docs/modules/webapp-websec-authz.md
- docs/modules/webapp-websec-bounds.md
- docs/modules/webapp-websec-headers-log.md
- docs/modules/webapp-websec-injection.md
- docs/modules/webapp-websec-session.md
- src/frob/gates/_taint_gate.py
- src/frob/lang/_common.py
- src/frob/sql/_extract.py
- src/frob/tickets/_reconcile.py
- src/frob/webapp/_a11y_substrate.py
- src/frob/webapp/_comply_substrate.py
- src/frob/webapp/_seo_substrate.py
- src/frob/webapp/_websec_authz_substrate.py
- src/frob/webapp/_websec_bounds.py
- src/frob/webapp/_websec_sinks.py
- tests/fixtures/webapp/websec2xx/rails_compliant/app/controllers/application_controller.rb
- tests/fixtures/webapp/websec2xx/rails_compliant/config/initializers/session_store.rb
- tests/fixtures/webapp/websec2xx/rails_violating/app/controllers/application_controller.rb
- tests/fixtures/webapp/websec2xx/rails_violating/config/initializers/session_store.rb
- tests/fixtures/webapp/websec4xx/rails/orders_controller.rb
- tests/unit/sql/test_extract.py
- tests/unit/test_webapp_comply_substrate.py
- tests/unit/test_websec_bounds.py
- tests/unit/test_websec_headers_log.py
findings:
- - ARCH102
  - src/frob/webapp/_seo_substrate.py
- - ARCH104
  - src/frob/gates/_taint_gate.py
- - COV001
  - design/frob.strata
- - COV001
  - src/frob/webapp/_seo_substrate.py
- - COV001
  - src/frob/webapp/_websec_authz_substrate.py
- - COV002
  - .claude/hooks/sync-claude-config.py
- - COV002
  - src/frob/lang/_common.py
- - COV002
  - src/frob/webapp/_a11y_substrate.py
- - DOC002
  - src/frob/webapp/_seo_substrate.py
- - DOC002
  - src/frob/webapp/_websec_authz_substrate.py
- - DUP001
  - src/frob/webapp/_seo_substrate.py
- - DUP002
  - src/frob/webapp/_seo_substrate.py
- - DUP002
  - tests/unit/sql/test_extract.py
- - DUP002
  - tests/unit/test_webapp_comply_substrate.py
- - DUP002
  - tests/unit/test_websec_bounds.py
- - DUP002
  - tests/unit/test_websec_headers_log.py
- - INV003
  - docs/modules/sql.md
- - INV003
  - docs/modules/webapp-seo.md
- - INV003
  - docs/modules/webapp-websec-authz.md
- - INV003
  - docs/modules/webapp-websec-bounds.md
- - INV003
  - docs/modules/webapp-websec-headers-log.md
- - INV003
  - docs/modules/webapp-websec-injection.md
- - INV003
  - docs/modules/webapp-websec-session.md
- - LANG002
  - tests/fixtures/webapp/websec2xx/rails_compliant/app/controllers/application_controller.rb
- - LANG002
  - tests/fixtures/webapp/websec2xx/rails_compliant/config/initializers/session_store.rb
- - LANG002
  - tests/fixtures/webapp/websec2xx/rails_violating/app/controllers/application_controller.rb
- - LANG002
  - tests/fixtures/webapp/websec2xx/rails_violating/config/initializers/session_store.rb
- - LANG002
  - tests/fixtures/webapp/websec4xx/rails/orders_controller.rb
- - PERF002
  - src/frob/webapp/_websec_authz_substrate.py
- - PERF002
  - src/frob/webapp/_websec_bounds.py
- - PERF002
  - src/frob/webapp/_websec_sinks.py
- - PERF004
  - src/frob/tickets/_reconcile.py
- - PII012
  - src/frob/webapp/_comply_substrate.py
- - REF002
  - docs/modules/sql.md
- - REF002
  - docs/modules/webapp-comply.md
- - REF002
  - docs/modules/webapp-seo.md
- - REF002
  - docs/modules/webapp-websec-authz.md
- - REF002
  - docs/modules/webapp-websec-session.md
- - SEC110
  - .claude/hooks/pgrep-self-match-guard.py
- - TEST010
  - .claude/hooks/pgrep-self-match-guard.py
- - TODO002
  - tests/unit/test_websec_bounds.py
- - WIRE001
  - src/frob/sql/_extract.py
- - WIRE001
  - src/frob/webapp/_comply_substrate.py
- - WIRE001
  - src/frob/webapp/_seo_substrate.py
- - WIRE001
  - src/frob/webapp/_websec_authz_substrate.py
- - WIRE001
  - tests/unit/test_websec_headers_log.py
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
The deferred post-land unscoped sweep (T-1684) for T-5436 at commit 2644a5021d0d452fbdf8f4549726153e6ca6f7ea found 46 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES, not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). The true per-finding count could not be independently re-measured this run (spawn refused/timeout/unparsable) -- re-run `frob check` unscoped against the file(s) below for the exact count before treating this identity count as a completeness claim.

New (rule, file) identit(ies) filed here:

- ARCH102  src/frob/webapp/_seo_substrate.py
- ARCH104  src/frob/gates/_taint_gate.py
- COV001  design/frob.strata
- COV001  src/frob/webapp/_seo_substrate.py
- COV001  src/frob/webapp/_websec_authz_substrate.py
- COV002  .claude/hooks/sync-claude-config.py
- COV002  src/frob/lang/_common.py
- COV002  src/frob/webapp/_a11y_substrate.py
- DOC002  src/frob/webapp/_seo_substrate.py
- DOC002  src/frob/webapp/_websec_authz_substrate.py
- DUP001  src/frob/webapp/_seo_substrate.py
- DUP002  src/frob/webapp/_seo_substrate.py
- DUP002  tests/unit/sql/test_extract.py
- DUP002  tests/unit/test_webapp_comply_substrate.py
- DUP002  tests/unit/test_websec_bounds.py
- DUP002  tests/unit/test_websec_headers_log.py
- INV003  docs/modules/sql.md
- INV003  docs/modules/webapp-seo.md
- INV003  docs/modules/webapp-websec-authz.md
- INV003  docs/modules/webapp-websec-bounds.md
- INV003  docs/modules/webapp-websec-headers-log.md
- INV003  docs/modules/webapp-websec-injection.md
- INV003  docs/modules/webapp-websec-session.md
- LANG002  tests/fixtures/webapp/websec2xx/rails_compliant/app/controllers/application_controller.rb
- LANG002  tests/fixtures/webapp/websec2xx/rails_compliant/config/initializers/session_store.rb
- LANG002  tests/fixtures/webapp/websec2xx/rails_violating/app/controllers/application_controller.rb
- LANG002  tests/fixtures/webapp/websec2xx/rails_violating/config/initializers/session_store.rb
- LANG002  tests/fixtures/webapp/websec4xx/rails/orders_controller.rb
- PERF002  src/frob/webapp/_websec_authz_substrate.py
- PERF002  src/frob/webapp/_websec_bounds.py
- PERF002  src/frob/webapp/_websec_sinks.py
- PERF004  src/frob/tickets/_reconcile.py
- PII012  src/frob/webapp/_comply_substrate.py
- REF002  docs/modules/sql.md
- REF002  docs/modules/webapp-comply.md
- REF002  docs/modules/webapp-seo.md
- REF002  docs/modules/webapp-websec-authz.md
- REF002  docs/modules/webapp-websec-session.md
- SEC110  .claude/hooks/pgrep-self-match-guard.py
- TEST010  .claude/hooks/pgrep-self-match-guard.py
- TODO002  tests/unit/test_websec_bounds.py
- WIRE001  src/frob/sql/_extract.py
- WIRE001  src/frob/webapp/_comply_substrate.py
- WIRE001  src/frob/webapp/_seo_substrate.py
- WIRE001  src/frob/webapp/_websec_authz_substrate.py
- WIRE001  tests/unit/test_websec_headers_log.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- ARCH102  src/frob/webapp/_seo_substrate.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- ARCH104  src/frob/gates/_taint_gate.py  -> UNATTRIBUTED (3 batch commits' touched symbols all reach this finding); candidate commits: ['e7999285fba19304ea8fe7e30bd6d0dfdb602d67', '5de152f3ce033a1b5fb11cbb6750dd708e5667bb', '28facf8285ca58dc11a3b91b67efa1760f89c403']
- COV001  design/frob.strata  -> attributed to T-5396 (commit 9340c155b0be, already closed/dropped -- filed below) via design/frob.strata::frob.cli
- COV001  src/frob/webapp/_seo_substrate.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV001  src/frob/webapp/_websec_authz_substrate.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  .claude/hooks/sync-claude-config.py  -> attributed to T-5436 (commit 2644a5021d0d, already closed/dropped -- filed below) via .claude/hooks/sync-claude-config.py::MANAGED
- COV002  src/frob/lang/_common.py  -> attributed to T-5394 (commit 7197e857d856, already closed/dropped -- filed below) via src/frob/lang/_common.py::_strip_comment_delims
- COV002  src/frob/webapp/_a11y_substrate.py  -> attributed to T-5323 (commit 5f192b78f5ab, already closed/dropped -- filed below) via src/frob/webapp/_a11y_substrate.py::ElementMatch
- DOC002  src/frob/webapp/_seo_substrate.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DOC002  src/frob/webapp/_websec_authz_substrate.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DUP001  src/frob/webapp/_seo_substrate.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DUP002  src/frob/webapp/_seo_substrate.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DUP002  tests/unit/sql/test_extract.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DUP002  tests/unit/test_webapp_comply_substrate.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DUP002  tests/unit/test_websec_bounds.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DUP002  tests/unit/test_websec_headers_log.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- INV003  docs/modules/sql.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- INV003  docs/modules/webapp-seo.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- INV003  docs/modules/webapp-websec-authz.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- INV003  docs/modules/webapp-websec-bounds.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- INV003  docs/modules/webapp-websec-headers-log.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- INV003  docs/modules/webapp-websec-injection.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- INV003  docs/modules/webapp-websec-session.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- LANG002  tests/fixtures/webapp/websec2xx/rails_compliant/app/controllers/application_controller.rb  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- LANG002  tests/fixtures/webapp/websec2xx/rails_compliant/config/initializers/session_store.rb  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- LANG002  tests/fixtures/webapp/websec2xx/rails_violating/app/controllers/application_controller.rb  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- LANG002  tests/fixtures/webapp/websec2xx/rails_violating/config/initializers/session_store.rb  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- LANG002  tests/fixtures/webapp/websec4xx/rails/orders_controller.rb  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF002  src/frob/webapp/_websec_authz_substrate.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF002  src/frob/webapp/_websec_bounds.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF002  src/frob/webapp/_websec_sinks.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF004  src/frob/tickets/_reconcile.py  -> attributed to T-5292 (commit 2e85de8131bf, already closed/dropped -- filed below) via src/frob/tickets/_reconcile.py::StripStaleFieldsReport
- PII012  src/frob/webapp/_comply_substrate.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- REF002  docs/modules/sql.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- REF002  docs/modules/webapp-comply.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- REF002  docs/modules/webapp-seo.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- REF002  docs/modules/webapp-websec-authz.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- REF002  docs/modules/webapp-websec-session.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- SEC110  .claude/hooks/pgrep-self-match-guard.py  -> attributed to T-5323 (commit 5f192b78f5ab, already closed/dropped -- filed below) via .claude/hooks/pgrep-self-match-guard.py::main
- TEST010  .claude/hooks/pgrep-self-match-guard.py  -> attributed to T-5323 (commit 5f192b78f5ab, already closed/dropped -- filed below) via .claude/hooks/pgrep-self-match-guard.py::main
- TODO002  tests/unit/test_websec_bounds.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- WIRE001  src/frob/sql/_extract.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- WIRE001  src/frob/webapp/_comply_substrate.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- WIRE001  src/frob/webapp/_seo_substrate.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- WIRE001  src/frob/webapp/_websec_authz_substrate.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- WIRE001  tests/unit/test_websec_headers_log.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.