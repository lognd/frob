<!-- mdtest: rule=VMOD001 -->
# VMOD001 orphan-requirement

A requirement is satisfied by no design artifact.

## What it does

Fires when a `vmodel` artifact at the `requirements` level is the target of no `satisfies` link from any other artifact. The finding names the requirement.

## Why it matters

A requirement nothing satisfies is a promise with no design behind it; the V-model has no left-side path from it down to a design, so it can never be verified end to end.

## Remedy

Add a design artifact that declares `satisfies <requirement>;`, or remove the requirement.

## Examples

### Fires case 1

```grmb expect=fire file=design/model.grmb
grimble = "2";
module m;
vmodel req_a {
  kind artifact;
  level requirements;
}
```

### Clean case 2

```grmb expect=clean file=design/model.grmb
grimble = "2";
module m;
vmodel req_a {
  kind artifact;
  level requirements;
}
vmodel des_a {
  kind artifact;
  level system_design;
  satisfies req_a;
}
```
