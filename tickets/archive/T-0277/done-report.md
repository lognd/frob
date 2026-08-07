## Done report

Resolved in the SAME commit as T-0257's landing (coordinator fold-in, to
avoid a red self-conformance test on main). Added "src/frob/deploy/**" to
the `core` node's code glob in design/frob.strata -- deploy is a frob
component alongside dup/perf/testing/etc. already aggregated under `core`,
and its observed capabilities (fs writes of the generated scripts) are
covered by core's existing may env/eval/exec/fs declarations, so no new
SYS100 arises. Verified: TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant
PASSES (was failing SYS102 pre-fix). No new capability declarations needed.

Evidence: tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant
Filed: none.
