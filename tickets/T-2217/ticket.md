---
id: T-2217
title: Wire frob.verify._quarantine.retire_unidentifiable_findings into frob verify
  dispose CLI
state: done
kind: feature
origin: human
created: '2026-08-16'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/verify_runner.py
- src/frob/_cli_parsers/_verify.py
- src/frob/app/_config_external.py
- tests/unit/test_app_config_flag_coverage.py
- docs/modules/tickets-verify-sweep.md
- tests/unit/verify/test_verify_runner.py
- src/frob/verify/_quarantine.py
- tests/unit/verify/test_quarantine.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/_cli_parsers/_verify.py
  reason: 'Measured: every existing frob verify dispose flag (--file-ticket, --dismiss,
    --reason, --actor) is registered in src/frob/_cli_parsers/_verify.py''s _add_verify_parser,
    not in verify_runner.py, and forwarded to AppConfig via the _BOOL_FLAGS/_STRING_FIELDS
    allowlists in src/frob/app/_config_external.py (T-1697 marker) -- --retire-unidentifiable
    needs the same two wiring points to be reachable from the CLI at all. src/frob/app/config.py
    is already covered by this ticket''s implicit_scope FEATURE-kind CLI-wiring grant
    (T-0446/T-1848), confirmed via ''frob ticket show T-2217''.'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: src/frob/app/_config_external.py
  reason: 'Measured: every existing frob verify dispose flag (--file-ticket, --dismiss,
    --reason, --actor) is registered in src/frob/_cli_parsers/_verify.py''s _add_verify_parser,
    not in verify_runner.py, and forwarded to AppConfig via the _BOOL_FLAGS/_STRING_FIELDS
    allowlists in src/frob/app/_config_external.py (T-1697 marker) -- --retire-unidentifiable
    needs the same two wiring points to be reachable from the CLI at all. src/frob/app/config.py
    is already covered by this ticket''s implicit_scope FEATURE-kind CLI-wiring grant
    (T-0446/T-1848), confirmed via ''frob ticket show T-2217''.'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: tests/unit/test_app_config_flag_coverage.py
  reason: find_dropped_cli_flags (COV/flag-coverage gate) cross-references src/frob/app/_config_external.py
    against tests/unit/test_app_config_flag_coverage.py -- a new _BOOL_FLAGS entry
    needs that test's own coverage kept in sync. docs/modules/tickets-verify-sweep.md#frob-verify-cli-t-1697
    documents the existing dispose flags this ticket extends. tests/test_verify_dispose.py
    (if present) is the existing CLI-level dispose test file the new flag's own test
    belongs beside.
  actor: logan
  at: '2026-08-16'
- op: add
  glob: docs/modules/tickets-verify-sweep.md
  reason: find_dropped_cli_flags (COV/flag-coverage gate) cross-references src/frob/app/_config_external.py
    against tests/unit/test_app_config_flag_coverage.py -- a new _BOOL_FLAGS entry
    needs that test's own coverage kept in sync. docs/modules/tickets-verify-sweep.md#frob-verify-cli-t-1697
    documents the existing dispose flags this ticket extends. tests/test_verify_dispose.py
    (if present) is the existing CLI-level dispose test file the new flag's own test
    belongs beside.
  actor: logan
  at: '2026-08-16'
- op: add
  glob: tests/test_verify_dispose.py
  reason: find_dropped_cli_flags (COV/flag-coverage gate) cross-references src/frob/app/_config_external.py
    against tests/unit/test_app_config_flag_coverage.py -- a new _BOOL_FLAGS entry
    needs that test's own coverage kept in sync. docs/modules/tickets-verify-sweep.md#frob-verify-cli-t-1697
    documents the existing dispose flags this ticket extends. tests/test_verify_dispose.py
    (if present) is the existing CLI-level dispose test file the new flag's own test
    belongs beside.
  actor: logan
  at: '2026-08-16'
- op: remove
  glob: tests/test_verify_dispose.py
  reason: tests/test_verify_dispose.py does not exist; the real existing dispose CLI
    test home is tests/unit/verify/test_verify_runner.py (confirmed via git grep for
    verify_dispose/_run_dispose across tests/).
  actor: logan
  at: '2026-08-16'
- op: add
  glob: tests/unit/verify/test_verify_runner.py
  reason: tests/test_verify_dispose.py does not exist; the real existing dispose CLI
    test home is tests/unit/verify/test_verify_runner.py (confirmed via git grep for
    verify_dispose/_run_dispose across tests/).
  actor: logan
  at: '2026-08-16'
- op: add
  glob: src/frob/verify/_quarantine.py
  reason: 'frob ticket land refused close: LiveTrackerCited -- two frob:waive WIRE001
    directives cite follow_up=T-2217 (the CLI-wiring gap this ticket exists to close).
    retire_unidentifiable_findings is now genuinely wired to the CLI, so its waiver
    is obsolete and must be removed; _seed_stuck_store''s waiver reason (test-only
    helper) was always independent of this ticket and just needs its stale follow_up
    citation dropped. Land''s own error message is the measurement.'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: tests/unit/verify/test_quarantine.py
  reason: 'frob ticket land refused close: LiveTrackerCited -- two frob:waive WIRE001
    directives cite follow_up=T-2217 (the CLI-wiring gap this ticket exists to close).
    retire_unidentifiable_findings is now genuinely wired to the CLI, so its waiver
    is obsolete and must be removed; _seed_stuck_store''s waiver reason (test-only
    helper) was always independent of this ticket and just needs its stale follow_up
    citation dropped. Land''s own error message is the measurement.'
  actor: logan
  at: '2026-08-16'
evidence:
- tests/unit/verify/test_verify_runner.py::TestDispose::test_retire_unidentifiable_flag_retires_and_clears
- tests/unit/verify/test_verify_runner.py::TestDispose::test_retire_unidentifiable_flag_rejects_combination_with_dismiss
- tests/unit/verify/test_verify_runner.py::TestDispose::test_retire_unidentifiable_flag_still_blocks_on_a_well_formed_sibling
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
T-2207 fixed the core identity-less quarantine finding defect
(producer filter in raise_quarantine, consumer recovery verb
retire_unidentifiable_findings) but could not wire it to the CLI --
src/frob/app/verify_runner.py is outside T-2207's declared scope
(src/frob/verify/_quarantine.py only).

Add a `frob verify dispose --retire-unidentifiable` flag (or similar)
that calls frob.verify._quarantine.retire_unidentifiable_findings
directly, so an operator hitting a stuck identity-less quarantine
record again does not need a Python REPL / ad hoc script to invoke the
recovery verb -- only a direct import currently reaches it.