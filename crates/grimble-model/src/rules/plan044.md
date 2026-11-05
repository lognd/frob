<!-- mdtest: rule=PLAN044 -->
# PLAN044 plan-open-map-no-rest

An outcome map over an `open` set has no `_` source.

## What it does

A waypoint with outcome mappings in an impl of a step whose outcome set is `open` must include a `_` source, the explicit other arm. A waypoint without any mapping is not judged here.

## Why it matters

An open set can grow variants the map does not know; without `_` the new outcomes have no destination.

## Remedy

Add `_ => VARIANT;` to the waypoint mapping.

## Examples

### Fires case 1

```grmb expect=fire file=design/model.grmb
grimble = "2";
module m;

system s {
  ambient escalate { verified_by "tests/a.py"; }
  actor u : human;
  step u.go : open { ok, bad };

  scenario t fails with { bad } {
    u.go => {
      ok => end ok;
      bad => end err(bad);
      unknown => end err(bad);
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
  step u.go : open { ok, bad };

  scenario t fails with { bad } {
    u.go => {
      ok => end ok;
      bad => end err(bad);
      unknown => end err(bad);
    }
  }

  impl u.go for t {
    chain {
      call c = "a.py::c" {
        PaymentDeclined => bad;
        _ => bad;
        verified_by "tests/a.py";
      }
    }
  }
}
```
