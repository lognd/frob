<!-- mdtest: rule=FLOW001 -->
# FLOW001 flow-label-closure

A flow's label exceeds the destination node's clearance and no declassify boundary lowers it.

## What it does

Fires when a flow's `label` is above the `clearance` of its destination node (default `Secret`) and no `declassify` boundary on the flow lowers the label to or below that clearance. The finding names the flow.

## Why it matters

A label above the clearance of the node it reaches means data rests where the model says it may not.

## Remedy

Raise the destination's `clearance`, lower the flow's `label`, or add a `declassify` boundary on the flow.

## Examples

### Fires case 1

```grmb expect=fire file=design/model.grmb
grimble = "2";
module m;
node a : trusted {
}
node b : trusted {
  clearance Public;
}
flow f2 : a -> b {
  label Secret;
  rate 1 req/s;
}
```

### Clean case 2

```grmb expect=clean file=design/model.grmb
grimble = "2";
module m;
node a : trusted {
}
node b : trusted {
  clearance Public;
}
flow f2 : a -> b {
  label Secret;
  rate 1 req/s;
}
boundary b1 declassify f2 : Secret -> Public;
```

### Clean case 3

```grmb expect=clean file=design/model.grmb
grimble = "2";
module m;
node a : trusted {
}
node b : trusted {
  clearance Secret;
}
flow f2 : a -> b {
  label Secret;
  rate 1 req/s;
}
```
