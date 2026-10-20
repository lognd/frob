+++
id = "01M35RZY82WBGGZPP8KZKBPKZB"
title = "test_dispatch_table_verbs_are_all_accounted_for: points/set/tokens verbs unclassified"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
points = 2
reporter = "human"
created = "2026-09-23T00:00:00Z"
updated = "2026-09-23T00:00:02Z"
aliases = ["T-5378"]
labels = ["milestone:0.534.0"]
scope = ["tests/test_ticket_leases.py"]
+++

CI run 35819358270 (ubuntu/windows); re-verified failing on dev tip 39b89ed091: tests/test_ticket_leases.py::TestLedgerAutoCommitEnumeratedOverDispatchTable::test_dispatch_table_verbs_are_all_accounted_for fails -- the real _ticket_dispatch_table() now has verbs 'points', 'set', 'tokens' (added by T-5132/T-5133-era work) that are not in any of the test's classification sets (_MUTATING_VERB_INVOCATIONS, _READ_ONLY_VERBS, _NEEDS_DEDICATED_FIXTURE, _LEDGER_TRANSACTIONAL_VERBS). File each verb into the correct bucket. T-5280 (done) fixed a related but distinct LEDGER_VERB_STRATEGY gap for points/tokens; this is the separate test-side accounting table in test_ticket_leases.py.
