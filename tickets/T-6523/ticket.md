---
id: T-6523
title: secrets_gate self-check flags its own WEBSEC positive fixtures as real credentials
state: done
kind: bug
origin: agent
created: '2026-09-25'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 0.534.0
flavour: null
due: null
rank: null
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-6523
branch: t-6523
scope:
- tests/fixtures/webapp/websec4xx/rls_llm/webesc417_positive/app.py
- tests/test_secrets_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: tests/fixtures/webapp/websec3xx/debug/webesc316_positive/static/main.js
  reason: 'T-5658 (in-progress) already owns main.js''s specific GH-push-protection
    placeholder fix; making this ticket the complement: exclude tests/fixtures/webapp/
    WEBSEC positive fixtures from the secrets self-check via the test''s existing
    by-path exclusion mechanism instead of editing fixture content.'
  actor: logan
  at: '2026-09-25'
evidence:
- tests/test_secrets_gate.py::TestGateIsGreenOnItself::test_secrets_module_source_is_clean
- tests/test_secrets_gate.py::TestGateIsGreenOnItself::test_this_test_file_is_clean
- tests/test_secrets_gate.py::TestGateIsGreenOnItself::test_repo_is_clean
designated_repro_test: tests/test_secrets_gate.py::TestGateIsGreenOnItself::test_repo_is_clean
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while draining CI run 36173008509 (dev 473cee7656). Reproduces on all
three legs (ubuntu-latest, macos-latest Test step; windows-latest Test step).

FAILED tests/test_secrets_gate.py::TestGateIsGreenOnItself::test_repo_is_clean
secrets_gate found real-looking credentials in the live repo:
- SEC003 tests/fixtures/webapp/websec3xx/debug/webesc316_positive/static/main.js:1
  stripe-secret-live (critical), sk_live_... (34 chars)
- SEC001 tests/fixtures/webapp/websec4xx/rls_llm/webesc417_positive/app.py:8
  openai-legacy (critical), sk-... (23 chars)

These are WEBSEC positive-fixture files (deliberately realistic secrets for
the SEC/WEBSEC gate test suite) that the secrets_gate's own
"is-the-repo-clean" self-check does not know to exempt. They need either a
`frob:secret-fake reason="..."` comment or a placeholder-shaped token so the
self-check gate passes without weakening the WEBSEC fixtures' realism.

Proposed fix: add `frob:secret-fake` markers (or swap in placeholder-tail
tokens) on the two flagged fixture lines.