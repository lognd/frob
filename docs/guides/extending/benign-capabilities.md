# Benign capabilities

<!-- frob:describes src/frob/strata/_threat.py::BenignCapability -->

## What it is and where it lives

`src/frob/strata/_threat.py`: `BenignCapability` (frozen, `kind` +
`reason` + `caught_by` + an optional `family`, mandatory for repo-declared
excuses -- T-0511) and `DEFAULT_BENIGN_CAPABILITIES: tuple[BenignCapability,
...]`. Mirrors
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

## Per-repo declarations

<a id="per-repo-declarations"></a>

T-0017 (graphite adoption): `DEFAULT_BENIGN_CAPABILITIES` above is a
hardcoded Python tuple living in frob's OWN source -- a consuming repo
with a genuinely benign, non-tier-2 `may` kind (e.g. `html_render`/
`client_storage` on a browser-only node, unmapped under a `QUALITY_
CATALOG`-only view) had no way to say so without either waiving THREAT002
by name (naming a gap frob itself must patch, not a real repo-specific
fact) or patching frob's own module. `load_repo_benign_capabilities`
(`src/frob/strata/_threat.py`) closes that gap: it reads `frob.toml`'s
`[[strata.benign_capabilities]]` array of tables -- the SAME array-of-
tables shape `frob.policy`'s `[[policy.*]]` rules already use, chosen
over inventing a new `.strata` surface construct (a `benign "kind" reason
"..."` grammar addition) because the excuse is repo-CONFIGURATION, not a
design-model FACT about a node -- it says nothing about what a node does,
only which catalog gaps this repo accepts, the same register `[graph].
exclude`/`[vet.allow]`/`[[policy.*]]` already occupy in `frob.toml`. See
[Per-repo declarations](#per-repo-declarations) below for the full design
rationale.

```toml
# frob.toml
[[strata.benign_capabilities]]
kind = "html_render"
reason = "browser node renders trusted static assets only, no template injection surface"
caught_by = "content-security-policy review, out of frob scope"
family = "quality"

[[strata.benign_capabilities]]
kind = "client_storage"
reason = "no QUALITY_CATALOG sink for this repo's usage (already CWE-922/312-classified under the security family)"
caught_by = "already CWE-922/312 classified in the security family"
family = "quality"
```

Each entry needs `kind`, a non-blank `reason`, a non-blank `caught_by`,
and (T-0511, strata audit G12) a mandatory `family` naming WHICH catalog
family ("security" | "quality") the excuse applies against -- deny-by-
default, same discipline `BenignCapability`'s own `Field(min_length=1)`
enforces for the built-in tuple. `family` is CHECKED, not merely
recorded: `load_repo_benign_capabilities` rejects an entry whose `kind`
is already classified (has a `capability_kind` entry) in the family it
names -- both `html_render`/`client_storage` above are legitimate
`family = "quality"` excuses (unmapped in `QUALITY_CATALOG`) but would be
REJECTED as `family = "security"` (both already classified there, under
CWE-79 and CWE-922/312 respectively). A missing `frob.toml`, or a
`[strata]` table with no `benign_capabilities` key, is `Ok(())` (no
repo-declared excuses is the common, valid case); a malformed entry
(missing `kind`/`reason`/`caught_by`/`family`, blank `reason`, an
unrecognized `family` value, a `family` claim the catalog contradicts, or
unparseable TOML) is `Err(StrataError.MalformedBenignConfig)` -- `frob
sys audit` exits 1 rather than silently dropping or silently trusting
it. `frob sys audit`'s wiring (`src/frob/app/sys_runner.py::
_evaluate_audit`) merges `DEFAULT_BENIGN_CAPABILITIES + repo_declared`
before calling `evaluate_exhaustiveness` -- repo entries are ADDITIONAL
excuses, never a replacement for the built-in tier-2 vocabulary bridge.
A `waive "THREAT002:<kind>"` a repo carried as a workaround before this
channel existed should be replaced by a first-class
`[[strata.benign_capabilities]]` entry with the same reason -- the excuse
becomes a declared, checkable fact instead of a suppression.

## See also

- [Threat catalog](threat-catalog.md)
- [Capability registry](capability-registry.md) -- the vet-side vocabulary
  and its own `MatrixExcuse` mechanism (a parallel but distinct concept).
