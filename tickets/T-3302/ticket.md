---
id: T-3302
title: Land-only gates (T-2114 frob:tests, ARCH001, CrossTicketLeakage) never run
  at check/close, and dry-run does not predict them
state: queued
kind: bug
origin: human
created: '2026-08-28'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_verify.py
- src/frob/app/ticket_runner/_land_cmd.py
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
REPORTED FROM REAL CONSUMER USE (../diax FROBLEMS.md F-032, F-051).

ROOT CAUSE: `frob check --ticket` / `frob ticket close` and `frob ticket
land` do not run the same rule set. At least three rule families were
observed to fire ONLY at land, never during the gate loop or at close:
  - T-2114 source-side `# frob:tests` directives (land wants a directive
    ABOVE each new public symbol's def; check/close were satisfied by
    test-side `# frob:tests src/...::Sym` bindings alone) -- F-032, hit on
    two different tickets (T-0045, T-0027).
  - ARCH001 "now N lines, past threshold" -- F-051, hit on T-0024, whose
    `frob check --ticket` read 0 errors.
  - CrossTicketLeakage on the coverage lock -- F-051, hit on T-0016.

F-051 also reports that `frob ticket land --dry-run` PASSED on T-0045 and
then the real land failed for the same reason -- so dry-run is not even a
reliable predictor of this gap today; either fix needs to close that too.

COST: each occurrence is a full agent round-trip after review -- work judged
done, reviewed, and only then bounced back by a rule nobody ran until the
last possible step.

WHAT NOT TO DO: do not just widen `frob check --ticket`'s rule set to
include every land-only rule unconditionally -- some of these may be
deliberately land-only because they are expensive or need full-repo state
only available post-merge (confirm which, if any, before assuming all four
belong in the everyday gate loop). Do not fix this by weakening the land-time
rules to match check's laxer view either (e.g. accepting test-side-only
frob:tests bindings at land) -- if the land-time rule is the intentionally
stricter one, the fix is to surface it EARLIER, not water it down.

WHAT TO BUILD:
  1. For each of the three rule families, determine WHY it is land-only
     today (a genuine post-merge-state dependency, or simply "the check that
     `close`/`--ticket` runs is a narrower preflight that was never updated
     to include it"). State the answer per rule in the Done report.
  2. Wherever the answer is "no real dependency, just never wired in", add
     it to the set `frob check --ticket` (or at minimum `frob ticket close`)
     runs, so a ticket that closes clean is actually landable.
  3. Fix `land --dry-run` to genuinely predict these -- F-051's report that
     dry-run passed a ticket that then failed for real at land is itself a
     second, independent bug worth calling out explicitly in the Done report
     even if the primary fix is (2).

MUST-FIRE FIXTURE: a new public symbol added with only a test-side
`# frob:tests` binding and no source-side directive -- `frob check --ticket`
must report the SAME T-2114 finding `land` reports today, not 0 errors.

MUST-STAY-QUIET FIXTURE: a ticket that already satisfies all land-time rules
during the normal gate loop -- close and land continue to succeed with no
new friction.
