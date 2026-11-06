<!-- mdtest: rule=CLAIM004 -->
# CLAIM004 claim-never-refuted

A `never NODE uses ATOM` claim is refuted by code the node owns.

## What it does

Fires per `claim` with a `never NODE uses ATOM;` proposition when code the node owns uses the atom, or a child of it (`net` covers `net.connect`), directly or transitively through callees. The message names the call sites, and a use carried through a wrapper names the path. Unresolved when the use sits in code owned only at `may` or the receiver did not resolve, since a claim is never silently ok.

## Why it matters

A negative guarantee ("this node never touches the network") otherwise lives only in prose, and a wrapper two calls away silently breaks it.

## Remedy

Remove the use, route it through a node that is allowed to make it, or retract the claim in a reviewed change.

## Examples

### Fires case 1

```grmb expect=fire file=design/m.grmb config="py"
grimble = "2";
module m;

node a : trusted {
  owns "src/x.py";
  may fs.read;
  may exec;
  may net.listen;
}
node d : trusted {
  owns "design/**";
}
claim a_reads_nothing {
  never a uses fs.read;
}
```

### Clean case 2

```grmb expect=clean file=design/m.grmb config="py"
grimble = "2";
module m;

node a : trusted {
  owns "src/x.py";
  may fs.read;
  may exec;
  may net.listen;
}
node d : trusted {
  owns "design/**";
}
claim a_writes_nothing {
  never a uses fs.write;
}
```
