---
id: T-3886
title: verify worker reports unmeasurable when its own child was killed, and the land
  then spins forever on a queue that cannot drain
state: in-progress
kind: bug
origin: human
created: '2026-09-05'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/verify/_worker.py
- docs/modules/tickets-verify-sweep.md
- tests/unit/verify/test_worker.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/verify/_worker.py
  reason: separate child-timeout/spawn-refused/unparsable/genuine-unmeasurable outcomes
    via log-signal capture (land_cmd.py locked by T-3906); never-spin already bounded,
    document/verify
  actor: logan
  at: '2026-09-05'
- op: add
  glob: docs/modules/tickets-verify-sweep.md
  reason: separate child-timeout/spawn-refused/unparsable/genuine-unmeasurable outcomes
    via log-signal capture (land_cmd.py locked by T-3906); never-spin already bounded,
    document/verify
  actor: logan
  at: '2026-09-05'
- op: add
  glob: tests/unit/verify/test_worker.py
  reason: separate child-timeout/spawn-refused/unparsable/genuine-unmeasurable outcomes
    via log-signal capture (land_cmd.py locked by T-3906); never-spin already bounded,
    document/verify
  actor: logan
  at: '2026-09-05'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Reported as logand.app-v2 FROBLEMS F-043, severity blocker. This is a
RELEASE-RELEVANT defect: the verification path -- the mechanism that is supposed
to guarantee a land was checked -- reports "unmeasurable" for a check that
demonstrably succeeds when run by hand.

REPORTER'S MEASUREMENT:

    frob ticket land T-0004
      -> blocked at "verify ceiling (depth 1 > max_depth 0; age 2875s)"
      -> looped 45 minutes on "unmeasurable verification at a476db7 --
         `frob check --ticket <sha>` output had no parsable gate-summary
         line (exit=1)"
      -> `frob verify now` says the same

    the SAME check run by hand:
      frob check --ticket a476db7... /abs/repo
      -> 560s under load ~60, prints a normal gate-summary
         (37 errors, 72 warnings)

So the check works. The WORKER's invocation of it does not. Their diagnosis is
the likely one: the worker times out its child under load and reads a truncated
stream, then reports the absence of a gate-summary line as a semantic verdict.

THE ROOT DEFECT IS A CONFLATION, and it is the shape this repo keeps finding:
"the check could not be measured" and "our child was killed or truncated" are
DIFFERENT FACTS being reported as one. The first is a statement about the
repository; the second is a statement about our own subprocess management. Only
the second was true here, and it was reported as the first.

CORROBORATION FROM THIS REPO, 2026-09-05: T-3820's land emitted

    LAND-PROOF: ticket=T-3820 ... claims_reverify=skipped-unmeasured
                verified=SKIPPED-UNMEASURED

under the rapid profile. That was read as "this land owes a T-1681
re-verification pass". If F-043's mechanism is general, some proportion of
SKIPPED-UNMEASURED verdicts are not "verification was skipped" at all but "our
child died and we could not tell". MEASURE WHICH before assuming either -- that
distinction decides whether recent lands are unverified or merely unreported.

THE SECOND HALF, AND WHY IT IS A BLOCKER RATHER THAN A WRONG LABEL: the land
does not fail, it SPINS. Backpressure ceiling `max_depth 0` means an unmeasured
entry can never drain, so the queue stays non-empty, so every land waits. The
reporter killed a 45-minute loop by hand. An unmeasurable verify must fail fast
with a remedy, never block indefinitely on a condition that cannot clear itself
-- this repo has already been deadlocked twice by a quarantine that could only
be cleared by a land it was blocking (TICK002), and this is the same topology.

WHAT TO BUILD:
  1. SEPARATE THE TWO FACTS. The worker must distinguish, in its own output and
     in whatever it records: child exited non-zero with parsable output / child
     was killed by our timeout / child produced unparsable output / check ran
     and genuinely could not measure. Only the last is "unmeasurable". Log the
     child's exit reason and, if killed, the budget it exceeded -- the reporter
     had to infer all of this.
  2. NEVER SPIN. A verify that cannot complete must surface a typed failure with
     a remedy, and must not hold the backpressure queue. Decide the policy
     explicitly: fail the land, or let it proceed with an honest
     "unverified, reason=<x>" verdict recorded. Both are defensible; silence
     and spinning are not.
  3. GIVE THE WORKER A REAL BUDGET. The hand-run took 560s under load 60. If the
     worker's child budget is below that it will keep failing on exactly the
     busy repos where verification matters most. Measure the worker's current
     budget and state it. `frob verify now --budget` is mentioned by the
     reporter as a possible escape -- check whether that flag exists before
     citing it as a remedy.

DO NOT fix this by raising the timeout alone. A bigger budget makes the
symptom rarer and leaves the conflation in place, so the next slow box reports
false unmeasurables again. The separation in (1) is the fix; the budget is a
tuning parameter.

MEASUREMENT REQUIRED BEFORE THE FIX IS ACCEPTED: how many SKIPPED-UNMEASURED /
unmeasurable verdicts in this repo's recent history were child-death rather
than genuine. If that number is non-zero, every one of those lands is
unverified and the release checklist needs to know.

MUST-FIRE FIXTURES:
  - a worker child killed by its own timeout is reported as a child timeout,
    naming the budget -- not as "unmeasurable"
  - a genuinely unmeasurable check is still reported as unmeasurable
MUST-STAY-QUIET:
  - a normal verify still records a clean verdict with no new noise

ACCEPTANCE
- The four child outcomes distinguished in output and in the recorded verdict.
- No path where a land waits indefinitely on an unmeasurable verify.
- The worker's child budget measured and stated, with the 560s datapoint
  considered.
- The historical count of false-unmeasurable verdicts reported.
- All fixtures committed.

ADDENDUM 2026-09-05 (coordinator, second independently-reported instance):
logand.app-v2 FROBLEMS F-049 ("real bug, misleading refusal") is the SAME
conflation at a different site. A land failed with "evidence no longer
resolves post-merge" because pytest --collect-only ERRORED on seven modules
(ModuleNotFoundError: fakeredis -- the root uv workspace did not install the
backend member's dev group). The real cause was three lines earlier:
collect_python_tests: pytest --collect-only exited 2. The site is
_land_collected_fn/_land_passed_fn in src/frob/app/ticket_runner/_land_cmd.py
(both fold a collection ERROR -- infrastructure -- into a bare frozenset(),
which then reads identically to a collection SUCCESS that simply found
nothing matching, so "evidence no longer resolves" is reported as a semantic
finding about the code when the true cause was "we could not even collect").

NOT FIXED IN THIS PASS: src/frob/app/ticket_runner/_land_cmd.py was held
under another in-progress ticket's (T-3906) scope lease for the whole of
T-3886's work session, so this site could not be touched. Filed as
follow-up scope, not silently dropped -- the same distinguish-the-outcomes
fix this ticket applied to frob.verify._worker (log-signal capture, or
better, a proper Result[frozenset|None, Reason] return type) is the shape
that closes this second site too, once _land_cmd.py's lease clears.

F-049's SECOND, separate half (agents' uv sync pulling member dev groups
that the per-ticket gate environment does not) is an environment-consistency
defect of the T-3887 family (gates executing project code in frob's own
interpreter) -- not this ticket's shape, and not fixed here.
