<!-- mdtest: rule=PLAN014 -->
# PLAN014 plan-dead-structure

A step is used nowhere, or a refinement or `one_of` has a single alternative.

## What it does

Flags a step that no scenario uses and no impl covers, a goal refined into exactly one variant (additive blocks aggregated), and a `one_of` group with one alternative.

## Why it matters

A step nobody calls, or a choice with one option, is structure that carries no information and usually marks a half-finished model.

## Remedy

Use or delete the step; add the missing alternatives or fold the single variant into its parent.

## Examples

### Fires case 1

```grmb expect=fire file=design/model.grmb
grimble = "2";
module m;

system s {
  actor u : human;
  step u.go;
  step system.unused;

  scenario t {
    u.go -> end ok;
  }
}
```

### Fires case 2

```grmb expect=fire file=design/model.grmb
grimble = "2";
module m;

system s {
  actor u : human;
  step u.go;

  goal u { start; }
  goal u.start { only; }

  scenario t realizes u.start.only {
    u.go -> end ok;
  }
}
```

### Fires case 3

```grmb expect=fire file=design/model.grmb
grimble = "2";
module m;

system s {
  actor u : human;
  step u.go;

  goal u { start; }
  goal u.start { one_of { by_hand; } }

  scenario t realizes u.start.by_hand {
    u.go -> end ok;
  }
}
```

### Clean case 4

```grmb expect=clean file=design/model.grmb
grimble = "2";
module m;

system s {
  actor u : human;
  step u.go;
  step system.work;

  scenario t {
    u.go -> system.work -> end ok;
  }
}
```
