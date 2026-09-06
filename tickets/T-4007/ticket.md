---
id: T-4007
title: The one-way profile auto-ratchet changes gate strictness with no durable record,
  and may have silently stopped coverage-run.json
state: queued
kind: bug
origin: human
created: '2026-09-06'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/config.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Consumer apollo, 2026-09-06 (r12). TWO REPORTS THAT ARE PROBABLY ONE INCIDENT --
establishing whether they are is the first job.

REPORT A -- THE RATCHET FIRED WITH NO TICKET TRAIL:
  "AUTO-RATCHET fired: profile rapid -> standard at repo file count 393 > 300,
   one-way (only `frob profile downgrade` reverts). Loudly logged, by design,
   but it changes gate strictness mid-project with no ticket trail."

REPORT B -- COVERAGE STAMPING STOPPED PRODUCING ITS ARTIFACT:
  "The land recipe's `.frob/coverage-run.json` is no longer produced by
   `frob check --stamp-coverage` (standard profile?); carrying just
   coverage-stamp + coverage-file-cache.json still yields verified=True lands."

THE CONSUMER'S OWN PARENTHETICAL -- "(standard profile?)" -- IS THE HYPOTHESIS TO
TEST FIRST. If the ratchet to standard is what stopped coverage-run.json being
written, then B is a CONSEQUENCE of A and the pair is one incident: an automatic,
one-way strictness change silently altered which artifacts the land recipe can
rely on. Confirm or refute that before treating them separately.

WHAT IS GENUINELY WRONG IN A, and it is not the ratchet itself. Growing
strictness as a project grows is defensible, and they explicitly credit it as
loudly logged and by design. THE DEFECT IS THAT A ONE-WAY, GATE-AFFECTING
DECISION LEAVES NO DURABLE RECORD. A log line scrolls past; the ratchet does not.
Afterwards nobody can answer from the repository: when did strictness change,
what triggered it, what was the file count, who (if anyone) decided. Every other
consequential state change in this system is ticketed or recorded in the ledger
-- this one is not, and it is one-way, which is precisely when a record matters
most.

WHAT TO BUILD FOR A: a durable, in-repo record of the transition -- the trigger,
the measured value, the threshold, and the timestamp. A ticket filed
automatically is one option and fits this repo's conventions; a config/ledger
entry is another. What matters is that it survives the terminal scrollback and
can be found later by someone asking "why did the gates get stricter".

WHAT TO DETERMINE FOR B, and treat this as the higher-severity half if confirmed:
whether `--stamp-coverage` SILENTLY stopped producing coverage-run.json, or
correctly stopped needing it. Note the consumer reports lands still verify True
without it. Both readings are alarming in different ways:
  - If the artifact is still required but silently absent, then verified=True is
    being reached without the evidence it is supposed to rest on -- a silent zero
    in the land proof itself.
  - If it is genuinely no longer needed, then a documented land recipe is stale
    and tells people to carry a file that does nothing.
DO NOT GUESS BETWEEN THESE. Measure which artifacts the standard-profile land
proof actually consumes, and make the answer explicit either way.

RELATED CONTEXT worth carrying: this repo runs RAPID with the auto-ratchet
OVERRIDDEN ([profile] override_ratchet=true, T-1681), and every land here prints
a warning that TEST016, the pre-commit sweep, the baseline worktree and REL001
are OFF on the land path. So we are the repo LEAST likely to notice a
ratchet-related regression through our own use -- the same structural blindness
that hid the hyphenated-scaffold and hardcoded-src/frob defects. Weight the
consumer's report accordingly rather than testing only against our own profile.

MUST-FIRE FIXTURE: a ratchet transition leaves a durable in-repo record naming
trigger, measured value and threshold.
MUST-STAY-QUIET: a repo below the threshold is unaffected and gains no spurious
record.
THIRD FIXTURE: whichever B answer is correct -- either coverage-run.json is
produced under standard, or the land proof demonstrably does not depend on it and
the recipe says so.

ACCEPTANCE
- Whether B is caused by A, answered by measurement.
- A durable record for one-way ratchet transitions.
- The stamp-coverage artifact question resolved explicitly, not left ambiguous.
- All three fixtures committed.