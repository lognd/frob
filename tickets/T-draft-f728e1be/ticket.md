---
id: T-draft-f728e1be
title: 'WEBSEC316 fixture: placeholder key must not match GitHub push-protection detectors'
state: in-progress
kind: docs
origin: human
created: '2026-09-24'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: v0.534.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-draft-f728e1be
branch: t-draft-f728e1be
scope:
- tests/fixtures/webapp/websec3xx/debug/webesc316_positive/static/main.js
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: kind
  old_value: bug
  new_value: docs
  reason: fixture placeholder-text change only, no production logic changed -- BUG002/BUG003's
    mutation-evidence requirement for kind=bug does not apply to a text-only fixture
    swap; closest fit is a docs/fixture-content correction
  actor: logan
  at: '2026-09-24'
evidence:
- tests/unit/test_websec_debug_config.py::test_websec_debug_config_findings_fixture[webesc316_positive-WEBSEC316-True]
kind_history:
- 2026-09-24 bug->docs evidence=1 done_report=yes
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-5329's WEBSEC316 positive fixture (tests/fixtures/webapp/websec3xx/debug/webesc316_positive/static/main.js) contains a string shaped like a real Stripe live secret key (sk_live_ + 24+ alphanumeric-only trailing chars), which GitHub push protection blocks on every push of dev (commit 8ff633a0). Change the placeholder to something WEBSEC316's own _SECRET_ASSIGNMENT_RE in src/frob/webapp/_websec_debug_config.py still reports (>=16 char quoted value) but GitHub's Stripe detector does not: keep the sk_live_ prefix but use fewer than 24 trailing characters AND include an underscore in the trailing portion (the regex already permits underscores in the captured value, so no regex change is needed). Keep the positive control firing (test_websec_debug_config_findings_fixture[webesc316_positive-WEBSEC316-True] must still pass).