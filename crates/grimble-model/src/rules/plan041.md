<!-- mdtest: rule=PLAN041 -->
# PLAN041 plan-unmapped-error

A failure variant of a step is reached by no outcome-map source.

## What it does

When an impl of a step writes outcome mappings, each declared variant other than `ok` must be the target of some mapping in the impl; the step name in the `impl` head is flagged otherwise. The producible errors of the waypoint unit (Exact, May, Unknown) need the error-flow facts of the language adapter and the required Unresolved on an opaque cone is not raised here.

## Why it matters

A failure variant no mapping reaches is a declared outcome the code never reports, so the scenario arm that handles it is untested dead path.

## Remedy

Add a mapping to the variant, or remove the variant from the step.

## Examples

### Fires case 1

```grmb expect=fire file=design/model.grmb
grimble = "2";
module m;

system s {
  ambient escalate { verified_by "tests/a.py"; }
  actor u : human;
  step u.go : { ok, bad, worse };

  scenario t {
    u.go => {
      ok => end ok;
      bad => end err(bad);
      worse => end err(worse);
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

### Clean case 2

```grmb expect=clean file=design/model.grmb
grimble = "2";
module m;

system s {
  ambient escalate { verified_by "tests/a.py"; }
  actor u : human;
  step u.go : { ok, bad, worse };

  scenario t {
    u.go => {
      ok => end ok;
      bad => end err(bad);
      worse => end err(worse);
    }
  }

  impl u.go for t {
    chain {
      call c = "a.py::c" {
        PaymentDeclined => bad;
        Timeout => worse;
        verified_by "tests/a.py";
      }
    }
  }
}
```
