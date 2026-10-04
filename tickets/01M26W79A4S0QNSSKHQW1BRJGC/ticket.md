+++
id = "01M26W79A4S0QNSSKHQW1BRJGC"
title = "Clean land and gates test-suite docstrings of change-narrative (DOCARCH001)"
type = "story"
flavour = "user_story"
category = "done"
outcome = "done"
priority = "medium"
parent = "01M0XNVQXJ1A3FA43N7AA0PAPK"
reporter = "human"
created = "2026-09-11T00:00:00Z"
updated = "2026-09-11T00:00:03Z"
aliases = ["T-4420"]
labels = ["milestone:0.534.0"]
scope = ["tests/gates_suite/test_compliance.py", "tests/gates_suite/test_coverage.py", "tests/gates_suite/test_debt.py", "tests/gates_suite/test_depr003_severity_override.py", "tests/gates_suite/test_doc.py", "tests/gates_suite/test_guard_closure.py", "tests/gates_suite/test_prework.py", "tests/gates_suite/test_protocol.py", "tests/gates_suite/test_run.py", "tests/gates_suite/test_severity_overrides_pin.py", "tests/gates_suite/test_test_gate.py", "tests/gates_suite/test_waive.py", "tests/gates_suite/test_wire.py"]

[[acceptance]]
text = "Given a frob check on tests/gates_suite's 13 files scoped to this ticket (test_sys.py/test_tick.py/test_invariant.py/test_fix_engine.py excluded, leased by T-4622/T-draft-cdd5b1eb/T-4221/T-draft-ede38ca6), when DOCARCH001 is measured, then the count is 0"
bound = true
+++

DOCARCH001 measured tests/ticket_land_suite 42 + tests/gates_suite 40 = 82 findings on a full check today (2026-09-11). Rewrite each flagged docstring to state WHAT the test verifies. Denominator: 82 (land+gates suites).

Re-measured 2026-09-19 (frob check --only docblocks --files <dir> --base dev,
scoped counts from the raw [gate:DOCARCH] lines, not the DOCARCH gate's
own repo-wide summary count which is not file-scoped):

- tests/ticket_land_suite: 42 findings (test_land_core.py 7,
  test_ledger_splice.py 6, test_land_plan.py 5, test_verify_reset.py 3,
  test_release.py 3, test_land_lock.py 3, test_draft.py 3,
  test_dirt_ownership.py 3, test_archive.py 3, test_wip.py 2,
  test_push.py 2, test_waive_deletion.py 1, test_claim_close.py 1).
- tests/gates_suite: 41 findings total, 33 after excluding files leased
  by other in-progress tickets (test_test_gate.py 10, test_coverage.py 6,
  test_run.py 5, test_wire.py 4, test_waive.py 4,
  test_severity_overrides_pin.py 1, test_protocol.py 1, test_prework.py 1,
  test_compliance.py 1; excluded: test_sys.py 2/T-4622,
  test_tick.py 5/T-draft-cdd5b1eb, test_invariant.py 1/T-4221,
  test_fix_engine.py 0-here-but-leased/T-draft-ede38ca6).

Narrowed this ticket (T-4420) to tests/gates_suite's 13 unleased files
(33 findings) as the first cluster. Split tests/ticket_land_suite (42
findings) to child ticket T-draft-7bdec243 (parent T-4420, kind docs)
per the coordinator's per-subdirectory clustering instruction.
