---
id: T-1594
title: AppConfig.ticket_kind_value validation conflicts with _kind()'s own strict-refusal
state: done
kind: bug
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/config.py
- src/frob/app/ticket_runner/**
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_ticket_evidence.py::TestKindCliInvalidKind::test_invalid_kind_refused
designated_repro_test: null
threat: null
component: null
---
tests/test_ticket_evidence.py::TestKindCliInvalidKind::test_invalid_kind_refused
expects AppConfig(ticket_kind_value="not-a-real-kind") to construct
successfully and _kind() (src/frob/app/ticket_runner/_mutate.py) to be the
one that refuses via a clean SystemExit, per _kind()'s own docstring ("no
validation is re-derived here... kind is validated strictly against the
real TicketKind enum inside TicketKind(...)").

tests/test_app_config.py::TestEnumFieldValidation::test_invalid_ticket_kind_value_lists_valid_values
expects the OPPOSITE: AppConfig(ticket_kind_value="nope") itself raises a
pydantic ValidationError, via the _check_ticket_kind_value field_validator
in src/frob/app/config.py.

These are mutually exclusive for the exact same field/value shape -- one
of them is always failing on main today (confirmed: test_app_config.py's
version currently passes in isolation, test_ticket_evidence.py's version
currently fails in isolation, both independent of xdist/worker ordering).
This was surfaced while investigating T-1591 (shared-state pollution) but
is NOT a pollution bug -- it reproduces deterministically regardless of
run order, so it does not belong in that ticket's fix. Needs a design
decision: either _check_ticket_kind_value should be removed/loosened (so
_kind() owns 100% of ticket_kind_value validation, matching its own
docstring and test_ticket_evidence.py's expectation) and
test_app_config.py's test updated to match, or
test_ticket_evidence.py::test_invalid_kind_refused should be updated to
expect the ValidationError at AppConfig construction instead of a
downstream SystemExit. Filed rather than guessed at under T-1591's own
scope (tests/**, src/frob/lang/**, src/frob/serve/**, src/frob/app/**
-- app/config.py IS technically in scope, but resolving which side is
"correct" is a design call this ticket's own charter (shared-state
pollution) does not cover).