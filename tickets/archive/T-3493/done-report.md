## Done report

Wired cuda into the same three FACETS-axis subsystems T-3492 wired java
into, mirroring both T-3492 and T-2906's precedents exactly.

Pre-widened scope up front (same 3 src files + docs + tests T-3492
needed) to avoid the mid-flight scope churn from that ticket.

Capability registry: new src/frob/vet/_capability_registry/
_dangerous_ops_cuda.py -- a .cu/.cuh file compiles with a HOST C/C++
compiler (nvcc invokes the platform's own C++ toolchain outside kernel
code), so _CUDA_OPERATIONS mirrors c-cpp's own exec/fs-read/fs-write/
ffi/net-connect/net-listen needles VERBATIM (identical C ABI, same
functions). CUDA's own device-side surface (cudaMalloc/cudaMemcpy/
kernel launch) is deliberately not patterned: it's a memory-safety
concern, not a capability this registry's taxonomy has a bucket for.
_kinds.py: "cuda" added to LANGUAGES. _matrix.py: _CUDA_OPERATIONS
folded into DANGEROUS_OPERATIONS; _NEW_ADAPTER_LANGUAGES widened; 11
hand-written excuses mirroring c-cpp's own excused set exactly (same
kind split: exec/fs-read/fs-write/ffi/net-connect/net-listen patterned,
everything else excused with the identical c-cpp reasoning).
_capability_core.py: .cu/.cuh -> "cuda". _capability_scan.py: self-match
exemption for the new file.

Dup exhaustiveness: "cuda" added to LANGUAGES, generated excuses (no
hand-written claim needed).

Docblocks: cuda does NOT get a new bucket -- its #include directives
resolve against tracked files the identical way c-cpp's do
(_c_include_violations is generic on file existence, not language-
specific), so it simply joined the existing _C_CPP_LANGS set, mirroring
T-2906's bash-reuses-console-tier precedent rather than csharp/java's
new-bucket shape.

Also fixed a frob:doc misplacement bug in src/frob/gates/_docblocks.py
introduced by T-3492's own ARCH001 split: the frob:doc/frob:tests
directive block for doc004_gate had ended up sitting above the new
private _doc004_block_violations helper instead of above doc004_gate
itself (measured via `frob check --only coverage`: COV001 on doc004_gate,
COV007 on the private helper). Moved the directive block back onto
doc004_gate.

frob.lang._support: closed cuda's _PENDING_FACET_WIRING_TICKETS entry
and removed its KNOWN_GAP_TRACKING_TICKETS "T-3493" citation.

Docs updated: docs/guides/extending/capability-registry.md,
docs/modules/{vet,dup,gates,lang}.md.

Evidence:
tests/test_capability_registry.py -- 622 passed (was 561 before adding
cuda's ~22 new fixture-driven test cases)
tests/test_lang_support.py::TestDeriveLanguageRegistry::test_cuda_capability_dup_docblock_are_implemented -- PASS
tests/test_vet.py::TestCapabilityScan::test_cuda_host_system_call_detected -- PASS
tests/test_vet.py::TestCapabilityScan::test_cuda_dlopen_detected -- PASS
tests/test_vet.py::TestCapabilityScan::test_cuda_benign_kernel_has_no_capabilities -- PASS
tests/test_gates.py -k Doc004 -- 10 passed (confirms the frob:doc
misplacement fix did not regress the existing doc004_gate binding)
Full tests/test_capability_registry.py + test_lang_support.py + test_vet.py: 1104 passed

Filed: none

Gates: frob check --ticket T-3493 --only coverage,drift,docstatus,tickets
-- after the frob:doc placement fix, no finding against
_dangerous_ops_cuda.py, _kinds.py, _matrix.py, _exhaustiveness.py,
_docblocks.py, _docblocks_refs.py, _capability_core.py,
_capability_scan.py, _support.py, or any touched test/doc file.

### Changed
```
 tickets/T-3493/ticket.md | 121 ++++++++++++++++++++++++++++++++++++++++++++++-
 1 file changed, 120 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_capability_registry.py::TestMatrixExhaustiveness::test_no_unexcused_empty_cells` (pytest node id, verified passing when recorded)
- `tests/test_lang_support.py::TestDeriveLanguageRegistry::test_cuda_capability_dup_docblock_are_implemented` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScan::test_cuda_host_system_call_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScan::test_cuda_dlopen_detected` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestCapabilityScan::test_cuda_benign_kernel_has_no_capabilities` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 24 error(s), 4287 warning(s), 895 waived
- error-findings: ARCH102@src/frob/process/_lock.py, ARCH103@src/frob/tickets/_leases.py, COV001@src/frob/tickets/_land_queue.py, COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DOC001@docs/design/macos-portability.md, DOC007@src/frob/verify/_bisect.py, DOC007@tests/unit/test_process_lock.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/process/_lock.py, DRIFT002@src/frob/verify/_bisect.py, DRIFT002@tests/unit/test_process_lock.py, DSL001@CHANGELOG.md, LARGE001@.claude/hooks/root-write-guard.py, LARGE001@src/frob/arch/_mayraise.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PII012@tests/test_ticket_leases.py, PRE001@tickets/T-3493, REF001@docs/design/macos-portability.md, REL001@src/frob/__init__.py, TICK004@tickets.md, WAIVE009@src/frob/arch/_normalized.py, WAIVE011@frob-ratchet.lock.json
