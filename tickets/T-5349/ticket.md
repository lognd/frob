---
id: T-5349
title: 'WEBSEC session/CSRF substrate: normalized SessionConfig reader'
state: done
kind: feature
origin: human
created: '2026-09-22'
priority: high
blocked_by:
- T-5302
parent: T-5142
tier: ticket
sprint: null
runs_last: false
milestone: 0.534.0
points: 5
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/webapp/_websec_session_config.py
- tests/fixtures/webapp/websec2xx/**
- docs/modules/webapp-websec-session.md
- tests/unit/test_webapp_websec_session_config.py
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/modules/webapp-websec-session.md
  reason: own family doc file, cited by frob:doc, siblings write their own docs/modules/webapp-<family>.md
    per WEBSEC fan-out brief
  actor: logan
  at: '2026-09-23'
- op: add
  glob: tests/unit/test_webapp_websec_session_config.py
  reason: unit test binding frob:tests evidence for read_session_config, per playbook
    step 2
  actor: logan
  at: '2026-09-23'
- op: add
  glob: design/frob.strata
  reason: declare src/frob/webapp/_websec_session_config.py fs.read site (config file
    reads) in core node via-list, SELFAUDIT001
  actor: logan
  at: '2026-09-23'
triage_changes:
- field: points
  old_value: null
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
- field: points
  old_value: '3'
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
- field: points
  old_value: '3'
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
- field: points
  old_value: '3'
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
- field: points
  old_value: '3'
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
- field: points
  old_value: '3'
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
- field: points
  old_value: '3'
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
- field: points
  old_value: '3'
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
- field: points
  old_value: '3'
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
evidence:
- tests/unit/test_webapp_websec_session_config.py::test_django_compliant_reads_secure_posture
- tests/unit/test_webapp_websec_session_config.py::test_django_violating_reads_insecure_posture
- tests/unit/test_webapp_websec_session_config.py::test_flask_compliant_reads_secure_posture
- tests/unit/test_webapp_websec_session_config.py::test_flask_violating_reads_insecure_posture
- tests/unit/test_webapp_websec_session_config.py::test_express_compliant_reads_secure_posture
- tests/unit/test_webapp_websec_session_config.py::test_express_violating_reads_insecure_posture
- tests/unit/test_webapp_websec_session_config.py::test_rails_compliant_reads_secure_posture
- tests/unit/test_webapp_websec_session_config.py::test_rails_violating_reads_insecure_posture
- tests/unit/test_webapp_websec_session_config.py::test_missing_config_file_is_err
- tests/unit/test_webapp_websec_session_config.py::test_unsupported_framework_is_err
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-5349
branch: t-5349
---
Framework-specific config-file parse (Django settings.py AST for MIDDLEWARE/SESSION_COOKIE_*; Flask app-factory AST for SESSION_COOKIE_*/app.config[...]; Express app.use(session(...)) call-argument AST; Rails config/initializers/session_store.rb + protect_from_forgery AST) producing one normalized SessionConfig model (secure/httponly/samesite/csrf_middleware_present/idle_timeout/absolute_timeout) every rule below reads instead of re-parsing. Fixture: one config fixture per framework, compliant and violating variants.