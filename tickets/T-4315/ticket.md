---
id: T-4315
title: Post-land sweep is budget-truncated under load so every land stays unverified
state: dropped
kind: bug
origin: human
created: '2026-09-08'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_land.py
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
THE POST-LAND SAFETY NET IS BUDGET-LIMITED, SO IT VERIFIES NOTHING EXACTLY WHEN
THE MACHINE IS BUSY -- WHICH IS EVERY TIME IT MATTERS. FIVE OF FIVE LANDS TODAY
ARE RECORDED AS UNVERIFIED.

WHAT WAS MEASURED. Every deferred post-land sweep run today ends the same way: the
sweep is reported UNMEASURABLE and the commit is explicitly recorded as staying
unverified, with the baseline left untouched. Five separate lands, five identical
outcomes, no exceptions. The logs are kept per-land under the sweep directory and
all say the same thing.

THE CAUSE IS STATED IN THE LOGS THEMSELVES, one line above the failure: the check
invocation runs with a budget, and the budget expired with three whole stage
groups still undone. The surrounding machinery then does the correct thing -- it
refuses to treat a truncated run as a smaller answer, because a truncated run
answers a different question -- and so the entire sweep resolves to UNMEASURABLE.
Nothing here is misbehaving in isolation; the pieces compose into a mechanism that
cannot succeed under load.

WHY THIS IS WORSE THAN A MISSING CHECK. This sweep exists specifically to
compensate for the fast land profile switching the pre-land sweep off. The
relaxation is granted on the promise that verification happens afterwards. If the
afterwards step is structurally unable to complete whenever several lands are in
flight, then the relaxation is unconditional in practice and nobody is measuring
these commits at all. Worse, it fails quietly into a log file rather than to
whoever is deciding whether the tree is releasable.

THE BUDGET IS THE WRONG INSTRUMENT HERE AND THAT IS THE HEART OF IT. A budget
bounds how long something may take by dropping coverage, which is a reasonable
trade for an interactive command a person is waiting on. This sweep is detached,
already deferred, and nobody is waiting on it -- there is no latency to protect.
Giving it a deadline buys nothing and costs the entire measurement. Consider
removing the budget from this path, or scaling it to the work rather than to a
fixed wall-clock figure, and say which you chose and why.

MAKE THE FAILURE REACH SOMEONE. An UNMEASURABLE sweep currently lands in a log
nobody reads. If a commit stays unverified, that fact should be visible where land
verification status is consulted -- the same place a verified result would appear.
An unverified land is a finding, not an absence of one, and this project has been
repeatedly bitten by an absent measurement dressed as a clean one.

CHECK WHETHER THE RECORDED STATE IS HONEST. Confirm what a land's proof line and
any status surface report for these five commits: if any of them presents as
verified or simply says nothing, that is a second defect and more serious than the
first. Report what you actually find.

VERIFY BY FORCING THE CONDITION -- run the sweep against a tree with contention, or
with the budget set low enough to truncate, and assert the resulting state is
reported as unverified everywhere it is consulted. Then run it unconstrained and
assert it genuinely measures. A fix confirmed only on an idle machine has not been
confirmed.

## Failure log
- 2026-09-08 attempt 1: scoped to src/frob/tickets/_land.py only, but both defects (detached sweep's --budget instrument in _land_cmd.py/_check_chunking.py; unverified-status silently absent from frob verify status/_watermark.py) live entirely outside that file -- filed T-draft-627c0a0d with the correct scope and full investigation notes
- 2026-09-09 attempt 2: Superseded: both defects this ticket describes (detached post-land sweep truncated by --budget under load producing UNMEASURABLE; that unverified state then invisible at frob verify status/ticket show) are already fixed and landed under T-4318 (a0683a483, _measure_fresh_and_write_baseline now calls _unscoped_error_findings(..., full=True), dropping the --budget ceiling entirely for this detached/nobody-waiting caller) and T-4324 (status/rapid-debt.jsonl visibility gap), both filed by this ticket's own prior attempt (see its Failure log) and both state=done on main. No remaining defect in src/frob/tickets/_land.py or elsewhere to fix under this id.

## Drop reason
- 2026-09-09: premise stale: both defects fixed under T-4318 (a0683a483) and T-4324; fail would only requeue it
