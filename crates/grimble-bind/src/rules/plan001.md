<!-- mdtest: rule=PLAN001 -->
# PLAN001 plan-unrealized-goal

A goal leaf is realized by no scenario.

## What it does

Fires per goal leaf that no scenario's `realizes` clause covers.

## Why it matters

A goal nobody realizes is a promise with no plan behind it; the planning graph reports it so it cannot silently stay open.

## Remedy

Add a scenario that `realizes` the goal, or drop the goal.

## Examples

### Fires case 1

```grmb expect=fire file=design/m.grmb
grimble = "2";
module m;

system s { title "S"; }
actor customer : human;
goal customer as action { buy; }
```

### Clean case 2

```grmb expect=clean file=design/m.grmb
grimble = "2";
module m;

system s { title "S"; }
actor customer : human;
goal customer as action { buy; }
step customer.lands;
scenario sc realizes customer.buy { customer.lands -> end ok; verified_by "tests/e2e/sc.spec.ts"; }
impl customer.lands for sc { handler = "src/lib.rs::run"; verified_by "tests/lands.rs"; }
```
