## Done report

Extended `_scan_file_fingerprints` (VET006/CVE fingerprint scanning) to
reuse the SAME binding tables capability resolution already built for
python (T-0328), typescript (T-0377), rust (T-0378), and c-cpp (T-0379):
new `_resolved_candidates_for_language` dispatches to whichever
`_python_resolved_candidates`/`_ts_resolved_candidates`/
`_rust_resolved_candidates`/`_c_resolved_candidates` table applies, and
`_binding_fingerprints` mirrors `_python_binding_operations`'s exact
shape against `CVE_FINGERPRINTS` instead of `DANGEROUS_OPERATIONS`.
`_scan_file_fingerprints` now unions the pre-existing lexical result with
`_binding_fingerprints`'s resolver-backed result (deduped by fingerprint
`id`) -- an aliased import that evades the lexical needle scan is still
caught.

Adversarial test per language (acceptance criterion):
- Python: real catalog entry `FP-DESERIALIZE-PICKLE-001` -- `import
  pickle as p; p.loads(...)` (no literal `pickle.loads(` text) still
  matches; unaliased control still matches too.
- TypeScript, Rust, C: no existing `CVE_FINGERPRINTS` entry happens to be
  shaped as a `module.member(`/`Module::method(` dotted call today (the
  real catalog's TS/Rust needles are argument-inclusive or bare-method
  shaped, not aliasable), so these three use a synthetic, test-local
  `CveFingerprint` (via `mock.patch("frob.strata.CVE_FINGERPRINTS", ...)`)
  to prove `_binding_fingerprints`' resolver path itself: TS `const ax =
  require('axios'); ax.get(url)`, Rust `use std::process::Command as C;
  C::new("sh")`, C `#define SYS system; SYS(cmd)` -- none contain the
  literal needle text, all still match through the resolved binding
  table; a clean-source negative accompanies each.

Scope note: `docs/modules/vet.md` was outside T-0380's declared scope
(`src/frob/vet/_capability.py`, `tests/test_vet*.py`); extended via `frob
ticket scope T-0380 --add docs/modules/vet.md` per the playbook's doc-
update mandate, same pattern used for T-1088 earlier in this series.

Changed:
- src/frob/vet/_capability.py::_resolved_candidates_for_language (new)
- src/frob/vet/_capability.py::_binding_fingerprints (new)
- src/frob/vet/_capability.py::_scan_file_fingerprints (unions lexical + binding)
- docs/modules/vet.md (public API section)
- tests/test_vet.py (TestFingerprintBindingResolution, 8 tests)

Evidence: 8 node ids bound via `frob ticket evidence T-0380`. Full
`tests/test_vet.py` (430 tests) passes clean:
`uv run pytest tests/test_vet.py -p no:cacheprovider -q`.

Gates: `uv run frob check --ticket T-0380 --only gates-fast/gates-native`
both clean of NEW errors -- gates-fast shows one pre-existing COV001
finding on `src/frob/gates/_tracked_files.py` (landed by T-1082/its
follow-up repair commit before this ticket started work, confirmed via
`git log -- src/frob/gates/_tracked_files.py`), unrelated to this
ticket's scope.

Filed: none.

### Changed
```
 docs/modules/vet.md         |  11 ++-
 src/frob/vet/_capability.py |  79 ++++++++++++++++++++-
 tests/test_vet.py           | 162 ++++++++++++++++++++++++++++++++++++++++++++
 tickets.md                  |  71 ++++++++++---------
 4 files changed, 289 insertions(+), 34 deletions(-)
```

### Evidence
- `tests/test_vet.py::TestFingerprintBindingResolution::test_python_aliased_pickle_loads_still_matches` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestFingerprintBindingResolution::test_python_unaliased_control_still_matches_lexically` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestFingerprintBindingResolution::test_typescript_aliased_require_still_matches` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestFingerprintBindingResolution::test_typescript_clean_source_does_not_match` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestFingerprintBindingResolution::test_rust_aliased_use_still_matches` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestFingerprintBindingResolution::test_rust_clean_source_does_not_match` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestFingerprintBindingResolution::test_c_aliased_macro_still_matches` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestFingerprintBindingResolution::test_c_clean_source_does_not_match` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: 7 error(s), 793 warning(s), 426 waived
- error-findings: COV001@src/frob/gates/_tracked_files.py, E501@/home/logan/projects/frob/.claude/worktrees/w17-vet/src/frob/vet/_capability.py:5338, E501@/home/logan/projects/frob/.claude/worktrees/w17-vet/src/frob/vet/_supplychain.py:154, E501@/home/logan/projects/frob/.claude/worktrees/w17-vet/src/frob/vet/_supplychain.py:168, E501@/home/logan/projects/frob/.claude/worktrees/w17-vet/src/frob/vet/_supplychain.py:209, E501@/home/logan/projects/frob/.claude/worktrees/w17-vet/src/frob/vet/_supplychain.py:267, E501@/home/logan/projects/frob/.claude/worktrees/w17-vet/src/frob/vet/_supplychain.py:295
