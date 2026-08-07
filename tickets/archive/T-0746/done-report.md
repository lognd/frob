## Done report

## Done report

Changed:
  src/frob/gates/_protocol_summary.py -- added PROTO002 (state-requirement
    violation) and PROTO003 (invalid transition) to the existing PROTO001
    per-package `compute_protocol_summaries` scan (one pass, three
    findings). New helpers: `_protocol_initial_states`,
    `_parse_transition_token`, `_established_states`, `_own_requires`,
    `_own_transitions`, `_discharge`. Fixed a pre-existing latent bug in
    `_package_edges` (edges came back with ABSOLUTE-path `src`/`origin`
    from `parse_file(root / rel_path)`, while `snapshot.edges`/entrypoints
    are always repo-root-relative -- PROTO001 never needed the two to
    compare equal since poisoning is a pure `CallGraph` fact, but
    PROTO002/PROTO003's requires/transition lookups key directly off
    `edge.src == symref`, so this needed fixing to make them work at all).
  src/frob/arch/_protocol_excuse.py (new) -- `DischargeResult`,
    `rust_drop_discharge`, `cpp_raii_discharge`, `python_with_discharge`,
    `typescript_using_discharge`, `gc_finalizer_discharge`: the per-
    language discharge predicates T-0746's doctrine names. Only
    `python_with_discharge` is wired into the real repo-scan gate today
    (see Deferred below).
  src/frob/gates/__init__.py -- registered PROTO002/PROTO003 in
    `_KNOWN_GATE_RULES`.
  docs/modules/gates.md -- new "PROTO002/PROTO003 (T-0746)" section (rule
    table rows + full doctrine/approximation/discharge-table writeup).
  tests/test_gates.py -- `TestProtocolVerificationGate` (7 tests) and
    `TestProtocolLanguageExcuseDischarge` (12 tests), 19 total.

