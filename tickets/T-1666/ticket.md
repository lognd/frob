---
id: T-1666
title: Classify and re-waive the 142 OPAQUE001 findings T-1659's symref fix surfaced;
  sweep PERF/PII/SEC005 for the same shape
state: queued
kind: bug
origin: human
created: '2026-08-06'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/_config_external.py
- src/frob/perf/**
- src/frob/gates/_pii_structural/**
- src/frob/gates/_taint_gate.py
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
T-1659 fixed CACHE001 and OPAQUE001's missing Violation.symref (both now
symbol-exact). That symref narrowing surfaced real work this ticket's
scope did not cover fixing:

## OPAQUE001: 142 newly-unwaived findings (166 waived -> 24 waived + 142/143 error)

Before (main, file-scope matching): 0 errors, 166 waived.
After (this ticket's fix, symbol-exact matching): 142-143 errors, 24 waived
(measured via `frob check --only opaque --json`, `gate:OPAQUE` diagnostics:
166 total, severity counter {error: 142, note: 24}).

Breakdown of the 142 unwaived:
- 136 in tests/** -- overwhelmingly literal getattr()/setattr()/eval()-shaped
  fixture STRINGS written as test source text (e.g.
  tests/test_ticket_work_and_land_finish.py: 30, tests/unit/strata: 14,
  tests/unit/test_ticket_runner_land_release.py: 12, tests/test_app.py: 11,
  tests/test_gates.py: 10, and 10+ more files with 1-9 each). These read as
  a genuine rule-level pattern (test fixtures constructing runtime-opaque
  constructs to exercise OTHER gates/features), not attacker-reachable
  production code -- but each needs a real frob:waive with its own reason
  (or the fixture rewritten to avoid the construct), not a blanket
  re-forgive. Recommend triaging by file: most are probably one `frob:waive
  OPAQUE001 reason="test fixture constructing a <rule> litmus, not
  production code"` per fixture function.
- 6 in src/**, all previously covered by ONE waiver each that the file-scope
  fallback let cover multiple sibling functions:
  - src/frob/app/_config_external.py:399,428,445,458,479 -- five
    `_apply_*_fields` helpers (_apply_path_fields/_apply_int_fields/
    _apply_float_fields/_apply_list_fields/_apply_bool_flags). The ONE
    existing waiver above `_apply_string_fields` (line 381) explicitly says
    in its own reason text (T-1424 update) "this waiver now covers every
    `_apply_*_fields` helper below" -- a deliberate multi-site waiver that
    relied on the file-scope fallback this ticket closes. This is a
    GENUINELY ACCEPTABLE pattern (same closed-tuple-of-known-field-names
    rationale applies to every sibling) -- the fix is mechanical: copy the
    same `frob:waive OPAQUE001 reason="..."` comment above each of the 5
    remaining `_apply_*_fields` functions (or extract a single small
    helper they all route the getattr through, if that reads better).
  - src/frob/logging/filter.py:26 -- NOT the same shape. Investigate
    separately (see the dsl.py bug filed alongside this ticket, referenced
    below) -- the existing waiver in `_BelowLevelFilter.__init__` resolves
    to `_BelowLevelFilter.filter` instead, a real comment-binding bug, not
    a multi-site-waiver pattern. Re-verify after that bug is fixed before
    assuming this site still needs its own waiver.

## CACHE001: dormant hole closed, no live waivers existed

T-1659 confirmed CACHE001 currently has 0 live `frob:waive CACHE001`
directives repo-wide, so populating its symref (done) closed a dormant hole
with no immediate unwaived-count consequence. No further action needed here
beyond what T-1659 already landed.

## Not yet swept for the same missing-symref shape (T-1659's own scope note)

`grep -c symref= <file>` presence-only audit (informed, NOT exhaustively
verified per site -- a real per-rule read is still owed):

- PERF001-014 (src/frob/perf/*.py): only `_recursion.py` sets symref today;
  `_advisories.py` (4 Violation sites), `_dup_spawn.py`, `_hotpath_smells.py`,
  `_loop_effects.py`, `_ratchet.py`, `_redundancy.py`, `_rules.py` do not.
  Each of these is a per-function/per-call-site finding by nature (the
  rule names -- duplicate-spawn, hotpath-smell, loop-invariant-effect,
  redundant-computation -- all describe a specific site), so these read as
  the SAME bug shape as CACHE001/OPAQUE001, not file-level-by-design. Needs
  the same live-waiver-population check T-1659 did for OPAQUE001 before
  fixing (a PERF gate promoted to ERROR with an existing waiver population
  could have the same silent-over-forgiveness exposure).
- PII011/PII012 (src/frob/gates/_pii_structural/*.py): none of the 5
  violation-emitting files (`_crosslang.py`, `_emails.py`, `_env_access.py`,
  `_keywords.py`, `_python_fields.py`) set symref today. Each finding is
  about a specific field/env-var/keyword site in a specific file -- same
  shape, needs the same audit.
- SEC005/taint_gate (src/frob/gates/_taint_gate.py): no symref at all,
  described in T-1659's own filing ticket as "per-sink finding" -- same
  shape, needs the same audit.

Scope for this successor: src/frob/app/_config_external.py (5-site
re-waive), src/frob/perf/**, src/frob/gates/_pii_structural/**,
src/frob/gates/_taint_gate.py, plus a representative slice of tests/** for
the 136 OPAQUE001 test-fixture re-waives (do not assume every file needs a
hand-written reason if a shared pattern emerges -- but do not blanket-waive
either, per the playbook's waive-discipline section).