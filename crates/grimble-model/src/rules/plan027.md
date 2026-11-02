<!-- mdtest: rule=PLAN027 -->
# PLAN027 plan-realized-non-goal

A scenario realizes a `non_goal` of its system.

## What it does

A scenario `realizes` a name its system declares with `non_goal NAME;` is flagged at the realized path.

## Why it matters

A non_goal is a declared promise not to build something; realizing it contradicts the declaration.

## Remedy

Drop the `realizes`, or remove the `non_goal` if the scope changed.

## Examples

### Fires case 1

```grmb expect=fire file=design/model.grmb
grimble = "2";
module m;

system s {
  actor u : human;
  step u.go;
  non_goal cross_tenant;

  scenario t realizes cross_tenant {
    u.go -> end ok;
  }
}
```

### Clean case 2

```grmb expect=clean file=design/model.grmb
grimble = "2";
module m;

system s {
  actor u : human;
  step u.go;
  non_goal cross_tenant;

  scenario t {
    u.go -> end ok;
  }
}
```
