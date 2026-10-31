<!-- mdtest: rule=PLAN006 -->
# PLAN006 plan-uncovered-arm

A collected error pair has no covering `verified_by ... for` evidence.

## What it does

Fires once per collected `(step, variant)` pair of a scenario that no resolving `verified_by SEL for STEP.VARIANT` covers, whether the clause is written on the scenario or on an impl of that step. The detail names the pair and the handle arm that takes it, or says it propagates. Unresolved when only a May selector could supply the evidence. Reported as Error: the rule table lists Advisory, but the severity model has no Advisory. Waypoints are unmodeled, so only scenario and impl clauses cover a pair.

## Why it matters

An error outcome that is handled or propagated but never exercised by a test is an unproven path.

## Remedy

Add `verified_by "path::test" for STEP.VARIANT;` to the scenario or to an impl of the step.

## Examples

### Fires case 1

```grmb expect=fire file=design/m.grmb
grimble = "2";
module m;

system s { title "S"; }
actor customer : human;
goal customer as action { buy; }
step customer.lands;
step system.flaky -> { ok, bad };
scenario sc realizes customer.buy fails with { bad } { customer.lands -> system.flaky -!> end ok; }
```

### Clean case 2

```grmb expect=clean file=design/m.grmb
grimble = "2";
module m;

system s { title "S"; }
actor customer : human;
goal customer as action { buy; }
step customer.lands;
scenario sc realizes customer.buy { customer.lands -> end ok; }
```
