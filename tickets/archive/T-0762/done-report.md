## Done report

## Done report

Changed:
- src/frob/gates/_pii_structural.py::_FieldSignature (added `langs` field)
- src/frob/gates/_pii_structural.py::_sig (added `langs` parameter)
- src/frob/gates/_pii_structural.py::_CROSS_LANG_TYPE_SIGNATURES (new module constant)
- src/frob/gates/_pii_structural.py::_ALL_TYPE_SIGNATURES (new module constant)
- src/frob/gates/_pii_structural.py::_type_hit (new shared lookup)
- src/frob/gates/_pii_structural.py::_field_type_hit (refactored onto _type_hit)
- src/frob/gates/_pii_structural.py::_type_identifier_names (new shared TS/Rust type-subtree walker)
- src/frob/gates/_pii_structural.py::_ts_type_hit (new)
- src/frob/gates/_pii_structural.py::_rust_type_hit (new)
- src/frob/gates/_pii_structural.py::_scan_ts_fields (wired in _ts_type_hit)
- src/frob/gates/_pii_structural.py::_scan_rust_fields (wired in _rust_type_hit)
- tests/test_gates.py::TestPiiStructuralCrossLanguage (6 new tests)
- docs/modules/gates.md (T-0762 section documenting the new type-kind behavior)

Evidence (all bound with --accepts 0, all measured passing via `uv run pytest tests/test_gates.py -k TestPiiStructuralCrossLanguage -n0 -v`: "23 passed"):
- tests/test_gates.py::TestPiiStructuralCrossLanguage::test_ts_secret_wrapper_type_field_fires
- tests/test_gates.py::TestPiiStructuralCrossLanguage::test_ts_branded_email_type_field_fires
- tests/test_gates.py::TestPiiStructuralCrossLanguage::test_ts_plain_string_field_type_does_not_fire
- tests/test_gates.py::TestPiiStructuralCrossLanguage::test_rust_secrecy_secretstring_type_field_fires
- tests/test_gates.py::TestPiiStructuralCrossLanguage::test_rust_secret_newtype_type_field_fires
- tests/test_gates.py::TestPiiStructuralCrossLanguage::test_rust_plain_string_field_type_does_not_fire

Also ran the pre-existing full test_pii_structural_gate.py + test_gates.py suites unchanged: "656 passed" combined (measured via `uv run pytest tests/test_pii_structural_gate.py tests/test_gates.py -p no:cacheprovider -q`, all dots, no failures).

Filed: none. No out-of-scope discoveries required a new ticket -- the one near-miss (needing to touch tests/test_pii_structural_gate.py's generic TestDriftLock to keep it passing) was avoided by design: the new TS/Rust-only TYPE-kind entries live in a separate `_CROSS_LANG_TYPE_SIGNATURES` table, not mixed into `FIELD_SIGNATURES`, so `TestDriftLock`'s per-entry Python-fixture parametrize never sees them and needed no edit. This kept the change entirely inside the ticket's declared scope (src/frob/gates/_pii_structural.py, tests/test_gates.py, docs/modules/gates.md).

Gates: `FROB_AGENT=1 FROB_WORKTREE=<worktree> uv run frob check --ticket T-0762 --only <stage>` clean for all 5 stage groups (lint, static, gates-fast, gates-native, gates-security) -- 0 errors on every stage. `static`'s "static" stage shows only pre-existing unrelated frob-exports findings (23+ symbols across arch/lang/mutate/perf/scaffold/serve/testing/vet, none in scope for this ticket). `gates-fast` initially failed with COV002 (a frob:doc directive riding onto a private symbol during the edit) and PRE001 (stale pre-work sweep) -- both fixed (removed the stray directive; re-ran `frob ticket sweep T-0762`), then re-verified clean.

Scope: `git diff main --diff-filter=D --stat` is empty (no deletions).

### Changed
```
 docs/modules/gates.md             |  38 ++++++-
 src/frob/gates/_pii_structural.py | 201 +++++++++++++++++++++++++++++++++-----
 tests/test_gates.py               |  91 +++++++++++++++++
 tickets.md                        |  17 +++-
 4 files changed, 316 insertions(+), 31 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestPiiStructuralCrossLanguage::test_ts_secret_wrapper_type_field_fires` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestPiiStructuralCrossLanguage::test_ts_branded_email_type_field_fires` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestPiiStructuralCrossLanguage::test_ts_plain_string_field_type_does_not_fire` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestPiiStructuralCrossLanguage::test_rust_secrecy_secretstring_type_field_fires` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestPiiStructuralCrossLanguage::test_rust_secret_newtype_type_field_fires` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestPiiStructuralCrossLanguage::test_rust_plain_string_field_type_does_not_fire` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
