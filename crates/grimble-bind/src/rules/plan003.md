<!-- mdtest: rule=PLAN003 -->
# PLAN003 plan-unimplemented-step

A step used by a scenario has no impl.

## What it does

Fires per step use `(step, scenario)` that has neither a specific `impl` nor an `impl ... for *`.

## Why it matters

A scenario that walks a step nothing implements cannot run end to end.

## Remedy

Add `impl <step> for <scenario>` (or `for *`) binding the step to code.

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
