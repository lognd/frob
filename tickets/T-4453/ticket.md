---
id: T-4453
title: 'pydantic serializer warning: Ticket.scope reaches model_dump as a list (corrupt-row
  path bypasses validation)'
state: done
kind: bug
origin: agent
created: '2026-09-12'
priority: medium
parent: null
tier: ticket
sprint: v0.531.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_models.py
- src/frob/tickets/_new*.py
- tests/unit/test_new_ticket_scope_overlap_warning.py
- tests/unit/test_ticket_models*.py
- docs/modules/tickets-data-storage.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/modules/tickets-data-storage.md
  reason: ACCEPTANCE criterion 3 requires documenting that scope normalizes to a tuple;
    the field is documented there, not in docs/modules/tickets.md
  actor: logan
  at: '2026-09-12'
body_changes:
- mode: append
  reason: 'record BUG002 waiver: check-repro flags confirmatory-only evidence because
    the failure only reproduces under -W error::UserWarning, not default pytest config'
  actor: logan
  at: '2026-09-12'
  old_length: 1915
  new_length: 2362
evidence:
- tests/unit/test_new_ticket_scope_overlap_warning.py::TestNonRelativeScopeDoesNotCrash::test_corrupt_row_is_named_loudly_not_silently_coerced
- tests/unit/test_new_ticket_scope_overlap_warning.py::TestNonRelativeScopeDoesNotCrash::test_unrelated_ticket_still_files_despite_one_corrupt_row
- tests/unit/test_new_ticket_scope_overlap_warning.py::TestNonRelativeScopeDoesNotCrash::test_multiple_corrupt_entries_use_plural_wording
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
pytest warnings summary on the macOS leg (CI run 34734529382): UserWarning "Pydantic serializer warnings: PydanticSerializationUnexpectedValue(Expected `tuple[str, ...]` - serialized value may not be as expected [field_name='scope', input_value=[...], input_type=list])" at src/frob/tickets/_models.py:2240 (`data = handler(self)` inside a model serializer), raised by tests/unit/test_new_ticket_scope_overlap_warning.py::TestNonRelativeScopeDoesNotCrash::{test_corrupt_row_is_named_loudly_not_silently_coerced, test_unrelated_ticket_still_files_despite_one_corrupt_row, test_multiple_corrupt_entries_use_plural_wording}. The `scope` field is declared `tuple[str, ...]` but the corrupt-row fixtures inject a plain list, and the model is later serialized with the list still in place, so pydantic v2 warns at dump time. Two defects: (a) a list reaching serialization means the model was constructed with `model_construct`/attribute assignment that bypassed validation, or a validator coerces on read but not on the stored value -- find the exact construction path in src/frob/tickets/_models.py and src/frob/tickets/_new*.py and make `scope` always a tuple by the time the model exists (a `field_validator("scope", mode="before")` that tuples any sequence, or fix the corrupt-row handling to build the Ticket through validation); (b) the tests deliberately feed a corrupt row -- if they must keep a list to exercise the "named loudly" path, assert the warning explicitly with `pytest.warns` or filter it in that test, never repo-wide. ACCEPTANCE: (1) the three node ids run clean under `-W error::UserWarning`; (2) `git grep -n "scope=\[" src/frob` shows no list literal assigned to a Ticket scope; (3) docs/modules/tickets.md (or wherever the Ticket model fields are documented) states scope is normalized to a tuple. Sprint v0.531.0. Per ~/.claude/CLAUDE.md: pydantic v2 conventions in ~/.claude/refs/pydantic.md.



frob:waive BUG002 reason="warning-only defect: the three named tests PASS under default pytest config on both the pre-fix and post-fix commit (no UserWarning-as-error configured), so --check-repro reads them as confirmatory-only; the fix is only observable under -W error::UserWarning (matching the macOS CI leg config described above), where all three FAILED on main with PydanticSerializationError before this change and PASS clean after it"