<!-- mdtest: rule=PLAN042 -->
# PLAN042 plan-unproducible-mapping

An outcome map targets a variant the step does not declare.

## What it does

A waypoint mapping `SOURCE => name;` whose target is not an outcome variant of the impl step is flagged at the target. Whether the unit can produce the mapped source, and whether a declared variant has any source, needs adapter error-flow facts and is not judged here.

## Why it matters

A mapping into a variant the step cannot report is dead and hides a misspelled outcome.

## Remedy

Map to a declared variant of the step or add the variant to the step.

## Examples

### Fires case 1

```grmb expect=fire file=design/model.grmb
grimble = "2";
module m;

system s {
  ambient escalate { verified_by "tests/a.py"; }
  actor u : human;
  step u.go :  { ok, bad };

  scenario t {
    u.go => {
      ok => end ok;
      bad => end err(bad);
    }
  }

  impl u.go for t {
    chain {
      call c = "a.py::c" {
        PaymentDeclined => bad;
        Timeout => nope;
        verified_by "tests/a.py";
      }
    }
  }
}
```

### Clean case 2

```grmb expect=clean file=design/model.grmb
grimble = "2";
module m;

system s {
  ambient escalate { verified_by "tests/a.py"; }
  actor u : human;
  step u.go :  { ok, bad };

  scenario t {
    u.go => {
      ok => end ok;
      bad => end err(bad);
    }
  }

  impl u.go for t {
    chain {
      call c = "a.py::c" {
        PaymentDeclined => bad;
        verified_by "tests/a.py";
      }
    }
  }
}
```
