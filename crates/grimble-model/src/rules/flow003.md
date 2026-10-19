<!-- mdtest: rule=FLOW003 -->
# FLOW003 flow-no-rate

A flow from a foreign node declares no rate.

## What it does

Fires when a flow's source node has `foreign` trust and the flow declares no `rate`. The finding names the flow.

## Why it matters

A foreign source can send without limit; the model has nothing to size or throttle the flow against.

## Remedy

Declare a `rate` on the flow.

## Examples

### Fires case 1

```grmb expect=fire file=design/model.grmb
grimble = "2";
module m;
node a : foreign {
}
node b : foreign {
}
flow f1 : a -> b {
  label Public;
}
```

### Clean case 2

```grmb expect=clean file=design/model.grmb
grimble = "2";
module m;
node a : foreign {
}
node b : foreign {
}
flow f1 : a -> b {
  label Public;
  rate 1 req/s;
}
```