Deferred, disclosed, filed:
  T-0840 (path-sensitive per-call-site state verification,
    scope src/frob/graph/**, src/frob/gates/_protocol_summary.py):
    `compute_protocol_summaries` (T-0745) has no per-call-site statement
    ordering, so PROTO002/PROTO003 ask an EXISTENTIAL question ("is state
    S established by SOME reachable transition anywhere in the tagged
    package closure") rather than a path-sensitive one. Deliberately
    false-negative-biased, never false-positive -- the crisp, ticket-named
    case (a state never established by ANY transition anywhere) is caught
    exactly. Referenced in both the gate module docstring and
    docs/modules/gates.md.
  T-0841 (wire Rust/C++/TypeScript discharge into a real
    call-graph scan, scope src/frob/gates/_protocol_summary.py,
    src/frob/graph/callgraph.py): the Rust/C++/TypeScript/GC discharge
    predicates in `frob.arch._protocol_excuse` are built and directly
    unit-tested but not wired into a real cross-file scan, because
    `build_call_graph` is Python-only (same disclosed limitation PROTO001
    already carries). Mirrors T-0745's own T-0809 disclosure pattern
    rather than building a second, unreviewed call-graph substrate here.
  (Both drafts will be renumbered by `frob ticket land`; referenced by
  their draft ids in code/docs per the land-renumber caution in
  docs/guides/agent-playbook.md.)

Deviation from the acceptance's literal fixture languages: the acceptance
text describes "a C fixture" for the state-requirement case and "Rust"
for the discharge-revocation case. `build_call_graph`'s Python-only scope
(disclosed by PROTO001 already, and unchanged by this ticket) means the
real repo-scan gate only exercises Python fixtures --
`test_state_never_established_is_an_error` is the Python-syntax
equivalent of the ticket's C-shaped example (a `frob:requires`-tagged
function reachable with no reachable transition establishing its
state), and the Rust Drop/mem::forget doctrine (acceptance's second
GIVEN) is verified directly against `rust_drop_discharge`
(`TestProtocolLanguageExcuseDischarge.test_rust_drop_impl_discharges` /
`test_rust_mem_forget_revokes_the_drop_discharge`) rather than through a
full C/Rust repo-scan gate that does not exist yet (T-0841).

docs/design/registry/check-coverage.yaml: NOT touched, per instruction --
`frob:enforces CHK-GATE-PROTO002`/`CHK-GATE-PROTO003` directives are in
place on `protocol_summary_gate` (REG009 WARN "phantom enforcement" is
expected/live until the coordinator adds the registry entries at land,
same as REG010's "2 live gate rule(s) have no CHK-GATE-<rule> entry"
finding -- both WARN, both disclosed here rather than worked around).

Evidence (bound via --accepts 0, all 19 collected and passing):
  tests/test_gates.py::TestProtocolVerificationGate::test_state_never_established_is_an_error
  tests/test_gates.py::TestProtocolVerificationGate::test_state_established_by_a_reachable_transition_is_not_flagged
  tests/test_gates.py::TestProtocolVerificationGate::test_state_equal_to_initial_is_not_flagged
  tests/test_gates.py::TestProtocolVerificationGate::test_poisoned_summary_at_a_requires_symbol_is_an_error
  tests/test_gates.py::TestProtocolVerificationGate::test_invalid_transition_precondition_never_established_is_an_error
  tests/test_gates.py::TestProtocolVerificationGate::test_valid_transition_chain_is_not_flagged
  tests/test_gates.py::TestProtocolVerificationGate::test_python_with_block_discharges_the_requirement
  tests/test_gates.py::TestProtocolLanguageExcuseDischarge::test_rust_drop_impl_discharges
  tests/test_gates.py::TestProtocolLanguageExcuseDischarge::test_rust_mem_forget_revokes_the_drop_discharge
  tests/test_gates.py::TestProtocolLanguageExcuseDischarge::test_rust_manually_drop_revokes_the_discharge
  tests/test_gates.py::TestProtocolLanguageExcuseDischarge::test_rust_no_drop_impl_is_not_discharged
  tests/test_gates.py::TestProtocolLanguageExcuseDischarge::test_cpp_raii_destructor_discharges
  tests/test_gates.py::TestProtocolLanguageExcuseDischarge::test_cpp_no_destructor_is_not_discharged
  tests/test_gates.py::TestProtocolLanguageExcuseDischarge::test_python_with_block_discharges
  tests/test_gates.py::TestProtocolLanguageExcuseDischarge::test_python_no_with_block_is_not_discharged
  tests/test_gates.py::TestProtocolLanguageExcuseDischarge::test_typescript_using_discharges
  tests/test_gates.py::TestProtocolLanguageExcuseDischarge::test_typescript_try_finally_discharges
  tests/test_gates.py::TestProtocolLanguageExcuseDischarge::test_typescript_bare_call_is_not_discharged
  tests/test_gates.py::TestProtocolLanguageExcuseDischarge::test_gc_finalizer_never_discharges

`uv run pytest tests/test_gates.py -q`: 1 pre-existing failure
(`TestGateOrderSetEquality::test_canonical_gate_order_matches_all_gates`,
confirmed identical on unmodified `main` -- `compliance` gate missing from
`_CANONICAL_GATE_ORDER`, unrelated to this ticket's scope), everything
else green including all 19 new + all pre-existing Protocol* tests.

Severity/main-cleanliness: PROTO002/PROTO003 default to ERROR per the
ticket's "enforceable, never fail-silent" mandate. This repo's own
tracked (non-fixture, non-test) source carries zero real `frob:protocol`/
`frob:requires`/`frob:transition` usage today, so ERROR-by-default
measures 0 errors against `main` (confirmed via
`frob check --ticket T-0746 --only <stage>` for every stage group: lint
PASS 0/0, static WARN 0 errors/168 warnings, gates-fast WARN 0/1118,
gates-native WARN 0/897, gates-security WARN 0/892 -- all pre-existing
WARN debt, none newly introduced by this ticket). No severity was
weakened to hit this number; both rules are genuinely ERROR-tier.

Gates: `frob check --ticket T-0746` (chunked, all 5 stage groups) clean
at 0 errors each. No new waivers added to production code by this
ticket's own findings; one `frob:waive INV006` added to
src/frob/arch/_protocol_excuse.py's module docstring (pre-existing
INV006 exclusivity-language pool disposition, same shape
`frob.graph.dsl`'s own module docstring already carries -- not a
finding introduced by this ticket's logic).

### Changed
(no changed files detected)

### Evidence
- `tests/test_gates.py::TestProtocolVerificationGate::test_state_never_established_is_an_error` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestProtocolVerificationGate::test_state_established_by_a_reachable_transition_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestProtocolVerificationGate::test_state_equal_to_initial_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestProtocolVerificationGate::test_poisoned_summary_at_a_requires_symbol_is_an_error` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestProtocolVerificationGate::test_invalid_transition_precondition_never_established_is_an_error` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestProtocolVerificationGate::test_valid_transition_chain_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestProtocolVerificationGate::test_python_with_block_discharges_the_requirement` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestProtocolLanguageExcuseDischarge::test_rust_drop_impl_discharges` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestProtocolLanguageExcuseDischarge::test_rust_mem_forget_revokes_the_drop_discharge` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestProtocolLanguageExcuseDischarge::test_rust_manually_drop_revokes_the_discharge` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestProtocolLanguageExcuseDischarge::test_rust_no_drop_impl_is_not_discharged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestProtocolLanguageExcuseDischarge::test_cpp_raii_destructor_discharges` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestProtocolLanguageExcuseDischarge::test_cpp_no_destructor_is_not_discharged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestProtocolLanguageExcuseDischarge::test_python_with_block_discharges` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestProtocolLanguageExcuseDischarge::test_python_no_with_block_is_not_discharged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestProtocolLanguageExcuseDischarge::test_typescript_using_discharges` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestProtocolLanguageExcuseDischarge::test_typescript_try_finally_discharges` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestProtocolLanguageExcuseDischarge::test_typescript_bare_call_is_not_discharged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestProtocolLanguageExcuseDischarge::test_gc_finalizer_never_discharges` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 19 passed (from 19 evidence id(s))
- gates: 0 error(s), 1203 warning(s), 207 waived
