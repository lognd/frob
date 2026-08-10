---
id: T-1974
title: 'Adding one gate rule id needs three hand edits and none is checked before
  the land: DOCENUM001+REG010 regressed the floor twice'
state: done
kind: bug
origin: human
created: '2026-08-10'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_new_gate_rule_acceptance.py
- src/frob/gates/_fix_engine.py
- src/frob/gates/_fix_engine_sync.py
- docs/modules/gates.md
- tests/test_gates.py
- src/frob/gates/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_fix_engine.py
  reason: 'chose fix direction (a) from the ticket''s own preferred order: a Tier-A
    auto-fix (fix_docenum001_enumerates_sync, mirroring REG010''s own fix_reg010_registry_sync)
    resyncs the enumerates members= claim mechanically at land time, so the ORIGINAL
    scope guess (_new_gate_rule_acceptance.py, direction (b)) is not what this change
    touches'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/gates/_fix_engine_sync.py
  reason: 'chose fix direction (a) from the ticket''s own preferred order: a Tier-A
    auto-fix (fix_docenum001_enumerates_sync, mirroring REG010''s own fix_reg010_registry_sync)
    resyncs the enumerates members= claim mechanically at land time, so the ORIGINAL
    scope guess (_new_gate_rule_acceptance.py, direction (b)) is not what this change
    touches'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: docs/modules/gates.md
  reason: 'chose fix direction (a) from the ticket''s own preferred order: a Tier-A
    auto-fix (fix_docenum001_enumerates_sync, mirroring REG010''s own fix_reg010_registry_sync)
    resyncs the enumerates members= claim mechanically at land time, so the ORIGINAL
    scope guess (_new_gate_rule_acceptance.py, direction (b)) is not what this change
    touches'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/test_gates.py
  reason: 'chose fix direction (a) from the ticket''s own preferred order: a Tier-A
    auto-fix (fix_docenum001_enumerates_sync, mirroring REG010''s own fix_reg010_registry_sync)
    resyncs the enumerates members= claim mechanically at land time, so the ORIGINAL
    scope guess (_new_gate_rule_acceptance.py, direction (b)) is not what this change
    touches'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/gates/__init__.py
  reason: '_KNOWN_RULE_FIXABILITY (this file) has its own drift-lock test (TestRuleFixability)
    requiring a DOCENUM001: auto entry paired with the new Tier-A handler'
  actor: logan
  at: '2026-08-10'
evidence:
- tests/test_gates.py::TestFixEngineTierABatch2::test_docenum001_fails_before_fix_and_passes_after
- tests/test_gates.py::TestFixEngineTierABatch2::test_docenum001_already_in_sync_is_a_no_op
- tests/test_gates.py::TestFixEngineTierABatch2::test_tier_a_handlers_dict_covers_every_batch_rule
- tests/test_gates.py::TestRuleFixability::test_checked_in_literal_matches_a_fresh_scan
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
REPEATED-MISTAKE AUDIT (2026-08-10). Adding ONE gate rule id requires
hand-updating at least THREE places. None of them is checked before the
land that adds the rule; each is caught afterwards by a different gate,
as a floor regression on main that then needs its own ticket.

The three places:
  1. `_KNOWN_GATE_RULES` (src/frob/gates/_waive.py) -- the registry
     literal.
  2. `docs/modules/gates.md#rule-catalog` -- the `frob:enumerates`
     member list, enforced by DOCENUM001.
  3. `docs/design/registry/check-coverage.yaml` -- a CHK-GATE-<rule>
     entry, enforced by REG010.

MEASURED, twice in one session, same shape both times:
  - T-1937 registered 8 new ids (BUDGET001, CHECK001, CVEFP001,
    DEPLOY001-003, DERIVED001, SYS109). Its land immediately produced
    DOCENUM001 on docs/modules/gates.md (filed as T-1958) AND REG010 on
    check-coverage.yaml. Both had to be fixed by follow-up tickets.
  - T-1629 registered SYS110. Its land produced the IDENTICAL
    DOCENUM001 (`docs/modules/gates.md:13 -- frob:enumerates ... claims a
    stale member list for 'src/frob/gates/_waive.py::_KNOWN_GATE_RULES'`)
    AND REG010 (filed as T-1972). T-1958 had fixed this exact error
    hours earlier; it recurred on the very next rule addition.

So the floor went 0 -> 1 purely as bookkeeping debt from a land that was
otherwise correct. The author of the rule is not doing anything wrong;
the tool simply does not tell them the other two edits exist until after
they have landed.

THE RULE IS ALREADY WRITTEN DOWN AND DID NOT HELP. Dispatch briefs this
session explicitly told agents "a new gate rule id must be added to
`_KNOWN_GATE_RULES` or the acceptance preflight will not see it", and
that warning was followed -- step 1 was done both times. Steps 2 and 3
were still missed, because nothing names them at the moment of the edit.
Per the standing audit rule: when a written rule is followed and the
failure still happens, the rule was not the fix.

DO NOT FIX IT THIS WAY:
- Do NOT make `_KNOWN_GATE_RULES` a computed expression to keep the doc
  in sync. `frob.tickets._new_gate_rule_acceptance` scrapes that
  literal's SOURCE TEXT (via `git show <rev>:...` plus a regex, not via
  import) for the T-0756 acceptance preflight; a computed expression has
  no literal to scrape and would silently blind that consumer -- the
  exact consumer T-1937 existed to protect.
- Do NOT relax DOCENUM001 or REG010. They are correctly catching real
  staleness; the defect is that they catch it too late.
- Do NOT solve it with a `frob rules sync` verb an author must remember
  to run. Per standing directive, a command requires knowledge of the
  command, and this failure is specifically about not knowing.

FIX DIRECTION, preferred order:
(a) At the moment a new rule id is registered, update all three places
    automatically (the registry entry and the enumerates list are both
    mechanically derivable from the id set).
(b) Failing that, make the ticket-close/land preflight that ALREADY
    detects newly-added rule ids -- `unregistered_rule_ids_in_scope`,
    wired into `_evidence.py`'s done-transition guard by T-1956 --
    also refuse when places 2 and 3 are stale for that id. That hook
    already exists and already fires at the right moment; it currently
    checks only place 1.

(b) is likely the cheap correct answer: the detection point is built,
tested and live, and only its coverage is narrow.

ACCEPTANCE: first test must FAIL before the fix -- register a new rule id
without touching docs/modules/gates.md or check-coverage.yaml, and assert
the close/land refuses naming BOTH stale locations. Then assert a rule id
whose three places are all consistent closes cleanly, and that removing a
rule id is handled symmetrically (no false refusal).

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
