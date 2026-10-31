<!-- mdtest: rule=PLAN002 -->
# PLAN002 plan-coarse-realization

A scenario realizes a goal that has child goals.

## What it does

Fires per scenario whose `realizes` names a goal with children (a non-leaf goal). The scenario is then a coarse realization: it covers the parent only through its own steps, not through its children. It runs even for a whole-body `sorry` scenario. Reported as Error: the rule table lists Warn, but the severity model has no Warn.

## Why it matters

A coarse scenario hides which child goals are realized, so the leaf goals under it look covered when no scenario targets them.

## Remedy

Realize the leaf goals under the parent, one scenario per leaf or one scenario naming several leaves.

## Examples

### Fires case 1

```grmb expect=fire file=design/m.grmb
grimble = "2";
module m;

system s { title "S"; }
actor customer : human;
goal customer as action { buy; }
goal customer.buy as path { card; cash; }
step customer.lands;
scenario sc realizes customer.buy { customer.lands -> end ok; }
```

### Clean case 2

```grmb expect=clean file=design/m.grmb
grimble = "2";
module m;

system s { title "S"; }
actor customer : human;
goal customer as action { buy; }
goal customer.buy as path { card; cash; }
step customer.lands;
scenario sc realizes customer.buy.card, customer.buy.cash { customer.lands -> end ok; }
```
