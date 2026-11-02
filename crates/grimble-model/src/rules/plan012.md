<!-- mdtest: rule=PLAN012 -->
# PLAN012 plan-vacuous-arm

A non-ok outcome arm ends `end ok` without doing anything.

## What it does

An arm for an outcome other than `ok` that is just `end ok;` swallows the outcome: the scenario succeeds as if nothing went wrong. Wildcard and `ok` arms are not checked.

## Why it matters

A failure that silently counts as success hides a missing recovery or error path.

## Remedy

End the arm with `end err(VARIANT)`, or give it a recovery chain before `end ok`.

## Examples

### Fires case 1

```grmb expect=fire file=design/model.grmb
grimble = "2";
module m;

system s {
  actor u : human;
  step u.go;
  step system.flaky -> { ok, bad };

  scenario t {
    u.go -> system.flaky => {
      ok -> end ok;
      bad -> end ok;
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
  step system.flaky -> { ok, bad };

  scenario t {
    u.go -> system.flaky => {
      ok -> end ok;
      bad -> end err(bad);
    }
  }
}
```
