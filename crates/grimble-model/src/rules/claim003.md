<!-- mdtest: rule=CLAIM003 -->
# CLAIM003 claim-unresolved

A claim cannot be evaluated on this model, so it has no verdict.

## What it does

A claim with `proof` above L1 and neither `evidence` nor `assumed` is Unresolved. A `bound METRIC TARGET <= Q` claim is Unresolved because the model declares no measured value to compare with. A `noflow` or `reach` claim is Unresolved when an operand resolves to no node, or when holes may hide a flow.

## Why it matters

An unevaluable claim is never reported as satisfied; the reason says what the model lacks.

## Remedy

Supply the missing evidence, or accept the claim with an `assumed` clause.

## Examples

### Fires case 1

```grmb expect=fire file=design/model.grmb
grimble = "2";
module m;
node a : trusted {
}
node b : trusted {
}
flow f : a -> b {
  label Public;
}
claim c {
  bound latency f <= 5ms; // unresolved: CLAIM003
}
```

### Clean case 2

```grmb expect=clean file=design/model.grmb
grimble = "2";
module m;
node a : trusted {
}
node b : trusted {
}
flow f : a -> b {
  label Public;
}
claim c {
  noflow b -> a;
}
```
