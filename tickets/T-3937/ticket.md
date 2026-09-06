---
id: T-3937
title: 'F-172: evidence BINDING resolves only python+rust collectors; ts/cpp/kotlin
  ids are rejected as UnknownEvidence'
state: done
kind: bug
origin: human
created: '2026-09-05'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_verify.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/unit/test_verify_language_buckets.py::TestBindingResolvesRealNonPythonRustCollectors::test_must_fire_real_vitest_node_id_binds_via_apply_evidence
- tests/unit/test_verify_language_buckets.py::TestBindingResolvesRealNonPythonRustCollectors::test_must_stay_quiet_nonexistent_ts_id_is_still_rejected
- tests/unit/test_verify_language_buckets.py::TestBindingResolvesRealNonPythonRustCollectors::test_real_cpp_node_id_binds_via_apply_evidence
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Consumer logand.app-v2 F-172. Their symptom: an agent took a vitest node id (file.test.ts::describe > it) VERBATIM from .frob/vitest-collect.json immediately after frob test refreshed it, and frob ticket evidence still rejected it with 'does not resolve to a collected test'.

MECHANISM VERIFIED IN OUR OWN SOURCE, not taken on trust:

  src/frob/app/ticket_runner/_verify.py:2033
      from frob.testing import collect_python_tests, collect_rust_tests, load_runners
  :2035  collected = collect_python_tests(root)
  :2045  rust_collected = collect_rust_tests(root)

That two-language set is what reaches _reject_unresolved_evidence in
src/frob/tickets/_evidence.py:1377, which returns Err(UnknownEvidence) for anything
that does not match. Meanwhile T-3925's all-language union over
frob.testing.LANGUAGE_COLLECTORS (which DOES include 'ts') lives in separate
functions at :2173 and :2243 and is only consulted on the VERIFICATION path.

So the consumer's stated mechanism is exactly correct: the resolver reads only
pytest-collect.json and cargo-collect.json.

THIS IS THE BINDING-VS-VERIFICATION SPLIT AGAIN. It is the third time this pair
has been confirmed separately broken (F-039, F-134, now F-172), and the second
time work was reported complete on the strength of the verification half alone.
Treat 'the union exists' as evidence about verification ONLY until the binding
path is measured.

COST TO THE CONSUMER: 14 tickets are parked or bound to a coarse
--evidence-cmd 'npx vitest run <file>' instead of real node ids -- T-0056,
T-0069, T-0085, T-0088, T-0098, T-0103, T-0104, T-0145, T-0155, T-0158, T-0159,
T-0161, T-0162, T-0164, plus 11 frontend leaves.

FIX: the binding path must resolve against the SAME LANGUAGE_COLLECTORS union the
verification path uses. Derive it from the registry -- do not hand-write a third
per-language list, which is the duplication that produced this desync in the
first place.

RELATED: T-3933 records that vitest EXECUTION is still unproven (its test uses a
synthetic LANGUAGE_COLLECTORS['ts'] lambda and monkeypatches _verify_ids_passing,
so no real vitest process is ever spawned). Fixing binding without fixing that
leaves the matrix's 'ts: verifies? yes' still overstated. Do not close this in a
way that implies ts is end-to-end proven.

MUST-FIRE FIXTURE: a real vitest node id present in .frob/vitest-collect.json
binds successfully via frob ticket evidence.
MUST-STAY-QUIET: a genuinely nonexistent ts id is still rejected as UnknownEvidence.
THIRD FIXTURE: the same for a cpp or kotlin id, since they share the defect.

ACCEPTANCE
- Binding and verification consult one shared, registry-derived collector set.
- All three fixtures committed, exercising the REAL collector rather than a lambda.