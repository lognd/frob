# Capability registry

<a id="capability-registry"></a>

<!-- frob:describes src/frob/vet/_capability_registry/_schemas.py::_DangerousOperation -->

## What / where

`src/frob/vet/_capability_registry/` (T-0158; split into a package by
T-1420 once the single file crossed 800 lines). Import from the package's
top level (`from frob.vet._capability_registry import X`) -- every symbol
below is re-exported through `__init__.py`, so callers never need to know
which submodule actually defines it. Core symbols, and their current home:

- `LANGUAGES: tuple[str, ...]` (`_kinds.py`) -- `("python", "typescript", "rust", "c-cpp", "kotlin")`.
- `CAPABILITY_KINDS: tuple[str, ...]` (`_kinds.py`) -- the vet-side
  capability vocabulary (net/fs/eval/env/ffi/install-hook/etc -- distinct
  from the threat catalog's CWE-sink vocabulary, see
  [Benign capabilities](benign-capabilities.md)).
- `_DangerousOperation` (`_schemas.py`, frozen: `language`, `library`,
  `function_or_pattern`, `capability_kind`, `cwe_links`, `rationale`,
  `safer_alternative`, `severity`, `needles`) built via the `_op(...)`
  helper (also `_schemas.py`).
- `DANGEROUS_OPERATIONS: tuple[_DangerousOperation, ...]` (`_matrix.py`,
  assembled from `_dangerous_ops_python.py`'s `_PYTHON_OPERATIONS` and
  `_dangerous_ops_other.py`'s `_OTHER_OPERATIONS`) -- hundreds of entries,
  one per known dangerous API/pattern per language.
- `_MatrixExcuse` (`_schemas.py`, frozen: `capability_kind`, `language`,
  `reason`) and `CAPABILITY_MATRIX_EXCUSES: tuple[_MatrixExcuse, ...]`
  (`_matrix.py`) -- for (capability_kind, language) cells that are
  LEGITIMATELY empty (e.g. c-cpp has no idiomatic `eval`, `env`/
  `env-read`/`env-write`, `install-hook`, `html_render`, `sql`,
  `fetch_url`, `deserialize`, or `client_storage` concept).
- `NO_CAPABILITY_MODULES` (`_matrix.py`) -- modules deliberately excused
  from needing ANY dangerous-operation pattern (the "pure side" of the
  same curation).

`src/frob/vet/_capability.py::_compile_patterns` builds the scanner's
`_PATTERNS` table FROM `DANGEROUS_OPERATIONS` at import time -- adding an
operation to the registry is picked up by the scanner automatically, no
separate pattern-table edit required.

## Add-an-entry recipe

1. New dangerous operation: append an `_op(language=..., library=...,
   function_or_pattern=..., capability_kind=..., cwe_links=(...,),
   rationale=..., safer_alternative=..., severity=..., needles=(...,))`
   call to `_PYTHON_OPERATIONS` in `_dangerous_ops_python.py` (python) or
   `_OTHER_OPERATIONS` in `_dangerous_ops_other.py` (typescript/rust/
   kotlin/c-cpp) -- both feed the combined `DANGEROUS_OPERATIONS` table in
   `_matrix.py`. `needles` are the literal substrings the scanner matches
   on.
2. Legitimately-empty (capability_kind, language) cell: append a
   `_MatrixExcuse(capability_kind=..., language=..., reason=...)` to
   `CAPABILITY_MATRIX_EXCUSES` (`_matrix.py`) instead of leaving the cell
   silently unaddressed -- the exhaustiveness matrix treats an
   unaddressed cell as a gap, not an implicit pass.
3. Module deliberately carrying no dangerous operations: add it to
   `NO_CAPABILITY_MODULES` (`_matrix.py`).

## Drift-locks that fire

- The capability exhaustiveness matrix check (T-0158): every
  (capability_kind, language) pair must have >=1 `_DangerousOperation` OR a
  `_MatrixExcuse` -- no cell may be silently absent.

## Worked example diff

```python
# src/frob/vet/_capability_registry/_dangerous_ops_python.py, in _PYTHON_OPERATIONS:
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
  ten excused kinds (`eval`, `env`, `env-read`, `env-write`,
  `install-hook`, `html_render`, `sql`, `fetch_url`, `deserialize`,
  `client_storage`) are all explicit `_MatrixExcuse` entries with a
  reason, not gaps the matrix silently tolerates -- an unaddressed cell
  fails the exhaustiveness check exactly like a missing
  `_DangerousOperation` would.
- **Confusing this vocabulary with the threat catalog's.** Design-lint's
  LINT004 deliberately uses a NARROWER `RISKY_CAPABILITY_KINDS` subset of
  this registry's kinds, not the full sink taxonomy from `_threat.py` --
  do not assume "capability kind" means the same enumerable set across
  every consumer module.

## See also

- [Benign capabilities](benign-capabilities.md) -- `BenignCapability`,
  the threat-catalog-side analog of `_MatrixExcuse`, a different
  vocabulary and mechanism.
- [Design-lint rules](design-lint-rules.md) -- LINT004's narrower reuse of
  this registry's kinds.
