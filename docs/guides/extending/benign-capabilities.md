# Benign capabilities

<!-- frob:describes src/frob/strata/_threat.py::BenignCapability -->

## What it is and where it lives

`src/frob/strata/_threat.py`: `BenignCapability` (frozen, `kind` + `reason`)
and `DEFAULT_BENIGN_CAPABILITIES: tuple[BenignCapability, ...]`. Mirrors
`OutOfScopeEntry` for THREAT001, but at the capability-kind level rather
than the CWE-id level -- it excuses a `may` capability kind that maps to
no sink in a given catalog family's taxonomy. See
[Threat catalog](threat-catalog.md) for `CWE_CATALOG`/`QUALITY_CATALOG`
themselves.

## Add-an-entry recipe

1. Identify the unmapped `may` capability kind (e.g. from `_selfconform.py`
   SYS100/SYS101 output, or a THREAT002 violation naming the kind).
2. Add `BenignCapability(kind=<the may-atom kind>, reason=<why no sink
   taxonomy entry targets it, min_length=1>)` to `DEFAULT_BENIGN_CAPABILITIES`.
3. **Check which family this actually affects.** `_evaluate_family` passes
   the SAME `benign` tuple to both `CWE_CATALOG` (security) and
   `QUALITY_CATALOG` (quality) loops; `excused` is only consulted for
   kinds NOT already `known` in that family's catalog. A kind already
   classified in one family makes your excuse a no-op there -- it only
   takes effect in the family that genuinely lacks the mapping.

## Drift-locks that fire

- **THREAT002**: an unclassified `may` kind with no `BenignCapability`
  entry fails closed (deny-by-default, charter law 2) -- "never forget."
- Indirectly **THREAT004/THREAT005**: the code-level mirrors join the
  same `_entries_by_capability_kind`/excused-kind logic against observed
  effects from `_effects.py`.

## Worked example diff

```python
# src/frob/strata/_threat.py, in DEFAULT_BENIGN_CAPABILITIES:
BenignCapability(
    kind="ffi",
    reason=(
        "tier-2 capability kind (frob.vet._capability scanner vocabulary); "
        "no CWE_CATALOG or QUALITY_CATALOG sink entry targets bare FFI calls "
        "on their own -- the memory-safety concern is captured by language-"
        "specific capability rows in the vet capability registry instead"
    ),
),
```

## Common mistakes

- **Assuming one excuse clears both families.** The `exec` entry in
  `DEFAULT_BENIGN_CAPABILITIES` is the canonical example: it is a pure
  no-op for the security loop (CWE-78 already covers `exec`) and only
  matters for `QUALITY_CATALOG`, which has no `exec`-mapped weakness at
  all. Read the module docstring's worked explanation before assuming an
  excuse you added "did nothing" -- it may be doing exactly the job it
  was meant for in the OTHER family.
- **Confusing this vocabulary with the vet scanner's.** `frob.vet.
  _capability`'s scanner kinds (net/fs-write-derived "fs"/eval/env/ffi/
  install-hook) are a DIFFERENT vocabulary from the CWE-sink-shaped kinds
  the threat catalog uses (html_render/sql/exec/fetch_url/deserialize/
  client_storage). Declaring a vet-scanner kind on a `may` atom without a
  `BenignCapability` fails THREAT002 with no way to excuse it under the
  wrong vocabulary -- this is exactly why `DEFAULT_BENIGN_CAPABILITIES`
  exists: to bridge the gap until the two vocabularies are reconciled.

## See also

- [Threat catalog](threat-catalog.md)
- [Capability registry](capability-registry.md) -- the vet-side vocabulary
  and its own `MatrixExcuse` mechanism (a parallel but distinct concept).
