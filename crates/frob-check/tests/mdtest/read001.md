<!-- mdtest: rule=READ001 -->
# READ001 unreadable file

A walked file the analysis cannot read, here one over `size_cap`, fires.

## A file over the size cap fires

```text expect=fire
=== frob.toml
[check]
size_cap = 64
=== docs/big.md
# Big

This file is well over the sixty-four byte cap set above, so it is skipped.
```

## A file under the cap is clean

```text expect=clean
=== frob.toml
[check]
size_cap = 4096
=== docs/small.md
# Small

Fits.
```

## A file over the size cap is never read, so it is unresolved

```text expect=unresolved
=== frob.toml
[check]
size_cap = 64
=== docs/big.md
# Big

This file is well over the sixty-four byte cap set above, so it is skipped.
```
