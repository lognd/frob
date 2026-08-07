## Done report
The duplicate recurred: a later ledger-conflict splice re-introduced an
unmarked `state: queued` T-0169 block into tickets-archive.md (lines
10857-10878) alongside the authoritative `state: done` marked entry.
Removed the stale block; verified 175 `<!-- ticket: -->` markers == 175
`id:` lines (no other unmarked splice artifacts), no duplicate ids within
either ledger, and no cross-ledger id overlap.

To stop this recurring class (it bit 3x this session: this T-0169 dup, the
TICK002 T-draft-1fae8bfb dup, and the recurring splice pattern), added a
real-ledger invariant meta-test, `TestRealLedgerIntegrity::
test_no_duplicate_ids_within_or_across_ledgers`, which parses the raw
`id:` lines of the committed tickets.md + tickets-archive.md (the dict
loaders silently collapse a dup, so it asserts against raw lines) and fails
on any within-file or cross-file duplicate. It is a repo-invariant test
(like TestRealGateGreen), deliberately NOT bound to a src symbol it does
not exercise.

Evidence: tests/test_tickets_collision.py::TestRealLedgerIntegrity::test_no_duplicate_ids_within_or_across_ledgers (passes). ruff/format/ty clean.
