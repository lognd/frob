<!-- mdtest: rule=PLAN018 -->
# PLAN018 plan-unrealized-one-of

No alternative of a `one_of` is realized by any scenario.

## What it does

A `one_of` group none of whose alternatives is realized (equal, ancestor or descendant) by a scenario `realizes` is flagged at the group.

## Why it matters

A `one_of` says one alternative must hold; with none realized the goal is not met.

## Remedy

Write a scenario that realizes one of the alternatives.

## Examples

### Fires case 1

```grmb expect=fire file=design/model.grmb
grimble = "2";
module m;

system s {
  actor u : human;
  step u.go;

  goal u { start; }
  goal u.start { one_of { by_hand; library; } }

  scenario t {
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

  goal u { start; }
  goal u.start { one_of { by_hand; library; } }

  scenario t realizes u.start.library {
    u.go -> end ok;
  }
}
```
