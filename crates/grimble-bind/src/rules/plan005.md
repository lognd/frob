<!-- mdtest: rule=PLAN005 -->
# PLAN005 plan-unverified

A goal leaf, scenario, impl or page has no own evidence.

## What it does

Fires per goal leaf, scenario, impl or page with no resolving `verified_by` of its own (or only `planned` clauses). Unresolved when only a May selector could supply it.

## Why it matters

Planned work with no evidence of its own is unverified, however well the parts around it are tested.

## Remedy

Add a `verified_by` clause that resolves to a test.

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
goal customer as action { buy { verified_by "tests/t.rs::it_works"; } }
step customer.lands;
scenario sc realizes customer.buy { customer.lands -> end ok; verified_by "tests/t.rs::it_works"; }
impl customer.lands for sc { handler = "src/lib.rs::run"; verified_by "tests/t.rs::it_works"; }
```
