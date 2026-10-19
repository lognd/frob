<!-- mdtest: rule=CLAIM001 -->
# CLAIM001 claim-refuted

A claim's proposition is refuted by the declared flows, with the witness path.

## What it does

A `noflow A -> B` claim is refuted when the declared flows connect A to B; the finding names the flow path. A `reach A -> B` claim is refuted when no declared flow path connects them.

## Why it matters

A claim that is never evaluated passes silently; a refuted claim is the model contradicting its own assertion.

## Remedy

Remove the flow named in the witness, drop the claim, or fix the claim's operands.

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
  noflow a -> b;
}
```

### Fires case 2

```grmb expect=fire file=design/model.grmb
grimble = "2";
module m;
node a : trusted {
}
node b : trusted {
}
claim c {
  reach a -> b;
}
```

### Clean case 3

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
  reach a -> b;
}
```

### Clean case 4

```grmb expect=clean file=design/model.grmb
grimble = "2";
module m;
node a : trusted {
}
node b : trusted {
}
claim c {
  noflow a -> b;
}
```
