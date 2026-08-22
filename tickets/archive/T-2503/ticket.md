---
id: T-2503
title: 'ambient vs enumerated capability grants: kill the via-list churn without losing
  the guard'
state: done
kind: feature
origin: human
created: '2026-08-18'
priority: high
parent: T-2501
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- design/frob.strata
- src/frob/strata/_effects.py
- tests/unit/strata/test_effects.py
- src/frob/gates/_lexical_selfcheck.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/strata/test_effects.py
  reason: test file already touched with new coverage for the ambient/enumerated split;
    SCOPE002 requires it in scope since _effects.py::check_legacy_capability_aliases's
    frob:tests target lives there
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/gates/_lexical_selfcheck.py
  reason: LEXCHECK001 fires on the new check_ambient_capability_reasons (T-2503) --
    it is legitimately textual (scans .strata source comments, not a resolved code
    symbol), requiring a one-line _ALLOWLIST entry per the gate's own instructions
  actor: logan
  at: '2026-08-18'
evidence:
- tests/unit/strata/test_effects.py::TestAmbientCapabilityReason::test_missing_reason_is_flagged
- tests/unit/strata/test_effects.py::TestAmbientCapabilityReason::test_reason_present_is_silent
- tests/unit/strata/test_effects.py::TestAmbientCapabilityReason::test_enumerated_grant_needs_no_reason
- tests/unit/strata/test_effects.py::TestAmbientVsEnumeratedCapabilitySplit::test_ambient_capability_new_site_produces_no_finding
- tests/unit/strata/test_effects.py::TestAmbientVsEnumeratedCapabilitySplit::test_enumerated_capability_new_site_still_refused
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: a1c49a2a504e0730fbb1afaa0cb3ea83fcdb46b1
---
MEASURED 2026-08-18. The `testsuite` node enumerates ~745 capability
sites across 14 kinds:

    352  fs.write        <- ~zero information: that is every test file
    190  exec            <- ~zero
    134  fs.read         <- ~zero
     23  env
     15  eval
     12  net
      5  env.read
      3  ffi / fetch_url / deserialize
      2  process-control / install-hook
      1  net-mutate / sql   <- ALL of the information is down here

The top three are 91% of the entries and carry no decision content: "a
test suite reads files, writes files, and runs subprocesses" is a
tautology. The bottom rows are worth naming and worth refusing to grow
silently -- WHICH test installs a hook is a real question with real
consequences.

One syntax is doing two jobs. Split it per (node, capability):

    // ambient: expected of every file in the node's code glob.
    // no enumeration, no churn -- but it MUST carry a reason.
    may "fs.write" across "tests/**"
        because "fixtures and tmp trees are how a suite asserts on disk state";
    may "exec" across "tests/**"
        because "the suite's purpose is executing frob under test";

    // exceptional: closed set. a new site is REFUSED until declared.
    may "install-hook" via "tests/test_scaffold.py";
    may "net-mutate"   via "tests/unit/test_capability_registry.py";

THE PROPERTY THAT MUST SURVIVE: a capability kind that is neither ambient
nor enumerated for a node is still a hard finding. Adding a test that
writes a file becomes silent and correct. Adding a test that opens a raw
socket or calls into ffi is still refused until declared. The entire
security value of the current model is preserved.

What is given up: the ability to answer "which test writes to disk",
where the answer is "all of them". Nothing is lost.

The real gain: 190 file names never explained WHY exec is acceptable in
the test suite; they only recorded that it happens. One `because` clause
states the design decision and is reviewable. That is the difference
between a design language and a manifest.

TWO GUARDS, both non-negotiable:
1. `across` REQUIRES a reason. An ambient grant without justification is
   exactly the exemption-that-matches-the-normal-case failure
   (T-1967). The reason is what makes it auditable.
2. Fail-closed kinds become per-node, not global. Today exec/eval/
   install-hook/ffi are fail-closed everywhere (T-2224). Under this
   scheme exec stays fail-closed for gates/core/serve and is
   deliberately ambient for testsuite -- one visible line instead of
   190 diffused ones.

Migration: ~745 enumerated sites -> ~30 enumerated + ~4 ambient. This
removes the three >5KB lines, the merge conflicts they generate, AND the
SELFAUDIT001 ratchet-bump tickets in one change: once fs.write is
ambient there is no site count left to ratchet.

POSITIVE CONTROL, BOTH DIRECTIONS, MANDATORY: a new test file using an
ambient capability must produce NO finding and NO diff; a new test file
using an undeclared exceptional capability (ffi, install-hook) must still
be REFUSED. Without the second half this ticket has removed a guard
rather than a chore.