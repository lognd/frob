<!-- mdtest: rule=FLOW002 -->
# FLOW002 flow-unendorsed

A flow into a higher-trust node has no endorse boundary reaching that trust.

## What it does

Fires when a flow runs from a node of lower trust to a node of higher trust and no `endorse` boundary on the flow starts at or below the source trust and ends at or above the destination trust. The finding names the flow.

## Why it matters

Untrusted input reaching a trusted node unchecked is the crossing the trust lattice exists to forbid.

## Remedy

Add an `endorse` boundary on the flow, or lower the destination's trust.

## Examples

### Fires case 1

```grmb expect=fire file=design/model.grmb
grimble = "2";
module m;
node a : foreign {
}
node b : trusted {
}
flow f1 : a -> b {
  label Public;
  rate 1 req/s;
}
```

### Clean case 2

```grmb expect=clean file=design/model.grmb
grimble = "2";
module m;
node a : foreign {
}
node b : trusted {
}
flow f1 : a -> b {
  label Public;
  rate 1 req/s;
}
boundary b1 endorse f1 : foreign -> trusted when "checked";
```
