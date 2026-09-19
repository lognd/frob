---
id: T-draft-aa0b055b
title: 'DECISION: SF-01 -- what should the SYS/SELFAUDIT family measure so that zero
  fires means clean rather than measures-nothing?'
state: queued
kind: docs
origin: agent
created: '2026-09-19'
priority: high
parent: T-4667
tier: ticket
sprint: v0.536.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: 'Owner records a decision in the body: which option or combination (run the
    self-conformance family less often, re-aim it at what consumers actually report,
    require a per-rule positive control so a zero is provable, or retire rules that
    cannot state what they would catch), and what it changes. No SYS/SELFAUDIT rule
    is re-tuned, re-scoped or retired before that decision is recorded, and any retiring
    option first establishes independently that the rule is not simply un-instrumented.'
  evidence: []
threat: null
component: strata
anchor: false
anchor_reason: null
land_commit: null
---
DECISION TICKET. SF-01 (HIGH). Child of story D (T-4667) under epic T-4662.
NOT implementation work. Do not re-tune, re-scope or retire any SYS/SELFAUDIT
rule until the owner records a decision in this body.

EVIDENCE TABLE ROW, VERBATIM FROM scratchpad/STRATA-FRICTION.md:
| SF-01 | SYS*/SELFAUDIT rules produce essentially zero signal while their model absorbs enormous churn | .frob/telemetry.jsonl: 614,294 rule fires across 82 distinct rule ids, **zero** `SYS*`, `SELFAUDIT001`=1 | 434 commits to design/frob.strata in 60d for 1 finding | HIGH |

FULL EVIDENCE (SF-01 section, verbatim):
Parsing `.frob/telemetry.jsonl` (31,459 rows) and summing every `rule_counts`
map: **614,294 rule fires across 82 distinct rule ids**. Not one id starts with
`SYS`. `SELFAUDIT001` appears exactly **once**. Top fires for contrast:
CPLACE002 124,184; CPLACE001 89,963; TICK014 88,050; DOCARCH001 59,362.

Against that, `git log --oneline --since="60 days ago" -- design/frob.strata` =
**434 commits**; all-time = 452. So >95% of the self-model's lifetime churn
happened in the last 60 days and produced one recorded finding.

79 rule ids of the SYS/SELFAUDIT/REL/PII/THREAT/VMOD/CLAIM families are defined
under `src/frob/strata` + `src/frob/gates/_sys.py`; zero of them appear in
telemetry.

Caveat a fixer must know: the SYS family is a *self-conformance* gate, so "zero
findings" is partly the intended steady state. The friction is the ratio -- the
cost of keeping it at zero (SF-02, SF-04, SF-06) is borne on every land.

WHY THIS IS A DECISION AND NOT INSTRUMENTATION
This ticket was originally filed as instrumentation work (T-4672). The
coordinator and owner have re-classified it: adding telemetry would tell us
WHICH KIND of zero we have, but it would not answer the question the number
actually poses, which is what the family should be measuring in the first place.
Per memory/silent-zero-is-the-dominant-bug-class.md a zero is one of four things
-- clean, could-not-run, nothing-to-measure, or matcher-never-fired -- and
instrumentation can only separate them. Choosing a family that fires when
something is wrong is a design question about the gate's purpose, and it is the
owner's to answer, especially while the module system and grammar are being
rethought.

THE QUESTION
What should the SYS/SELFAUDIT family MEASURE so that a zero means CLEAN rather
than MEASURES-NOTHING?

OPTIONS THE EVIDENCE SUPPORTS

Option 1 -- keep the family as a self-conformance invariant, and accept the zero
as correct, but stop paying for it on every land.
The audit's own caveat supports this: for a self-conformance gate, zero IS the
steady state. Would have to change: WHEN the family runs (a nightly or
pre-release sweep rather than every land), not what it measures. Costs nothing
in coverage and removes the per-land cost that SF-02/SF-04/SF-06 all trace back
to. Does not answer whether the rules would catch anything if they did run.

Option 2 -- re-aim the family at what consumers actually report.
The four consumer-filed SYS defects (SF-14/15/16/17: T-3833, T-3821, T-3832,
T-3825) are all `origin: human`, all from CONSUMER repos, all `priority: medium`,
all parked on milestone v1.1.0. The outside world's experience of SYS is
false positives, not missed findings. Would have to change: what the rules
assert, and the milestone posture that defers every consumer report.

Option 3 -- keep the family, and make the zero provable rather than assumed.
Require a positive control per rule: a planted fixture each rule must report, so
a zero in production is backed by a rule that demonstrably fires. Would have to
change: the test suite and the rule-registration surface (each rule gains a
required fixture). This is the option that makes "zero" a measurement rather
than an absence, and it composes with options 1 and 2 rather than competing.

Option 4 -- retire the rules that cannot state what they would catch.
79 defined rule ids with zero fires is a large surface to carry. Would have to
change: the rule set and the docs. Highest risk: telemetry is the ONLY rule-fire
record available, so a gate path that does not emit telemetry would make a
live rule look dead (see the boundary note below).

MEASUREMENT BOUNDARIES THE OWNER MUST WEIGH
- `.frob/telemetry.jsonl` rule_counts is the only rule-fire record available. If
  a gate path exists that does not emit telemetry, its SYS findings would be
  invisible to this finding entirely. SELFAUDIT001's single recorded fire
  suggests the path IS instrumented, but that is inference, not proof. Any
  option that RETIRES a rule (option 4) must first establish this independently.
- **No one has ever recorded a `check --only sys` timing** -- zero such rows in
  31,459 telemetry entries. T-4672 has been re-scoped to take exactly that one
  measurement and nothing else. Its number is an input to this decision,
  particularly to option 1, so read T-4672's result before deciding.

ACCEPTANCE
Owner records a decision in the body: which option (or combination), and what it
changes.
