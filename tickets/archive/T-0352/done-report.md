## Done report

Extended `frob.gates._pii_structural`'s Python-only PII010/SEC110 structural
scan (T-0207) to TypeScript/Rust field-shape and env-access equivalents, per
this ticket's mandate.

TS coverage: `interface_declaration` bodies, `type_alias_declaration`s whose
value is an `object_type`, and `class_declaration` bodies (`_scan_ts_fields`)
-- reusing `_field_name_hit`/`FIELD_SIGNATURES` unchanged (name-kind entries
only; type-kind `EmailStr`/`SecretStr` stays Python-only, an honest disclosed
gap). `process.env.NAME`/`process.env["NAME"]` and `import.meta.env.NAME`/
`import.meta.env["NAME"]` (`_scan_ts_env_access`) fire SEC110, reusing
`_ENV_VAR_ALLOWLIST` unchanged.

Rust coverage: `struct_item` named fields via `field_declaration_list`
(`_scan_rust_fields`) fire PII010; `std::env::var(...)`/`env::var(...)`/
`std::env::var_os(...)` (`_scan_rust_env_access`) fire SEC110. Tuple structs
(no source field names) are out of scope for name matching by design, not a
false negative.

NO-FAIL-SILENT (ticket mandate): a TS index signature (`[key: string]: T`)
or computed property name fires PII010 as an "unresolvable field shape"
finding demanding manual review rather than being silently skipped. A
dynamic (non-literal) `process.env[someDynamicKey]` subscript key still
fires SEC110, mirroring `_scan_python_env_access`'s existing posture for
`os.environ[dynamic_key]`.

All parsing reuses `frob.lang.raw_tree` (the single tree-sitter grammar-load
dispatch `frob.arch`/`frob.dup._legacy` already share) -- no second parser
stood up. The T-0351 declared-surface join (`_load_declared_surface`)
applies identically since it is keyed on rel_path alone, language-agnostic.

Verified manually against real TS/Rust fixtures in a scratch git repo before
writing the pytest suite: PII010 fired on interface/type-alias/class fields
named email/ssn/password/token; the index signature fired as unresolvable;
SEC110 fired on process.env.X, process.env["X"], import.meta.env.X, a
dynamic process.env[key], std::env::var, and env::var (unqualified); PATH
(allowlisted) stayed silent in both languages; clean fixtures (Widget
interface/struct with no PII-shaped names) stayed silent.

Adversarial tests: dynamic env-access key still fires (NO-FAIL-SILENT);
index signature still fires as unresolvable (NO-FAIL-SILENT); Rust tuple
struct has no field names to match (correctly silent, not a false
negative); allowlisted PATH var silent in both TS and Rust; T-0351 join
applies identically across both new languages.

Filed: T-0762 (filed by the coordinator/land process from this ticket's
disclosed gap, TS/Rust nominal PII-shaped types e.g. an `EmailStr`-like
branded type or a `SecretString`-like Rust crate type) -- left for that
follow-on ticket, not silently dropped.

REVIEWER-FLAGGED FIX (round 2): the reviewer rejected the first pass on a
real mechanical defect -- the `frob:doc`/`frob:tests`/`frob:enforces`
directive block above `pii_structural_gate` had been pushed down by the
newly-inserted `_CROSS_LANGUAGE_SCANS`/`_scan_cross_language_files` helper
code, so the directives silently rebound to that helper instead of
`pii_structural_gate` -- COV001 (missing doc edge on `pii_structural_gate`)
plus 12x COV005 (directives drifted onto the wrong symbol), unwaived, RED.
My first Done report claimed clean without having run
`uv run frob check --only coverage`; that was wrong to claim. Fixed by
moving the directive block back to immediately precede `pii_structural_gate`
(verified by reading the file, not by assumption). Re-verified for real
this time:

- `uv run frob check --ticket T-0352 --only coverage` -> `gate:COV 0
  errors, 20 warnings, 87 waived` (0 references to `_pii_structural.py`
  among the errors before the fix; after the fix, 0 COV001/COV005 hits on
  this module at all).
- `uv run frob check --ticket T-0352 --only pii_structural --only prework
  --only coverage` -> `gate:COV 0 errors`, `gate:PII 0 errors, 19
  warnings, 3 waived`, `gate:SEC 0 errors, 5 warnings, 10 waived`,
  `gate:WAIVE 0 errors`, `gate-summary 0 errors, 806 warnings, 100 waived`.
- All 17 `TestPiiStructuralCrossLanguage` tests re-run and still pass:
  `uv run pytest tests/test_gates.py -k PiiStructuralCrossLanguage -q` ->
  17 passed.
- `git diff main --diff-filter=D --stat` empty after two intervening
  `git merge main`s (main advanced twice while this fix was in flight,
  including an unrelated WAIVE002-to-error land) -- no accidental
  reverts.
- `git diff main -- tickets.md` confined to this ticket's own block only
  (verified: every `T-####` token in the diff is either T-0352 itself or
  an in-prose reference inside T-0352's own body/Done-report text, plus
  one unchanged context line for the following ticket's header).

### Changed
```
 docs/modules/gates.md             |  35 ++-
 src/frob/gates/_pii_structural.py | 436 +++++++++++++++++++++++++++++++++++++-
 tests/test_gates.py               | 254 ++++++++++++++++++++++
 tickets.md                        | 100 ++++++++-
 4 files changed, 810 insertions(+), 15 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestPiiStructuralCrossLanguage::test_ts_interface_email_field_fires` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestPiiStructuralCrossLanguage::test_ts_type_alias_password_field_fires` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestPiiStructuralCrossLanguage::test_ts_class_field_token_fires` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestPiiStructuralCrossLanguage::test_ts_clean_interface_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestPiiStructuralCrossLanguage::test_ts_index_signature_reported_not_skipped` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestPiiStructuralCrossLanguage::test_ts_process_env_fires` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestPiiStructuralCrossLanguage::test_ts_process_env_subscript_fires` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestPiiStructuralCrossLanguage::test_ts_import_meta_env_fires` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestPiiStructuralCrossLanguage::test_ts_dynamic_env_key_still_fires` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestPiiStructuralCrossLanguage::test_ts_allowlisted_env_var_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestPiiStructuralCrossLanguage::test_rust_struct_ssn_field_fires` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestPiiStructuralCrossLanguage::test_rust_clean_struct_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestPiiStructuralCrossLanguage::test_rust_env_var_fires` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestPiiStructuralCrossLanguage::test_rust_unqualified_env_var_fires` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestPiiStructuralCrossLanguage::test_rust_allowlisted_env_var_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestPiiStructuralCrossLanguage::test_rust_tuple_struct_field_not_matched` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestPiiStructuralCrossLanguage::test_ts_and_rust_findings_joined_against_declared_surface` (pytest node id, verified passing when recorded)
