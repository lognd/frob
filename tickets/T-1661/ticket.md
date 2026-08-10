---
id: T-1661
title: 'TEST005 remainder (55 findings): successor to T-1657'
state: queued
kind: feature
origin: human
created: '2026-08-06'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- tests/**
- src/frob/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
Successor to T-1657 (itself successor to T-1655/T-1650/T-1273): T-1657's
agent closed a small slice (gates/_fix_engine_shared.py clear_autofix_manifest,
gates/_prework.py record_prework + load_prework, gates/_ratchet.py
load_ratchet_lock + ratchet_enabled_rules, gates/decisions.py load_decisions
-- 6 symbols, 12 new tests, all real OSError/malformed-JSON/bad-TOML/bad-YAML
induced failures asserting the documented Result/None contract, bound via
frob:tests) and must NOT close T-1657 on partial progress per its own body's
standing instruction -- filing this successor instead, per that same
instruction.

Remaining work, last measured on a fresh non-deflated coverage.xml (make
coverage run completed cleanly with 8628 tests passing, coverage.xml copied
from .frob/coverage.partial.xml, no TEST017 finding): 55 TEST005 findings
remain (62 measured at T-1657 start, minus 7 whose branch/line coverage
crossed threshold from this slice's tests).

Remaining breakdown by package, measured via `frob check --only test`
unscoped on the fresh stamp:
app=10, serve=9, arch=8, tickets=5, scaffold=5, refactor=3, testing=3,
gates=9 (down from 14 -- _baseline/_prework/_ratchet/decisions.py closed
this round; _cache_gate, _coverage(load_lock_audit_log),
_exhaustive_handling, _fix_engine_sync, _fix_engine_tier_c, _gate_cache,
_inv006_split_assist remain), strata=2, vet=2, dup=1.

dup's one remaining finding (src/frob/dup/_pipeline/_smt.py, 21.0% line
coverage) involves z3 SMT solver internals -- genuinely harder to reach
with a narrow unit test; may need a dedicated investigation rather than a
quick Err-path test, same note as prior rounds.

Method (carried forward, it worked -- verified again this round):
- Measure UNSCOPED. A --ticket-scoped zero is not a package zero.
- Verify coverage.xml freshness and non-deflation (TEST017) before
  trusting any count; if TEST017 fires, stop and report rather than
  burning down against fiction. Recover from .frob/coverage.partial.xml
  per playbook 6d if the promote-to-committed step is blocked.
- Write tests that would FAIL if the behaviour broke -- induce the real
  failure (OSError, malformed input, missing git ref) and assert the
  documented Result/contract. A test that only executes lines to move a
  percentage is worse than the missing coverage -- it hides the gap
  permanently.
- Bind each test to the symbol it covers with a frob:tests directive,
  node-level, using the path::Class.method dotted form (not pytest's ::
  form) to satisfy DOC007.
- New top-level Test* classes (or free test functions) added to tests/**
  require `frob sys sync-interface` to be re-run before `make coverage` --
  the testsuite node's design/frob.strata interface list enumerates every
  public test symbol by name, and an undeclared one fails
  tests/unit/strata/test_selfconform.py's SYS104 check AND
  tests/system/test_frob_self_model.py's zero-violations check AND
  tests/unit/strata/test_conform_eval_needle.py's needle-gap check --
  all three failed together in this round until `frob sys sync-interface`
  was run and its rewrite of design/frob.strata committed alongside the
  new tests. Run it as a matter of course whenever a test file gains a
  new top-level class or function, not just when a coverage run
  surprises you with these three failures.
- Prioritize `app`/`serve`/`arch` (10/9/8) next -- they are the largest
  remaining clusters and were not touched this round.

Do NOT close this ticket on partial progress. Either drive it to zero or
file a named successor first and say so in the Done report, same as
T-1650/T-1655/T-1657 before it.