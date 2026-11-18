<!-- mdtest: rule=VMOD002 -->
# VMOD002 unjustified-design

A design artifact satisfies no requirement.

## What it does

Fires when a `vmodel` artifact at the `system_design` or `component_design` level declares no `satisfies` link that resolves to an artifact. The finding names the design.

## Why it matters

A design with no requirement above it has no stated reason to exist; it grows scope the customer never asked for and nothing can show it is needed.

## Remedy

Declare `satisfies <requirement>;` on the design, or remove the design.

## Examples

### Fires case 1

```grmb expect=fire file=design/model.grmb
grimble = "2";
module m;
vmodel des_a {
  kind artifact;
  level system_design;
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
