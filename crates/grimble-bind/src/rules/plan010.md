<!-- mdtest: rule=PLAN010 -->
# PLAN010 plan-unjustified-scenario

A scenario realizes no goal and no scenario includes it.

## What it does

Fires per scenario with an empty `realizes` list that no other scenario includes. It runs even for a whole-body `sorry` scenario. Reported as Error: the rule table lists Warn, but the severity model has no Warn.

## Why it matters

A scenario that serves no goal and is reused by none has no reason to exist in the plan.

## Remedy

Add a `realizes` goal, include the scenario from one that does, or delete it.

## Examples

### Fires case 1

```grmb expect=fire file=design/m.grmb
grimble = "2";
module m;

system s { title "S"; }
actor customer : human;
goal customer as action { buy; }
step customer.lands;
scenario orphan { customer.lands -> end ok; }
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
