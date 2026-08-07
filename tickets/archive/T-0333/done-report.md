## Done report

Implemented all three design parts; reviewer-pending (not self-closed).

Changed (all within scope):
- `src/frob/testing/_models.py`: new frozen `NativeSpec` (name/build_cmd/
  language); `CollectedTests` gains `missing_natives: tuple[NativeSpec, ...]`.
- `src/frob/testing/_runners.py`: `load_natives(root)` parses the new
  `frob.toml` `[[native]]` table (missing table -> Ok(()), malformed ->
  Err(BadRunnerSpec)).
- `src/frob/testing/_collect.py`: `_native_artifact_digest` /
  `_native_fingerprint` / `_compiled_artifacts` / `_missing_natives` /
  `_collection_cache_key`; the pytest collection cache key now unions the
  test-file content hash with a fingerprint over each declared native's
  COMPILED artifacts (`.so`/`.pyd`/`.dylib`, resolved via
  `importlib.util.find_spec`). Handles both the maturin PACKAGE layout
  (origin is `__init__.py`; the real `.so` sits alongside it and is what
  gets hashed) and the single-file C/C++ extension layout (origin IS the
  `.so`). `drop_collection_cache(root)` backs the new `frob test --collect`.
  `collect_python_tests` populates `missing_natives`.
- `src/frob/gates/__init__.py`: COV003 now routes through
  `_missing_native_remedy` -- when a declared native is unbuilt it names the
  module and its `build_cmd` instead of blaming the evidence id; the
  non-native remedy references the real ``frob test --collect``, not the
  nonexistent flag it used to print.
- `src/frob/__main__.py` + `src/frob/app/config.py` +
  `src/frob/app/test_runner.py`: `frob test --collect` (drop + re-collect).
- `frob.toml`: `[[native]]` entries for `strata_core` and `frob_core`.
- `docs/modules/testing.md`: new "Native extensions" section + API/model
  entries. `CHANGELOG.md` [0.13.0]; `pyproject.toml` 0.12.0 -> 0.13.0 (REL001
  minor bump for the additive API); `.frob-release.json` re-stamped.

Cross-platform: the fingerprint matches `.so` (Linux), `.pyd` (Windows),
`.dylib` (macOS) anywhere in the filename, so platform/arch tags
(cp311-win_amd64, abi3, aarch64, x86_64) all match; it is toolchain-agnostic
because it hashes the compiled OUTPUT, not any build manifest.

Validated live: mid-implementation a uv re-sync (triggered by a pyproject
dep edit) UNINSTALLED the editable maturin natives -- exactly the failure
class this ticket targets. After `make core`, the T-0333 fingerprint
auto-invalidated the stale collection cache (absent-hash -> artifact-hash)
with no manual `rm`, confirming AC1 end to end.

Evidence: 18 tests in `tests/test_testing.py::TestNativeFingerprint`
(load_natives parse/missing/malformed; absent vs built vs rebuilt
fingerprint; single-file vs package layout; missing_natives; drop-cache
success/idempotent/OSError; find_spec-raises) + 2 in
`tests/test_gates.py::TestCoverageGate` (COV003 names the unbuilt native +
build_cmd; honest non-native remedy). `frob test --collect` exercised
against the real tree (2893 node ids, 0 missing).

Gates: `make coverage` green; ruff check + `ruff format --check` clean on all
changed files; `ty check` clean; REL001 clean after the bump + stamp. The
only full-check error observed was a transient SYS004 during the native-nuke
window, resolved by the rebuild.
