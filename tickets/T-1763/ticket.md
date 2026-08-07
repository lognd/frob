---
id: T-1763
title: 'INV006/AFFECT001/DUP001 have a 100% waive rate: 406 waivers, zero findings
  -- make them symbolic or delete them'
state: done
kind: bug
origin: human
created: '2026-08-07'
priority: critical
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_inv.py
- src/frob/gates/_waive.py
- docs/modules/gates.md
- tests/test_waive_gate.py
- src/frob/gates/_inv006_split_assist.py
- src/frob/gates/invariants.py
- src/frob/gates/_fix_engine_tier_c.py
- tests/test_gates_fix_engine.py
- src/**
- strata-core/src/**
- frob-core/src/**
- tests/**
- docs/**
- design/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_inv006_split_assist.py
  reason: corpus-wide INV006/AFFECT001/DUP001 measurement + INV006 deletion requires
    touching the gate's split-assist helper, its Tier-A auto-fix handler, and their
    tests -- the ticket's own 4-file scope did not name any of these
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/gates/invariants.py
  reason: corpus-wide INV006/AFFECT001/DUP001 measurement + INV006 deletion requires
    touching the gate's split-assist helper, its Tier-A auto-fix handler, and their
    tests -- the ticket's own 4-file scope did not name any of these
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/gates/_fix_engine_tier_c.py
  reason: corpus-wide INV006/AFFECT001/DUP001 measurement + INV006 deletion requires
    touching the gate's split-assist helper, its Tier-A auto-fix handler, and their
    tests -- the ticket's own 4-file scope did not name any of these
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tests/test_gates_fix_engine.py
  reason: corpus-wide INV006/AFFECT001/DUP001 measurement + INV006 deletion requires
    touching the gate's split-assist helper, its Tier-A auto-fix handler, and their
    tests -- the ticket's own 4-file scope did not name any of these
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tests/test_waive_gate.py
  reason: corpus-wide INV006/AFFECT001/DUP001 measurement + INV006 deletion requires
    touching the gate's split-assist helper, its Tier-A auto-fix handler, and their
    tests -- the ticket's own 4-file scope did not name any of these
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/**
  reason: INV006 deletion requires sweeping ~349 frob:waive INV006 directives spread
    across nearly every module in src/strata-core/frob-core/tests, plus the doc/registry
    updates -- a corpus-wide mechanical removal genuinely needs this breadth; not
    a scope-creep, the task IS this broad by construction
  actor: logan
  at: '2026-08-07'
- op: add
  glob: strata-core/src/**
  reason: INV006 deletion requires sweeping ~349 frob:waive INV006 directives spread
    across nearly every module in src/strata-core/frob-core/tests, plus the doc/registry
    updates -- a corpus-wide mechanical removal genuinely needs this breadth; not
    a scope-creep, the task IS this broad by construction
  actor: logan
  at: '2026-08-07'
- op: add
  glob: frob-core/src/**
  reason: INV006 deletion requires sweeping ~349 frob:waive INV006 directives spread
    across nearly every module in src/strata-core/frob-core/tests, plus the doc/registry
    updates -- a corpus-wide mechanical removal genuinely needs this breadth; not
    a scope-creep, the task IS this broad by construction
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tests/**
  reason: INV006 deletion requires sweeping ~349 frob:waive INV006 directives spread
    across nearly every module in src/strata-core/frob-core/tests, plus the doc/registry
    updates -- a corpus-wide mechanical removal genuinely needs this breadth; not
    a scope-creep, the task IS this broad by construction
  actor: logan
  at: '2026-08-07'
- op: add
  glob: docs/**
  reason: INV006 deletion requires sweeping ~349 frob:waive INV006 directives spread
    across nearly every module in src/strata-core/frob-core/tests, plus the doc/registry
    updates -- a corpus-wide mechanical removal genuinely needs this breadth; not
    a scope-creep, the task IS this broad by construction
  actor: logan
  at: '2026-08-07'
- op: add
  glob: design/**
  reason: INV006 deletion requires sweeping ~349 frob:waive INV006 directives spread
    across nearly every module in src/strata-core/frob-core/tests, plus the doc/registry
    updates -- a corpus-wide mechanical removal genuinely needs this breadth; not
    a scope-creep, the task IS this broad by construction
  actor: logan
  at: '2026-08-07'
evidence:
- tests/test_gates.py::TestTestGate::test_waive004_exempts_a_diff_scoped_rule
- tests/test_gates.py::TestFmt001Gate::test_directive_run_over_limit_flagged
- tests/test_gates.py::TestFmt001Gate::test_untouched_line_not_flagged
- tests/test_gates.py::TestFixEngineTierABatch2::test_fmt001_wraps_overlong_directive_line_and_reverifies_clean
- tests/test_gates.py::TestInv003Gate::test_exclusivity_claim_without_marker_warns
designated_repro_test: null
threat: null
component: null
---
Measured on frob's own source, 2026-08-07:

    RULE        WAIVED   LIVE   WAIVE-RATE
    INV006         338      0         100%
    AFFECT001       49      0         100%
    DUP001          19      0         100%

INV006 has **338 waiver directives and zero live findings**. It has never
produced an unwaived finding in this codebase. It is 34% of frob's entire
suppression corpus (997 waivers across 28 rules) and it enforces nothing.

Each of those 338 is a hand-written prose justification that a person had
to compose, a reviewer had to read, and that now has to be maintained
through every refactor. That is the cost. The benefit is zero findings.

WHY IT MISFIRES. INV006 flags "exclusivity/normative claims" -- the words
`never`, `only`, `always` -- appearing in docstrings and comments. But
those words appear constantly in ordinary descriptive prose about
implemented behaviour, which is exactly what a good docstring contains.
The waiver reasons say so, near-verbatim, 338 times: "describes this
module's own implemented branching, verifiable by reading the code it
annotates -- not a separate cross-module contract needing a tracked
invariant."

It is a LEXICAL rule standing in for a SEMANTIC question. The question it
wants to ask is "does this module make a cross-module contract that no
tracked invariant covers?" The question it actually asks is "does this
text contain the word 'never'?" Today it fired on a waiver reason
EXPLAINING a previous INV006 misfire (T-1640, landed), which is the rule
consuming its own output as input.

DECIDE, then implement. Two honest options, and the ticket wants a
reasoned choice, not a hedge:

(a) MAKE IT SYMBOLIC. Fire only where a normative claim is attached to a
    declared cross-module surface -- an exported symbol's contract, a
    `frob:invariant` anchor's subject -- and never on narrative prose
    about a module's own internals. This is the same move T-1626 made for
    capability detection and T-1627 for `via`: replace the needle with a
    resolved symbol.

(b) DELETE IT. `frob:invariant`/INV001/INV002 already exist to bind real
    invariants to real evidence. If INV006's only demonstrated effect is
    338 waivers, the honest conclusion may be that the tracked-invariant
    mechanism is sufficient and this detector adds nothing but paperwork.

If (a): the acceptance bar is that it fires on a REAL uncovered
cross-module contract in this repo. If a symbolic INV006 still produces
zero findings after recalibration, that is evidence for (b) -- report it
and take (b).

Either way, SWEEP THE 338 WAIVERS in the same change. A rule that stops
firing leaves 338 dead directives behind, and a dead waiver is worse than
none: it reads as a live suppression of a live rule, so the next reader
assumes both still matter. Removing them is most of the value of this
ticket.

Do AFFECT001 (49 waivers, 0 findings) and DUP001 (19, 0) in the same
pass -- identical shape, same decision procedure, same sweep. Total
removal if all three go: 406 of 997 waivers, 41% of the suppression
corpus, with no loss of enforcement because none of the three is
currently enforcing anything.

Report the before/after waiver count and the live-finding count for each
rule. Those two numbers are the deliverable.