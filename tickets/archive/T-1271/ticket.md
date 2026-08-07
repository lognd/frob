---
id: T-1271
title: 'cli hygiene: no hidden-argument hell, maximally informative output, mined
  from real agent usage'
state: done
kind: ux
origin: human
created: '2026-07-29'
priority: high
parent: T-1238
tier: ticket
sprint: null
scope:
- src/frob/_cli_parsers/__init__.py
- src/frob/app/config.py
- docs/modules/app.md
- tests/test_app_config.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/_cli_parsers/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: remove
  glob: src/frob/app/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: remove
  glob: docs/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: remove
  glob: tests/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/_cli_parsers/__init__.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/app/config.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: docs/modules/app.md
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: tests/test_app_config.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
evidence:
- tests/test_app_config.py::TestEnumFieldValidation::test_invalid_ticket_state_lists_valid_values
- tests/test_app_config.py::TestEnumFieldValidation::test_valid_ticket_state_passes_through
- tests/test_app_config.py::TestEnumFieldValidation::test_none_ticket_state_passes_through
- tests/test_app_config.py::TestEnumFieldValidation::test_invalid_ticket_kind_lists_valid_values
- tests/test_app_config.py::TestEnumFieldValidation::test_invalid_ticket_kind_value_lists_valid_values
- tests/test_app_config.py::TestEnumFieldValidation::test_invalid_ticket_tier_lists_valid_values
- tests/test_app_config.py::TestEnumFieldValidation::test_invalid_ticket_tier_value_lists_valid_values
- tests/test_app_config.py::TestEnumFieldValidation::test_invalid_ticket_priority_level_lists_valid_values
- tests/test_app_config.py::TestEnumFieldValidation::test_invalid_ticket_origin_lists_valid_values
- tests/test_app_config.py::TestEnumFieldValidation::test_invalid_ticket_review_verdict_lists_valid_values
designated_repro_test: null
acceptance:
- text: 'GIVEN any enum-valued flag receives an invalid value THEN the error lists
    every valid value inline (today: frob ticket list --status open yields ''open''
    is not a valid TicketState with no valid-values list)'
  evidence:
  - tests/test_app_config.py::TestEnumFieldValidation::test_invalid_ticket_state_lists_valid_values
  - tests/test_app_config.py::TestEnumFieldValidation::test_valid_ticket_state_passes_through
  - tests/test_app_config.py::TestEnumFieldValidation::test_none_ticket_state_passes_through
  - tests/test_app_config.py::TestEnumFieldValidation::test_invalid_ticket_kind_lists_valid_values
  - tests/test_app_config.py::TestEnumFieldValidation::test_invalid_ticket_kind_value_lists_valid_values
  - tests/test_app_config.py::TestEnumFieldValidation::test_invalid_ticket_tier_lists_valid_values
  - tests/test_app_config.py::TestEnumFieldValidation::test_invalid_ticket_tier_value_lists_valid_values
  - tests/test_app_config.py::TestEnumFieldValidation::test_invalid_ticket_priority_level_lists_valid_values
  - tests/test_app_config.py::TestEnumFieldValidation::test_invalid_ticket_origin_lists_valid_values
  - tests/test_app_config.py::TestEnumFieldValidation::test_invalid_ticket_review_verdict_lists_valid_values
acceptance_amendments:
- op: remove
  index: 4
  old_text: GIVEN the audit lands THEN a short cli-hygiene principles doc exists in
    docs/design/ and a checklist test (or gate rule) verifies new parsers against
    it (every flag help string states its default; no flag silently changes another
    flag's meaning)
  new_text: null
  reason: not delivered by this dispatch; split to main-side follow-up T-1556 (worktree
    draft T-draft-8a96bf8c cannot survive the land preview, land-splice draft-loss
    class)
  actor: logan
  at: '2026-08-05'
- op: remove
  index: 3
  old_text: GIVEN a multi-step workflow (close needs start, done-report, evidence,
    accepts) THEN each refusal names the exact next command AND a single porcelain
    verb exists that sequences the happy path; hidden optional arguments that change
    behavior (e.g. renumber's positional-only contract) are documented in --help with
    examples
  new_text: null
  reason: not delivered by this dispatch; split to main-side follow-up T-1556 (worktree
    draft T-draft-8a96bf8c cannot survive the land preview, land-splice draft-loss
    class)
  actor: logan
  at: '2026-08-05'
- op: remove
  index: 2
  old_text: GIVEN a read-only invocation (check --ticket for review, show, brief)
    THEN it never requires a lease or mutates state -- reviewers repeatedly could
    not re-verify gate claims because check --ticket demands a lease
  new_text: null
  reason: not delivered by this dispatch; split to main-side follow-up T-1556 (worktree
    draft T-draft-8a96bf8c cannot survive the land preview, land-splice draft-loss
    class)
  actor: logan
  at: '2026-08-05'
- op: remove
  index: 1
  old_text: GIVEN a command emits repeated advisory warnings (scope-closure on ticket
    new can flood thousands of lines) THEN they collapse to a counted summary with
    a --verbose escape hatch -- signal is never drowned
  new_text: null
  reason: not delivered by this dispatch; split to main-side follow-up T-1556 (worktree
    draft T-draft-8a96bf8c cannot survive the land preview, land-splice draft-loss
    class)
  actor: logan
  at: '2026-08-05'
threat: null
component: null
---
User directive 2026-07-29: no hidden optional argument hell; intuitive and maximally informative -- no noise, nothing missing; mine what agents ACTUALLY do. Evidence from this drive's own agent/coordinator usage: (1) --status open cryptic enum error; (2) ticket new scope-closure warning floods (5000+ lines in one invocation) drowning the created-id line; (3) frob check --ticket lease requirement blocked all four reviewers from re-verifying gate claims read-only; (4) ticket renumber had no --next and its usage was guessable only from error text; (5) the close dance (start -> done-report -> evidence -> accepts -> close) was discovered by error-chasing across five invocations -- each error WAS informative (good pattern, keep) but no porcelain wraps the sequence; (6) positive examples to preserve: evidence-rejection errors name the cache-refresh remedy, TICK002 names its exact fix command. Method: also mine .frob spawn/telemetry if present and the agent-playbook's accumulated workarounds for further real-usage pain points before designing.