# Capability registry

<a id="capability-registry"></a>

<!-- frob:describes src/frob/vet/_capability_registry.py::DangerousOperation -->

## What / where

`src/frob/vet/_capability_registry.py` (T-0158). Core symbols:

- `LANGUAGES: tuple[str, ...]` -- `("python", "typescript", "rust", "c-cpp")`.
- `CAPABILITY_KINDS: tuple[str, ...]` -- the vet-side capability vocabulary
  (net/fs/eval/env/ffi/install-hook/etc -- distinct from the threat
  catalog's CWE-sink vocabulary, see [Benign capabilities](benign-capabilities.md)).
- `DangerousOperation` (frozen: `language`, `library`, `function_or_pattern`,
  `capability_kind`, `cwe_links`, `rationale`, `safer_alternative`,
  `severity`, `needles`) built via the `_op(...)` helper.
- `DANGEROUS_OPERATIONS: tuple[DangerousOperation, ...]` -- hundreds of
  entries, one per known dangerous API/pattern per language.
- `MatrixExcuse` (frozen: `capability_kind`, `language`, `reason`) and
  `CAPABILITY_MATRIX_EXCUSES: tuple[MatrixExcuse, ...]` -- for
  (capability_kind, language) cells that are LEGITIMATELY empty (e.g.
  c-cpp has no idiomatic `eval`, `env`, `install-hook`, `html_render`,
  `sql`, `fetch_url`, `deserialize`, or `client_storage` concept).
- `NO_CAPABILITY_MODULES` -- modules deliberately excused from needing ANY
  dangerous-operation pattern (the "pure side" of the same curation).

`src/frob/vet/_capability.py::_compile_patterns` builds the scanner's
`_PATTERNS` table FROM `DANGEROUS_OPERATIONS` at import time -- adding an
operation to the registry is picked up by the scanner automatically, no
separate pattern-table edit required.

## Add-an-entry recipe

1. New dangerous operation: append an `_op(language=..., library=...,
   function_or_pattern=..., capability_kind=..., cwe_links=(...,),
   rationale=..., safer_alternative=..., severity=..., needles=(...,))`
   call to `DANGEROUS_OPERATIONS`. `needles` are the literal substrings
   the scanner matches on.
2. Legitimately-empty (capability_kind, language) cell: append a
   `MatrixExcuse(capability_kind=..., language=..., reason=...)` to
   `CAPABILITY_MATRIX_EXCUSES` instead of leaving the cell silently
   unaddressed -- the exhaustiveness matrix treats an unaddressed cell as
   a gap, not an implicit pass.
3. Module deliberately carrying no dangerous operations: add it to
   `NO_CAPABILITY_MODULES`.

## Drift-locks that fire

- The capability exhaustiveness matrix check (T-0158): every
  (capability_kind, language) pair must have >=1 `DangerousOperation` OR a
  `MatrixExcuse` -- no cell may be silently absent.

## Worked example diff

```python
# src/frob/vet/_capability_registry.py, in DANGEROUS_OPERATIONS:
_op(
    language="python",
    library="pickle",
    function_or_pattern="pickle.loads",
    capability_kind="deserialize",
    cwe_links=("CWE-502",),
    rationale="deserializing untrusted bytes can execute arbitrary code",
    safer_alternative="use json or a schema-validated format for untrusted input",
    severity="critical",
    needles=("pickle.loads(", "pickle.load("),
),
```

## Common mistakes

- **Leaving a matrix cell unaddressed instead of excusing it.** c-cpp's
  eight excused kinds (`eval`, `env`, `install-hook`, `html_render`,
  `sql`, `fetch_url`, `deserialize`, `client_storage`) are all explicit
  `MatrixExcuse` entries with a reason, not gaps the matrix silently
  tolerates -- an unaddressed cell fails the exhaustiveness check exactly
  like a missing `DangerousOperation` would.
- **Confusing this vocabulary with the threat catalog's.** Design-lint's
  LINT004 deliberately uses a NARROWER `RISKY_CAPABILITY_KINDS` subset of
  this registry's kinds, not the full sink taxonomy from `_threat.py` --
  do not assume "capability kind" means the same enumerable set across
  every consumer module.

## See also

- [Benign capabilities](benign-capabilities.md) -- `BenignCapability`,
  the threat-catalog-side analog of `MatrixExcuse`, a different
  vocabulary and mechanism.
- [Design-lint rules](design-lint-rules.md) -- LINT004's narrower reuse of
  this registry's kinds.
