<!-- mdtest: rule=PLAN004 -->
# PLAN004 plan-unbound-impl

An impl or page has no realization clause.

## What it does

Fires per impl or page with no realization clause. An empty selector is SYS004 and is not reported twice here.

## Why it matters

An impl that realizes nothing is dead weight the plan cannot trace to code.

## Remedy

Add a realization clause (`handler`, `ui`, ...) to the impl or page, or remove it.

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
impl customer.lands for sc { in node n; }
node n : trusted { owns "src/**"; }
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
