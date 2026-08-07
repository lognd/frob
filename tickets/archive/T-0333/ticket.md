---
id: T-0333
title: collection cache blind to native-extension build state -> stale COV003 + misleading
  remedy
state: done
kind: bug
origin: human
created: '2026-07-19'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/testing/_collect.py
- src/frob/testing/_runners.py
- src/frob/testing/_models.py
- src/frob/testing/__init__.py
- src/frob/gates/__init__.py
- src/frob/app/config.py
- src/frob/app/test_runner.py
- src/frob/__main__.py
- tests/**
- docs/**
- frob.toml
- pyproject.toml
- .frob-release.json
- tickets.md
- CHANGELOG.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_testing.py::TestNativeFingerprint::test_fingerprint_changes_absent_to_built
- tests/test_testing.py::TestNativeFingerprint::test_fingerprint_changes_on_rebuild
- tests/test_testing.py::TestNativeFingerprint::test_single_file_extension_fingerprinted
- tests/test_gates.py::TestCoverageGate::test_cov003_names_unbuilt_native_as_remedy
- tests/test_gates.py::TestCoverageGate::test_cov003_honest_remedy_when_no_native_missing
designated_repro_test: null
acceptance:
- text: given a repo whose test suite importorskip-gates on a native extension, when
    the extension is built (or rebuilt) after a prior collection ran with it absent,
    then collect_python_tests re-collects automatically (cache key reflects the native
    artifact hash) and the newly-collected tests resolve COV003 without any manual
    cache deletion
  evidence: []
- text: 'given a declared native module that is genuinely not built, when frob check
    runs the coverage gate, then the finding names the missing native module and its
    build command (e.g. ''native extension strata_core not built; run make core'')
    rather than the current false ''run: frob test --collect to refresh'' pointing
    at a nonexistent flag'
  evidence: []
- text: given the fingerprint mechanism, when the same design is used on a Python/C
    or Python/C++ project (setuptools/pybind11/scikit-build compiled .so/.pyd), then
    build-state changes invalidate the collection cache identically to the Rust/pyo3/maturin
    case (the fingerprint hashes the compiled artifact, not the toolchain)
  evidence: []
threat: null
component: null
---
ROOT CAUSE (diagnosed 2026-07-19, recurring footgun): collect_python_tests in src/frob/testing/_collect.py caches pytest --collect-only node ids keyed on _content_key(), a sha256 over test-FILE bytes only. Building a native extension changes NO test file, so a collection captured while the native was unbuilt -- where pytest.importorskip('strata_core') SKIPS the kernel-property tests, so they never enter the collected set -- is reused indefinitely. Result: after 'make core' builds strata_core, COV003 still fires ('evidence does not resolve to a collected test') on evidence that IS correctly bound, blocking ticket closes (hit on T-0288). Today the only remedy is manually 'rm .frob/pytest-collect.json'. Worse, the COV003 message tells the user to 'run: frob test --collect to refresh' -- a flag that DOES NOT EXIST. This is the strata_core/frob_core 'worktree-natives artifact' generalized: any importorskip-gated native (Rust via pyo3/maturin OR C/C++ via setuptools/pybind11/scikit-build) poisons the cache.

DESIGN (three parts, language-agnostic):

(1) NATIVE-BUILD FINGERPRINT folded into the collection cache key. Extend the cache key so it incorporates the state of the project's declared native extension modules. For each module: importlib.util.find_spec(name); if found with a compiled origin (.so/.pyd/.dylib), hash the artifact bytes (or size+mtime for speed, content-hash for correctness); if not found, record 'absent'. Fold this into _content_key (or a sibling term unioned into the key). Because it fingerprints the COMPILED OUTPUT, it is identical across Rust (maturin/pyo3) and C/C++ (setuptools/pybind11/scikit-build/meson) -- unbuilt->built or any recompile flips the key and forces re-collection automatically.

(2) DECLARE native modules in frob.toml. Add a [[native]] table (or [testing].native_modules) parsed alongside [[test.runner]] in src/frob/testing/_runners.py: name (import name, e.g. 'strata_core'), build_cmd (e.g. 'make core'), optional language. Source of truth is explicit config (honest, cross-language, no fragile build-manifest parsing). OPTIONAL follow-up: auto-discover from */Cargo.toml (pyo3/cdylib crate-type) and pyproject [tool.maturin]/ext-modules -- file as a separate ticket if not done here.

(3) ACTIONABLE DIAGNOSTIC + honest remedy. When the coverage gate would fire COV003 on evidence whose module is a DECLARED native that find_spec reports ABSENT, emit a distinct finding naming the module and build_cmd instead of the misleading COV003 -- an unbuilt declared native is an ENVIRONMENT gap, not a ticket defect, and must not red a bound-evidence ticket the same way a typo'd node id does. Also FIX the lying message: either implement 'frob test --collect' (force cache drop + recollect) as the real escape hatch, or replace the message text with the true remedy. Prefer implementing --collect (first-class 'refresh collection' verb) since part (1) makes it rarely needed but it should exist and be honest.

Keep parts orthogonal and testable in isolation: (1) is a pure cache-key change (unit-testable by toggling a fake artifact hash), (2) is config parsing, (3) is gate message routing. See memory 'worktree-natives-artifact'.