---
id: T-draft-95a6b834
title: 'Post-land sweep residue 2026-09-23_2032: ARCH102:src/frob/webapp/_seo_substrate.py
  ARCH104:src/frob/gates/_taint_gate.py COV001:design/frob.strata COV001:src/frob/webapp/_seo_substr'
state: queued
kind: bug
origin: human
created: '2026-09-23'
priority: medium
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
Findings raised by a post-land sweep and disposed against this ticket by the coordinator's runner to keep the quarantine clear. Fix each in scope:
ARCH102:src/frob/webapp/_seo_substrate.py
ARCH104:src/frob/gates/_taint_gate.py
COV001:design/frob.strata
COV001:src/frob/webapp/_seo_substrate.py
COV001:src/frob/webapp/_websec_authz_substrate.py
COV002:.claude/hooks/sync-claude-config.py
COV002:src/frob/lang/_common.py
COV002:src/frob/webapp/_a11y_substrate.py
DOC002:src/frob/webapp/_seo_substrate.py
DOC002:src/frob/webapp/_websec_authz_substrate.py
DUP001:src/frob/webapp/_seo_substrate.py
DUP002:src/frob/webapp/_seo_substrate.py
DUP002:tests/unit/sql/test_extract.py
DUP002:tests/unit/test_webapp_comply_substrate.py
DUP002:tests/unit/test_websec_bounds.py
DUP002:tests/unit/test_websec_headers_log.py
INV003:docs/modules/sql.md
INV003:docs/modules/webapp-seo.md
INV003:docs/modules/webapp-websec-authz.md
INV003:docs/modules/webapp-websec-bounds.md
INV003:docs/modules/webapp-websec-headers-log.md
INV003:docs/modules/webapp-websec-injection.md
INV003:docs/modules/webapp-websec-session.md
LANG002:tests/fixtures/webapp/websec2xx/rails_compliant/app/controllers/application_controller.rb
LANG002:tests/fixtures/webapp/websec2xx/rails_compliant/config/initializers/session_store.rb
LANG002:tests/fixtures/webapp/websec2xx/rails_violating/app/controllers/application_controller.rb
LANG002:tests/fixtures/webapp/websec2xx/rails_violating/config/initializers/session_store.rb
LANG002:tests/fixtures/webapp/websec4xx/rails/orders_controller.rb
PERF002:src/frob/webapp/_websec_authz_substrate.py
PERF002:src/frob/webapp/_websec_bounds.py
PERF002:src/frob/webapp/_websec_sinks.py
PERF004:src/frob/tickets/_reconcile.py
PII012:src/frob/webapp/_comply_substrate.py
REF002:docs/modules/sql.md
REF002:docs/modules/webapp-comply.md
REF002:docs/modules/webapp-seo.md
REF002:docs/modules/webapp-websec-authz.md
REF002:docs/modules/webapp-websec-session.md
SEC110:.claude/hooks/pgrep-self-match-guard.py
TEST010:.claude/hooks/pgrep-self-match-guard.py
TODO002:tests/unit/test_websec_bounds.py
WIRE001:src/frob/sql/_extract.py
WIRE001:src/frob/webapp/_comply_substrate.py
WIRE001:src/frob/webapp/_seo_substrate.py
WIRE001:src/frob/webapp/_websec_authz_substrate.py
WIRE001:tests/unit/test_websec_headers_log.py