---
id: T-0623
title: 'arch: fallibility checks (ARCH1xx) -- unhandled Result, swallowed exception,
  wrong-signature raise, over-broad except'
state: done
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
blocked_by:
- T-0609
parent: T-0330
tier: ticket
sprint: null
scope:
- src/frob/arch/_fallibility.py
- docs/modules/arch.md
- tests/unit/test_arch.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/arch/_models.py
  reason: extend shared ArchCategory for fallibility checks
  actor: logan
  at: '2026-07-23'
- op: remove
  glob: src/frob/arch/_models.py
  reason: release lease -- T-0623's own _models.py edit already committed; T-0624/T-0625
    need the lease next
  actor: logan
  at: '2026-07-23'
evidence:
- tests/unit/test_arch.py::TestUnhandledResult::test_bare_statement_call_to_result_function_flagged
- tests/unit/test_arch.py::TestUnhandledResult::test_returned_call_to_result_function_not_flagged
- tests/unit/test_arch.py::TestSwallowedException::test_bare_except_with_no_reaction_flagged
- tests/unit/test_arch.py::TestSwallowedException::test_except_with_nearby_log_call_not_flagged
- tests/unit/test_arch.py::TestRecoverableErrorWrongSignature::test_raises_value_error_without_result_signature_flagged
- tests/unit/test_arch.py::TestRecoverableErrorWrongSignature::test_raises_value_error_with_result_signature_not_flagged
- tests/unit/test_arch.py::TestOverBroadExcept::test_bare_except_flagged
- tests/unit/test_arch.py::TestOverBroadExcept::test_specific_except_not_flagged
- tests/unit/test_arch.py::TestOverBroadExcept::test_reraise_with_different_type_loses_context_flagged
- tests/unit/test_arch.py::TestRunFallibilityChecks::test_combines_all_four_checks
designated_repro_test: null
threat: null
component: null
---
unhandled Result: a call known to return typani Result[T,E] (or Rust #[must_use]) used as a bare statement, discarding the value. swallowed exception: bare except: or except Exception: pass with no re-raise/log/return-Err. recoverable-error-wrong-signature: a function raises a clearly-recoverable error (e.g. ValueError on bad user input) but its signature returns T, not Result[T,E]. over-broad except / re-raise-losing-context: except Exception (or bare except) catching more than the call site can name, or a re-raise that drops the original exception/traceback. Acceptance: fixture per sub-check; docs updated.