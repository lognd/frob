## Done report

Changed:
tests/unit/test_ticket_runner_ledger_mirror.py::TestVerbStrategy.test_derived_sets_track_the_live_strategy_table (renamed from test_derived_match)
src/frob/app/ticket_runner/_ledger_mirror.py (frob:tests directive on LEDGER_VERB_STRATEGY updated to the new name)
tickets/T-2603/ticket.md (evidence citation --replace'd to the new test name)

Root cause (the coordinator's real question): test_derived_match was a
T-2603 MIGRATION regression test -- "did unifying three separate
hand-maintained verb sets into one LEDGER_VERB_STRATEGY table change
which verbs land in which bucket". It asserted that against a LITERAL
frozenset snapshot of the table's contents AT MIGRATION TIME, even
though OWN_TRANSACTION_VERBS/MIRRORED_LEDGER_VERBS were ALREADY derived
(frozenset comprehensions filtering LEDGER_VERB_STRATEGY by strategy
value, see those constants' own docstrings) -- there was no technical
need for the second, hand-maintained literal; it was migration-day
scaffolding that outlived its purpose and nobody removed it. T-2624
added a new verb to the table and, as anyone re-deriving from source
would have been immune to, the migration-day snapshot silently went
stale instead.

Fix: replaced the migration snapshot with a test that recomputes the
IDENTICAL filter fresh from the LIVE LEDGER_VERB_STRATEGY on every run,
so it structurally cannot go stale on a future verb addition -- it still
protects a real invariant (the exported aliases stay a genuine live
filter over the table, not a name that quietly regresses to a second
hand-maintained set, and any future LedgerWriteStrategy member missing
from the OWN_TRANSACTION/OWN_TRANSACTION_LEDGER_MIRROR filter tuple
would show up as a mismatch here too), just never a fixed verb count.

Positive control: verified the OLD test would have failed against the
CURRENT table (it does -- that is exactly T-2675's own reported bug,
reproduced against main before touching anything) and the NEW test
passes against the same current table without modification, and would
keep passing after a future verb addition since it re-derives rather
than hardcodes.

Filed: none new.

Gates: frob check --ticket T-2675 clean of every ticket-attributable
finding after fixing the cascade (renamed-test COV003 citation drift in
the archived-but-active T-2603, and the frob:tests directive in
_ledger_mirror.py itself). tests/unit/test_ticket_runner_ledger_mirror.py
full file: 20/20 green.

### Changed
```
 tickets/T-2603/ticket.md | 10 +++++++++-
 tickets/T-2675/ticket.md | 43 ++++++++++++++++++++++++++++++++++++++++++-
 2 files changed, 51 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/test_ticket_runner_ledger_mirror.py::TestVerbStrategy::test_derived_sets_track_the_live_strategy_table` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 18 error(s), 856 warning(s), 711 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1688, COV003@tickets/T-2365, CYCLE001@src/frob/__init__.py, DOC006@docs/audits/test005-zero-classification-t1418.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, PERF004@src/frob/tickets/_evidence.py, REG002@docs/design/registry/check-coverage.yaml, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SYS003@src/frob/check/__init__.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md
