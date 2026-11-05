<!-- mdtest: rule=PLAN016 -->
# PLAN016 plan-retry-hazard

A `retry` repeats a step that is not marked `idempotent`.

## What it does

An arm `retry` re-runs the chain path from its target to the matched element; an ambient `retry` re-runs every system step of the scenarios it covers and their includes. The rule reports one finding per retry, naming the repeated steps that lack the trailing `idempotent` fact. An ambient `restart` is not read, and neither is a `retry` in a `handle` arm.

## Why it matters

Repeating a step with side effects, such as a payment, can apply the effect twice.

## Remedy

Mark the step `idempotent` if repeating it is safe, or replace the `retry` with an arm that ends the scenario.

## Examples

### Fires case 1

```grmb expect=fire file=design/model.grmb
grimble = "2";
module m;

system s {
  actor u : human;
  step u.go;
  step system.pays : { ok, declined };

  scenario t {
    u.go -> system.pays => {
      ok => end ok;
      declined => retry system.pays max 3;
    }
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
  step system.pays : { ok, declined } idempotent;

  scenario t {
    u.go -> system.pays => {
      ok => end ok;
      declined => retry system.pays max 3;
    }
  }
}
```
