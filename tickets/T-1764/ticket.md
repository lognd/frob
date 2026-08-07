---
id: T-1764
title: 'Make the per-rule waive-rate a first-class number: 997 waivers against 276
  rules was measured by hand'
state: queued
kind: feature
origin: human
created: '2026-08-07'
priority: high
blocked_by:
- T-1763
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_waive.py
- src/frob/app/check_runner.py
- docs/modules/gates.md
- tests/test_waive_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: 'METHODOLOGICAL CORRECTION (2026-08-07): the coordinator''s original waive-rate
    census was INVALID for diff-scoped rules. It compared waiver counts against live
    findings from a full unscoped ''frob check'' on a clean tree -- but a diff-scoped
    gate (AFFECT001, DUP001, and others) only ever fires on a diff, so 0 findings
    on a clean tree is its EXPECTED signature when the backlog is clean, not evidence
    it is broken. Acting on the raw number would have deleted two working detectors.'
  evidence: []
- text: 'Therefore: the census MUST classify each rule as corpus-wide or diff-scoped
    BEFORE computing a waive-rate, and must compute the diff-scoped rules'' rate over
    diffs where they actually ran -- never over a clean-tree snapshot. A single undifferentiated
    waive-rate column is a metric that produces confidently wrong deletions.'
  evidence: []
- text: _WAIVE004_STRUCTURALLY_UNVERIFIABLE_RULES already documents which rules are
    diff-scoped; read that classification rather than re-deriving it, and report any
    rule it does not cover.
  evidence: []
threat: null
component: null
---
frob has 276 registered gate rules and 997 waiver directives against them
in its OWN source. Nobody could state that number before today; it was
measured by hand with a throwaway script, and it is the single most
informative fact about the tool's calibration.

Measured 2026-08-07 (waivers in `src/frob/**`, live findings from a full
`frob check` on a clean tree):

    RULE          WAIVED   LIVE   WAIVE-RATE
    INV006           338      0         100%
    COV007           124    338          27%
    EXHAUST003       104    273          28%
    PERF004           65    134          33%
    AFFECT001         49      0         100%
    EXHAUST002        43    113          28%
    ARCH103           25     52          32%
    ARCH001           23     48          32%
    DUP001            19      0         100%
    ARCH102           14     31          31%

Six rules are waived more often than they are obeyed. Three enforce
nothing at all.

THE PRINCIPLE THIS MAKES ENFORCEABLE: **a rule waived more often than it
is obeyed is not a rule, it is a tax.** An imprecise detector produces
false positives; false positives demand escape hatches; escape hatches
acquire flags and become verbs. That loop is why this CLI has 60
top-level verbs and 39 ticket subverbs, and why `frob ticket scope-ack`
exists as a four-flag command whose only purpose is silencing a warning
that nobody ever acts on (TICK009 has reported the same 4 outstanding
scope-breadth nudges all day while scopes were narrowed BY HAND).

Sprawl is the symptom. Detector imprecision is the disease.

WANTED: make the waive-rate a first-class, continuously-visible number so
this never again requires a hand-rolled script.

1. `frob check --census` (name negotiable; fold into the CLI regrouping
   in T-1567..T-1571 rather than adding a 61st top-level verb -- do not
   let the fix for sprawl add sprawl). For every registered rule: times
   fired, times waived, waive-rate, and the count of waivers whose
   `follow_up` names a closed ticket (a dead waiver).
2. Report DEAD WAIVERS explicitly: a directive suppressing a rule that no
   longer fires anywhere. Those are pure decay -- they read as live
   suppressions of live rules, so a reader assumes both still matter.
3. A rule's waive-rate crossing a threshold should itself be a finding
   against the RULE, not the code. Start it as a warning with the number
   in the message; do not make it blocking until the top offenders are
   dealt with, or it will fire on day one and be waived, which would be
   the joke writing itself.

EXPLICITLY NOT WANTED: a new suppression mechanism, a new verb outside
the regrouping, or a dashboard. The output is a table and a threshold.

Sequencing note: T-1763 (INV006/AFFECT001/DUP001, the three 100% rules)
should land FIRST. It removes 406 of the 997 waivers, which changes every
number in this table -- measuring after that lands gives a truer baseline
than measuring now. Do not run the census as a one-off before it; build
the standing capability so it can be re-run.

Related: T-1567..T-1571 (CLI regrouping) should be sequenced AFTER this.
Regrouping cruft yields organised cruft; the census tells us how much of
the surface is load-bearing before anyone rearranges it.