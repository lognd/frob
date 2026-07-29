# Compliance registry

<a id="compliance-registry"></a>

<!-- frob:describes src/frob/strata/_compliance.py::RegulationEntry -->

## What / where

`src/frob/strata/_compliance.py`. `RegulationEntry` (frozen catalog entry)
and `OutOfScopeRegulation` populate `COMPLIANCE_CATALOG: tuple[
RegulationEntry, ...]` (7 entries at time of writing: COPPA, GDPR erasure,
retention, lawful-basis, HIPAA BAA, minimization, PRIVACY-NOTICE). Unlike
the threat catalog, compliance has TWO levels of extension:

- **Catalog data** (id/attrs/cite) -- pure data, one tuple entry.
- **Discharge logic** -- a dedicated `_check_<regulation>` function
  (`_check_coppa`, `_check_erasure`, `_check_retention`,
  `_check_lawful_basis`, `_check_baa`, `_check_minimization`,
  `_check_privacy_notice`), each wired individually into
  `check_regulation_discharge`/`evaluate_compliance`.

Adding a catalog entry does NOT automatically get you a discharge check --
those are bespoke functions, not data-driven.

## Add-an-entry recipe

1. **Catalog only** (id exists in a baseline VIEW, needs a home): append a
   `RegulationEntry(id=..., ...)` to `COMPLIANCE_CATALOG`, or an
   `OutOfScopeRegulation(id=..., reason=...)` if deliberately excluded.
2. **New discharge rule**: write a `_check_<name>(model: KernelModel) ->
   tuple[ComplianceViolation, ...]` function following the existing
   checkers' shape, then wire it into `check_regulation_discharge`. This
   is new code, not a registry append -- do not attempt to shoehorn a
   discharge rule into `COMPLIANCE_CATALOG`'s data shape.

## Drift-locks that fire

- `check_regulation_catalog_completeness`: every baseline-named regulation
  id needs a `RegulationEntry` or `OutOfScopeRegulation` -- catalog-level
  only, does NOT verify a discharge checker exists for it.

## Worked example diff

```python
# src/frob/strata/_compliance.py, in COMPLIANCE_CATALOG:
RegulationEntry(
    id="CCPA-1798.100",
    title="California Consumer Privacy Act -- right to know",
    cite="https://leginfo.legislature.ca.gov/...",
    attrs=("jurisdiction=us-ca", "subject=disclosure"),
),
```

Catalog completeness now passes for this id; if no `_check_ccpa_*`
function exists, `check_regulation_discharge` silently has no opinion on
it -- file a follow-up ticket for the discharge checker rather than
writing one as a documentation side-effect (this ticket fixes nothing
beyond doc anchors).

## Common mistakes

- **Assuming catalog completeness implies discharge coverage.** They are
  independent checks; a passing `check_regulation_catalog_completeness`
  says nothing about whether `evaluate_compliance` can actually verify
  the regulation against a model.
- **Duplicating a jurisdiction-specific rule into a baseline check.**
  Mirrors the [PII categories](pii-categories.md) precedent: `_check_
  retention` is documented as the jurisdiction-agnostic baseline, with
  jurisdiction-specific tightening (e.g. EU) layered as a SEPARATE check
  rather than widened into the baseline's default.

## See also

- [Threat catalog](threat-catalog.md) -- the closer-to-pure-data sibling
  registry; contrast its recipe with compliance's two-level extension.
- [PII categories](pii-categories.md)
