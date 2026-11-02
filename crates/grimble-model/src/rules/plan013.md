<!-- mdtest: rule=PLAN013 -->
# PLAN013 plan-unused-wildcard-impl

An `impl STEP for *` covers a step that no scenario uses.

## What it does

A wildcard impl whose step appears in no scenario chain is flagged at the `*`.

## Why it matters

An impl nothing can reach is dead code that still has to be maintained and verified.

## Remedy

Use the step in a scenario, or delete the impl.

## Examples

### Fires case 1

```grmb expect=fire file=design/model.grmb
grimble = "2";
module m;

system s {
  actor u : human;
  step u.go;
  step system.work;

  scenario t {
    u.go -> end ok;
  }

  impl system.work for * { handler = "src/work.rs::work"; }
}
```

### Clean case 2

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

  impl system.work for * { handler = "src/work.rs::work"; }
}
```
