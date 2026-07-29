# PII categories

<!-- frob:describes src/frob/strata/_pii.py::PiiViolation -->

## What / where

`src/frob/strata/_pii.py` (T-0154). `_PII_PREFIX = "pii="` -- the tag
convention (`pii=<category>.<field>`, e.g. `pii=identifier.email`),
shared with the `code=`/`skew=` attr-desugar convention in
`_code_binding.py`. `PII_CATEGORIES: frozenset[str]` is the flat category
vocabulary. Rules: PII001 (catalog), PII002 (boundary-crossing
protection), PII003 (retention/erasure join, jurisdiction-agnostic
baseline), PII004 (undeclared-PII lint).

## Add-an-entry recipe

1. Add the new category string to the `PII_CATEGORIES` frozenset.
2. Tag nodes with `pii=<category>.<field>` in the design file; `_pii_
   category` splits on the first `.` to resolve the category.
3. Do NOT hand-roll a jurisdiction-specific variant of an existing
   category (e.g. `identifier.email.eu`) -- jurisdiction tightening is a
   SEPARATE check layered on top of the baseline (PII003's model), not a
   category-string convention.

## Drift-locks that fire

- **PII001**: any `pii=` tag whose category prefix is not in
  `PII_CATEGORIES` fires -- deny-by-default on unknown categories.
- **PII002/PII003/PII004** consume the category only indirectly (via
  `node_carries_pii`/`node_pii_tags`); adding a category does not by
  itself change their behavior beyond making PII001 stop firing on it.

## Worked example diff

```python
# src/frob/strata/_pii.py, in PII_CATEGORIES:
PII_CATEGORIES: frozenset[str] = frozenset(
    (
        "identifier",
        "financial",
        "health",
        "biometric",  # new
        ...
    )
)
```

## Common mistakes

- **Baking jurisdiction into the category name.** PII003 is explicitly
  documented as the jurisdiction-agnostic baseline ("if you carry PII you
  need SOME retention story"), with EU-specific tightening layered
  separately -- a model can fail PII003 and pass the EU layer's stricter
  test independently. This is the same "separate views, not widened
  defaults" precedent as the threat catalog's security/quality split
  ([threat-catalog.md](threat-catalog.md)) and mirrors the compliance
  catalog's baseline-vs-jurisdiction split
  ([compliance-registry.md](compliance-registry.md)).

## See also

- [Threat catalog](threat-catalog.md) -- the separate-views precedent.
- [Compliance catalog](compliance-registry.md)
