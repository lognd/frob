## Done report

T-0689/T-0931 already landed the call-site `frob:callee-raises` directive
and its resolver consumption (opaque ctypes/cffi/C-extension boundaries
fall back to it) plus the above-the-def `frob:raises` declared-propagation
directive consumed by EXHAUST002 -- but neither cross-checks a pyo3
boundary's Rust-side observed exception surface against a Python-side
declaration, and neither MANDATES a declaration exist at all on a
ctypes/cffi boundary. Nothing in that prior work is duplicated here; this
ticket supplies exactly the residual: FFI001 (pyo3 Rust-vs-.pyi cross-check
drift, reusing the existing above-the-def `frob:raises` directive as the
declaration surface) and FFI002 (mandatory callee-raises declaration on
every ctypes-loaded-handle call site, reusing the existing call-site
directive as the enforcement target). New module `frob.arch._ffi` (raw
regex scans, deliberately independent of the tree-sitter-backed
NormalizedModule adapters -- see its module docstring for why) and new gate
`frob.gates._ffi_boundary.ffi_boundary_gate`, wired into `frob.gates`'s
gate registry (`_KNOWN_GATE_RULES`, `_ALL_GATES`/`_CANONICAL_GATE_ORDER`,
the `process_jobs` dispatch table) at ERROR severity directly -- a real
run against this repo's own strata-core/frob-core crates surfaced exactly
one FFI001 finding (`worst_age`'s genuine `.expect(...)` panic site),
fixed at landing by adding `# frob:raises PanicException` to
`strata_core.pyi`, and zero FFI002 findings (no ctypes/cffi usage anywhere
in this repo today), so there is no pre-existing debt corpus forcing a
WARN-first posture the way EXHAUST001/002 needed.

`src/frob/check/__init__.py`'s `_STAGE_GROUPS` (which stage-group alias
like `gates-native`/`gates-fast` bundles `ffi_boundary` for a bare `--only
gates-native` run) is OUT of this ticket's declared scope
(`src/frob/gates/**` does not cover `src/frob/check/__init__.py`) -- the
gate is fully runnable today via its own bare name (`--only ffi_boundary`)
or as part of any `frob check` run that does not filter by stage group,
just not yet bundled into an existing named stage alias. Filed as a
follow-up (see Filed below) rather than silently expanding scope to add it.

docs/modules/arch.md was not touched (out of this ticket's declared
scope glob list, which names docs/modules/gates.md only) -- the new
gate's full design writeup lives at docs/modules/gates.md#ffi001-ffi002-t-0690
instead, and every `frob:doc` directive in the new code points there.

### Changed
```
 docs/modules/gates.md           |  68 +++++++
 src/frob/arch/_ffi.py           | 421 ++++++++++++++++++++++++++++++++++++++++
 src/frob/gates/__init__.py      |  18 ++
 src/frob/gates/_ffi_boundary.py | 206 ++++++++++++++++++++
 strata-core/strata_core.pyi     |   6 +
 tests/test_gates.py             | 126 ++++++++++++
 tickets.md                      | 165 +++++++++++++++-
 7 files changed, 1007 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestFfiBoundaryGate::test_pyo3_drift_fires_ffi001` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFfiBoundaryGate::test_pyo3_declared_matches_no_drift` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFfiBoundaryGate::test_ctypes_call_without_declaration_fires_ffi002` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFfiBoundaryGate::test_ctypes_call_with_empty_declaration_clean` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 3 error(s), 20162 warning(s), 341 waived
- error-findings: COV003@tickets/T-0698, COV003@tickets/T-1018, PRE001@tickets/T-0690
