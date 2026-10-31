<!-- mdtest: rule=PLAN009 -->
# PLAN009 plan-node-mismatch

An impl declares one node but its code is owned by another.

## What it does

Fires per impl with `in node N` when the Must owner of a bound identity of one of its realizations is a different node. A May owner is not reported. Waypoints are not modeled, so only the realization owner is compared. Reported as Error: the rule table lists Warn, but the severity model has no Warn.

## Why it matters

The declared node is the plan's claim about where the work lives; code owned elsewhere makes the plan and the ownership map disagree.

## Remedy

Change `in node` to the owning node, or move the code under the declared node's `owns` selector.

## Examples

### Fires case 1

```grmb expect=fire file=design/m.grmb
grimble = "2";
module m;

system s { title "S"; }
actor customer : human;
goal customer as action { buy; }
step customer.lands;
scenario sc realizes customer.buy { customer.lands -> end ok; }
impl customer.lands for sc { handler = "src/lib.rs::run"; in node b; }
node a : trusted { owns "src/**"; }
node b : trusted { owns "b/**"; }
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
impl customer.lands for sc { handler = "src/lib.rs::run"; in node a; }
node a : trusted { owns "src/**"; }
node b : trusted { owns "b/**"; }
```
