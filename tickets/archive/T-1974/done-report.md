## Done report

Adding a gate rule id needed three hand edits (_KNOWN_GATE_RULES,
docs/modules/gates.md's frob:enumerates member list, check-coverage.yaml's
CHK-GATE-<rule> entry), and only the first was checked before land. REG010
already self-heals check-coverage.yaml via a Tier-A auto-fix
(fix_reg010_registry_sync); the gates.md enumerates list had no
equivalent, and regressed the unscoped floor twice on the identical
anchor in one session (T-1937 -> T-1958, T-1629's SYS110).

Chose fix direction (a) from the ticket's own preferred order: a new
Tier-A auto-fix, fix_docenum001_enumerates_sync (src/frob/gates/
_fix_engine_sync.py), reuses frob.gates._docenum's own AST resolution
(_extract_members/_parse_symref/_site_from_origin -- the same functions
DOCENUM001's detector calls) to recompute a frob:enumerates edge's real
member set and rewrite the doc's members="..." attribute in place, the
same posture fix_reg010_registry_sync already uses for its own derived
artifact. Registered in TIER_A_HANDLERS (src/frob/gates/_fix_engine.py)
so it runs automatically at frob ticket land's pre-merge Tier-A fix
phase, same as REG010 -- no command to remember, no new manual step.
Covers every frob:enumerates edge in the graph, not only the gates.md
anchor that motivated it.

Split fix_docenum001_enumerates_sync's per-edge resync logic into
_docenum001_resync_edge after ARCH001 flagged the first draft at 77
lines (60 threshold); waived the per-edge sorted() call under PERF004
(each edge's own target member set, nothing to hoist across edges).
Registered the new rule in two drift-locked literals the test suite
checks against a fresh scan: TIER_A_HANDLERS (test_tier_a_handlers_
dict_covers_every_batch_rule) and _KNOWN_RULE_FIXABILITY
(test_checked_in_literal_matches_a_fresh_scan, src/frob/gates/
__init__.py).

Fixture proof (T-0756 acceptance shape): test_docenum001_fails_before_
fix_and_passes_after builds a stale frob:enumerates edge, asserts
DOCENUM001 fires (FAILS) before the fix, runs
fix_docenum001_enumerates_sync, asserts the doc's members= line was
rewritten, then re-runs docenum001_gate against a corrected snapshot and
asserts it PASSES (clean). test_docenum001_already_in_sync_is_a_no_op
covers the idempotent case.

### Changed
```
 docs/modules/gates.md              |  20 ++++--
 rapid-debt.jsonl                   |   4 ++
 src/frob/gates/__init__.py         |   1 +
 src/frob/gates/_fix_engine.py      |   8 ++-
 src/frob/gates/_fix_engine_sync.py | 132 ++++++++++++++++++++++++++++++++++++-
 tests/test_gates.py                | 106 +++++++++++++++++++++++++++++
 tickets/T-1972/ticket.md           |  10 ++-
 tickets/T-1974/ticket.md           |  55 +++++++++++++++-
 8 files changed, 326 insertions(+), 10 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestFixEngineTierABatch2::test_docenum001_fails_before_fix_and_passes_after` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineTierABatch2::test_docenum001_already_in_sync_is_a_no_op` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineTierABatch2::test_tier_a_handlers_dict_covers_every_batch_rule` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestRuleFixability::test_checked_in_literal_matches_a_fresh_scan` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 6 error(s), 1707 warning(s), 709 waived
- error-findings: ARCH001@src/frob/tickets/_land.py, ARCH001@src/frob/tickets/_scope.py, COV001@src/frob/tickets/_scope.py, F401@/home/logan/projects/frob/.claude/worktrees/rule-bookkeeping/tests/unit/test_tickets_evidence_only_scope.py, PRE001@tickets/T-1974, TEST001@src/frob/tickets/_scope.py
