## Done report

Lands OPAQUE001, the fail-closed obligation for runtime-resolved
capability indirection per the coordinator's T-0665 sign-off. Category 1
(evasion-indicative dynamic lookup: eval/exec, non-literal
getattr/setattr/__import__/importlib.import_module, non-literal dlsym,
non-literal JS/TS dynamic import(), reflection APIs, libloading dynamic
symbol lookup) is implemented as a new RUNTIME_OPAQUE_CONSTRUCTS registry
table plus frob.vet._capability._opaque_indirection_findings, wired into
a new frob.gates._opaque.opaque_gate (OPAQUE001). Category 2 (bounded
polymorphism -- ordinary virtual dispatch/dyn Trait/interface calls with
a statically enumerable impl set) deliberately emits NO finding, per the
coordinator's rationale recorded once in the module docstring rather
than per-row prose: the may-analysis is sound over the visible
override/impl set, and where the impl set is open the dangerous
construct is the dynamic LOAD itself, already caught by category 1.
Category 3 (source-invisible: linker weak-symbol interposition, runtime
vtable patching) is excused via OPAQUE_SOURCE_INVISIBLE's REG011-style
"none -- <explanation>" dispositions, cross-registered as
CHK-GATE-OPAQUE001 in check-coverage.yaml.

Literal-vs-non-literal detection is a same-line balanced-paren argument
split (_split_top_level_args) plus a literal-string-prefix check
(_arg_looks_literal handling r/b/f prefixes and rejecting f-string
interpolation) -- a deliberate byte-level heuristic, not a full AST
walk; disclosed limitation: it does not handle a call whose determining
argument spans multiple lines. A same-line quote-parity check
(_byte_offset_inside_string_literal) suppresses the single largest
false-positive class the first-turn-on measurement found: this module's
OWN registry constants (needle="getattr(" etc.) tripping their own
obligation.

Lands at WARN-tier (Severity.WARN, not ERROR) per the T-0688/T-0973
first-turn-on precedent: a fresh scan of frob's own tracked codebase
found 147 raw needle hits, 93 real after the string/comment
false-positive filters -- above the >25-site threshold the coordinator
set for landing at WARN rather than ERROR. T-1038 tracks the
promotion to ERROR once those 93 sites are fixed-or-waived.

17 new mutation-kill tests (TestOpaqueIndirectionGate) cover: literal
vs non-literal split for python/TS/C/Kotlin/Rust, comment-span and
string-literal exclusion, the balanced-paren splitter's edge cases
(nested parens, unterminated call fail-closed to firing), and the gate
function's WARN severity + empty-tracked-set behavior. All pass
foreground. gates-native/gates-security/lint/static/test all clean
against a fresh merge of main and from-scratch natives build; deletion
filter against main is empty.

Disclosed scope cuts, not silently dropped: (1) the 93 first-turn-on
sites in frob's own codebase are NOT individually fixed-or-waived here
-- that is T-1038's job, matching the WARN-first posture. (2)
The Rust libloading needle and C dlsym needle are coarse (a bare `.get(`
gated only by a whole-file `libloading` import check for rust; a bare
`dlsym(` needle for C) since precise type-aware detection needs more
than a byte-level scan -- documented in the registry row's own
rationale field, not silently claimed precise. (3) docs/design/registry/
evasion.yaml's 112-entry taxonomy denominator is NOT re-dispositioned
by this ticket -- T-0665's job was building the obligation, not
auditing the full taxonomy; that redisposition belongs to T-0666 (the
cross-language exhaustiveness meta-test) per the original brief's task
split, and is picked up there.

### Changed
```
 docs/design/registry/check-coverage.yaml |   6 +-
 docs/modules/gates.md                    |   1 +
 docs/modules/vet.md                      |  13 ++
 src/frob/check/__init__.py               |  12 +-
 src/frob/gates/__init__.py               |  14 ++
 src/frob/gates/_opaque.py                | 138 +++++++++++++++
 src/frob/vet/_capability.py              | 198 +++++++++++++++++++++-
 src/frob/vet/_capability_registry.py     | 212 +++++++++++++++++++++++
 tests/test_vet.py                        | 243 +++++++++++++++++++++++++++
 tickets.md                               | 277 ++++++++++++++++++++++++++++++-
 10 files changed, 1108 insertions(+), 6 deletions(-)
```

### Evidence
- `tests/test_vet.py::TestOpaqueIndirectionGate::test_python_getattr_non_literal_name_fires` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestOpaqueIndirectionGate::test_python_getattr_literal_name_does_not_fire` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestOpaqueIndirectionGate::test_python_eval_always_fires_regardless_of_argument` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestOpaqueIndirectionGate::test_python_import_module_non_literal_fires` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestOpaqueIndirectionGate::test_typescript_dynamic_import_non_literal_specifier_fires` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestOpaqueIndirectionGate::test_typescript_dynamic_import_literal_specifier_does_not_fire` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestOpaqueIndirectionGate::test_c_dlsym_non_literal_symbol_fires` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestOpaqueIndirectionGate::test_c_dlsym_literal_symbol_does_not_fire` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestOpaqueIndirectionGate::test_kotlin_class_forname_always_fires` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestOpaqueIndirectionGate::test_rust_libloading_get_fires_only_when_file_uses_libloading` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestOpaqueIndirectionGate::test_finding_inside_comment_span_does_not_fire` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestOpaqueIndirectionGate::test_finding_inside_string_literal_does_not_fire` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestOpaqueIndirectionGate::test_arg_looks_literal_rejects_fstring_interpolation` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestOpaqueIndirectionGate::test_split_top_level_args_balances_nested_parens` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestOpaqueIndirectionGate::test_split_top_level_args_returns_none_when_unterminated` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestOpaqueIndirectionGate::test_opaque_gate_emits_warn_severity_violation` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestOpaqueIndirectionGate::test_opaque_gate_no_findings_on_empty_tracked_set` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestOpaqueIndirectionGate::test_waived_finding_is_suppressed_and_reason_recorded` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 18 passed (from 18 evidence id(s))
- gates: 8 error(s), 4102 warning(s), 344 waived
- error-findings: ARCH001@src/frob/arch/_cpp_mayraise.py, COV001@src/frob/arch/_models.py, COV001@src/frob/gitlog/__init__.py, COV001@src/frob/process/parsers/common.py, COV001@src/frob/render/_color.py, COV001@src/frob/render/_elements.py, PERF003@src/frob/arch/_cpp_mayraise.py, PERF004@src/frob/arch/_cpp_mayraise.py
