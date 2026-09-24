---
id: T-5440
title: 'Post-land sweep residue 2026-09-23_2032: ARCH102:src/frob/webapp/_seo_substrate.py
  ARCH104:src/frob/gates/_taint_gate.py COV001:design/frob.strata COV001:src/frob/webapp/_seo_substr'
state: done
kind: bug
origin: human
created: '2026-09-23'
priority: medium
parent: null
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
worktree: /home/logan/projects/frob/.claude/worktrees/t-5440
branch: t-5440
scope:
- .claude/hooks/sync-claude-config.py
- src/frob/lang/_common.py
- src/frob/tickets/_reconcile.py
- .claude/hooks/pgrep-self-match-guard.py
- docs/guides/claude-hooks.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: .claude/hooks/sync-claude-config.py
  reason: 'in-scope subset of the post-land sweep residue: COV002/PERF004/SEC110/TEST010
    on non-webapp/non-sql files; ARCH104:_taint_gate.py held by live T-5372, deferred;
    remaining findings are inside src/frob/webapp/**, src/frob/sql/**, tests/fixtures/webapp/**,
    docs/modules/webapp-*.md, docs/modules/sql.md, out of touch-scope per standing
    brief -- handed off'
  actor: logan
  at: '2026-09-24'
- op: add
  glob: src/frob/lang/_common.py
  reason: 'in-scope subset of the post-land sweep residue: COV002/PERF004/SEC110/TEST010
    on non-webapp/non-sql files; ARCH104:_taint_gate.py held by live T-5372, deferred;
    remaining findings are inside src/frob/webapp/**, src/frob/sql/**, tests/fixtures/webapp/**,
    docs/modules/webapp-*.md, docs/modules/sql.md, out of touch-scope per standing
    brief -- handed off'
  actor: logan
  at: '2026-09-24'
- op: add
  glob: src/frob/tickets/_reconcile.py
  reason: 'in-scope subset of the post-land sweep residue: COV002/PERF004/SEC110/TEST010
    on non-webapp/non-sql files; ARCH104:_taint_gate.py held by live T-5372, deferred;
    remaining findings are inside src/frob/webapp/**, src/frob/sql/**, tests/fixtures/webapp/**,
    docs/modules/webapp-*.md, docs/modules/sql.md, out of touch-scope per standing
    brief -- handed off'
  actor: logan
  at: '2026-09-24'
- op: add
  glob: .claude/hooks/pgrep-self-match-guard.py
  reason: 'in-scope subset of the post-land sweep residue: COV002/PERF004/SEC110/TEST010
    on non-webapp/non-sql files; ARCH104:_taint_gate.py held by live T-5372, deferred;
    remaining findings are inside src/frob/webapp/**, src/frob/sql/**, tests/fixtures/webapp/**,
    docs/modules/webapp-*.md, docs/modules/sql.md, out of touch-scope per standing
    brief -- handed off'
  actor: logan
  at: '2026-09-24'
- op: add
  glob: docs/guides/claude-hooks.md
  reason: doc anchor closure for pgrep-self-match-guard.py/sync-claude-config.py symbols
  actor: logan
  at: '2026-09-24'
triage_changes:
- field: milestone
  old_value: null
  new_value: 0.534.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-23'
- field: points
  old_value: null
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
- field: points
  old_value: '5'
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-24'
body_changes:
- mode: append
  reason: gate-directive-only fix, no repro test possible per T-4561 precedent
  actor: logan
  at: '2026-09-24'
  old_length: 2300
  new_length: 2870
evidence:
- tests/test_hook_pgrep_self_match_guard.py::test_self_matching_polls_are_denied
- tests/test_hook_pgrep_self_match_guard.py::test_non_self_matching_recipes_stay_quiet
- tests/test_ticket_reconcile.py::TestReconcileStaleHold::test_dry_run_reports_but_does_not_requeue
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

frob:waive BUG002 reason="the defects fixed here (PERF004/SEC110/TEST010) are all gate-directive/waiver-annotation changes on lines the fix itself only comments above -- no runtime program behavior changed, so no repro test can genuinely fail at dev and pass at the fix; each was instead independently re-measured with a family-scoped frob check (--only pii_structural --only test, and --only perf) before and after the fix, confirming the finding fires at dev and is gone (waived/moved, per rule) at HEAD, the same shape T-4561's identical waiver already established"