# Threat catalog

<a id="threat-catalog"></a>

<!-- frob:describes src/frob/strata/_threat_models.py::WeaknessEntry -->

## What / where

`src/frob/strata/_threat_catalog_cwe.py` holds the `std.cwe` catalog: a conditional
obligation predicated on a capability being present in a strata model
(docs/strata/threat.md#the-core-reframe). Two SEPARATE catalogs exist as
distinct views, not one shared list:

- `CWE_CATALOG: tuple[WeaknessEntry, ...]` -- the security family.
- `QUALITY_CATALOG: tuple[WeaknessEntry, ...]` -- the quality family.

Supporting types: `WeaknessEntry` (frozen, `id`/`title`/`cite`/`family`/
`capability_kind`/`mitigation`/`rung`), `OutOfScopeEntry` (a baseline CWE
id explicitly excluded, with a `reason`), `BenignCapability` (a `may`
capability kind excused from THREAT002's sink taxonomy -- its own
registry, see [Benign capabilities](benign-capabilities.md)) and
`DEFAULT_BENIGN_CAPABILITIES: tuple[BenignCapability, ...]`.

## Add-an-entry recipe

1. Decide which family the new CWE belongs to: security (`CWE_CATALOG`)
   or quality (`QUALITY_CATALOG`). They are joined INDEPENDENTLY by
   `_evaluate_family` -- an entry in one does not satisfy the other.
2. Append a `WeaknessEntry(id="CWE-xxx", title=..., cite=<authoritative
   source url>, capability_kind=<may-atom kind or None>, mitigation=<
   required boundary predicate name>, rung=Rung.Lx)` to the chosen tuple.
   `cite` must never be hand-transcribed prose -- link the source.
3. If the id is deliberately NOT cataloged (e.g. out of scope for this
   codebase), add an `OutOfScopeEntry(id=..., reason=...)` instead of a
   `WeaknessEntry`.
4. If a `may` capability kind has no sink mapping in the family you are
   touching, add a `BenignCapability(kind=..., reason=...)` -- see
   [Benign capabilities](benign-capabilities.md) for why this can be a
   no-op in one family and load-bearing in the other.

## Drift-locks that fire

- **THREAT001** (catalog completeness): every CWE id a selected baseline
  VIEW names must have a `WeaknessEntry` or an `OutOfScopeEntry`.
- **THREAT002** (precondition/capability completeness, model-level):
  every capability kind a node declares via `may` must be CLASSIFIED --
  named as a sink in `_entries_by_capability_kind` or excused via
  `BenignCapability`. Unclassified fails closed (charter law 2).
- **THREAT003** (discharge completeness): every FIRED obligation needs a
  `Claim` at or above the catalog's `rung`, never REFUTED. As of the
  Phase C tightening, a `NoFlow` claim discharging a weakness must PROVE
  as a genuine mitigation chokepoint (`_mitigation_is_chokepoint`), not
  merely exist -- see Common mistakes below.
- **THREAT004/THREAT005** (code-level mirrors of THREAT002): join
  `_effects.py::extract_effects`'s observed net/fs/exec sinks into the
  same taxonomy; an observed sink with no matching `may` declaration is
  THREAT004, an unrecognized-and-unexcused kind is THREAT005.

## Worked example diff

```python
# src/frob/strata/_threat_catalog_cwe.py, in CWE_CATALOG:
WeaknessEntry(
    id="CWE-943",
    title="Improper Neutralization of Special Elements in Data Query Logic",
    cite="https://cwe.mitre.org/data/definitions/943.html",
    capability_kind="nosql",
    mitigation="output_encoding",
    rung=Rung.L4,
),
```

After this, THREAT001 requires every baseline VIEW naming CWE-943 to
resolve against this entry; any node declaring a `may nosql` capability
now auto-instantiates this obligation for THREAT003.

## Common mistakes

- **Widening the wrong catalog instead of an excuse.** See
  [Benign capabilities](benign-capabilities.md) for the canonical
  `DEFAULT_BENIGN_CAPABILITIES` `exec`-entry example of this trap.
- **Treating any claim as discharge.** THREAT003 originally accepted any
  `NoFlow` claim proven at the right rung as sufficient. Review caught
  that `reachable`'s boundary test ignores `direction`/`predicate`, so a
  `declassify` boundary with an unrelated predicate (e.g.
  `"legal_review_signed_off"`) could prove the exact same `NoFlow` a
  genuine `endorse output_encoding` boundary would. `_mitigation_is_
  chokepoint` now re-evaluates the claim on a model restricted to ONLY
  the correctly-kinded boundaries before accepting discharge.

## See also

- `docs/strata/threat.md` -- full design rationale and phasing history.
- [Benign capabilities](benign-capabilities.md)
- [Capability registry](capability-registry.md)
- [CVE fingerprints](cve-fingerprints.md) -- fingerprints join `cwe_id`
  against this catalog; add the `WeaknessEntry` here first.
