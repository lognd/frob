---
id: T-1364
title: Consider an explicit partial-stamp marker for coverage gates (T-1363 follow-up)
state: done
kind: docs
origin: human
created: '2026-07-31'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_coverage.py
- src/frob/gates/__init__.py
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/gates.md
  reason: T-1364's deliverable is a documented decision (docs-kind ticket) recording
    why the partial-stamp marker was considered and deferred
  actor: logan
  at: '2026-08-01'
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
- tests/test_gates.py::TestCoverageLoad::test_write_coverage_lock_refuses_downward_ratchet
- tests/test_gates.py::TestCoverageLoad::test_write_coverage_lock_allow_decrease_overrides_ratchet
designated_repro_test: null
threat: null
component: null
---
T-1363 fixed the two concrete data-integrity bugs (a failed `make coverage` run
promoting bad data into `coverage.xml`/`.frob/coverage-stamp`, and
`frob-coverage.lock.json` ratcheting downward from bad data) by choosing the
simpler of the two designs the ticket offered: NEVER promote a failed/partial
run's data at all, rather than promoting it with an explicit "partial" marker
for gates to disclose against.

This is sufficient for every realistic case reached in practice: as long as
SOME earlier good stamp/lock exists, a failed run now leaves it completely
untouched, and TEST006 already discloses a genuinely missing stamp
(`_test006_missing`) as a real violation rather than silent success -- so the
bootstrap case (no stamp has ever existed, and the very first `make coverage`
run also fails) already reads as "no data" rather than "false clean", which
was the acceptance criterion's real intent.

NOT built (disclosed, not silently dropped): an explicit `"partial": true`
marker on `.frob/coverage-stamp` plus TEST005/TEST006 wording that
distinguishes "stamp missing" from "stamp exists but was computed from a
partial run" for the specific case where a partial run's data is judged worth
keeping over nothing. T-1363's Done report chose "keep nothing" over "keep and
mark partial" for the first cut; if a future incident shows losing ANY partial
signal is worse than the disclosed-missing-stamp status quo, revisit this
ticket to add the explicit partial-stamp representation.