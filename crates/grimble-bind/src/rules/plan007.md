<!-- mdtest: rule=PLAN007 -->
# PLAN007 plan-affordance

An impl's realization kinds do not fit the kind of the step owner.

## What it does

Fires per impl whose realization kinds miss the affordance rule of the step owner: `human` needs one of `ui`, `cli`, `api`; `external` needs `handler` or `api`; `device` needs `isr` or `driver`; `timer` needs `handler` or `isr`; a `system` step needs `handler`, or `isr`/`driver` when every scenario using the step is started by a `timer` or `device` actor. A scenario is started by the owner of its first main-chain step, through leading includes. Unresolved when the only open question is a scenario whose trigger is unknown. An impl with no realization is PLAN004's. Reported as Error: the rule table lists Warn, but the severity model has no Warn.

## Why it matters

A human cannot call a handler and a timer cannot click a button; an impl of the wrong kind can never run as planned.

## Remedy

Give the impl a realization of a kind the step owner can use, or fix the step owner.

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
impl customer.lands for sc { handler = "src/lib.rs::run"; }
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
impl customer.lands for sc { ui = "src/lib.rs::run"; }
```

### Clean case 3

```grmb expect=clean file=design/m.grmb
grimble = "2";
module m;

system s { title "S"; }
actor tick : timer;
goal tick as action { sample; }
step tick.fires;
step system.read;
scenario sc realizes tick.sample { tick.fires -> system.read -> end ok; }
impl system.read for sc { isr = "src/lib.rs::run"; }
```
