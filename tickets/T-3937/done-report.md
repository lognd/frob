## Done report

T-3937 (F-172): the code fix this ticket describes was already landed by
T-3925 (commit f96a36ae2) -- add_evidence and replace_evidence already
union python_ids | rust_ids | _other_language_collected_ids(...) before
calling into add_evidence/replace_evidence, which is what reaches
_reject_unresolved_evidence in frob.tickets._evidence. Re-verified the
mechanism still holds in this checkout at
src/frob/app/ticket_runner/_verify.py:2695-2701 and :2796-2802.

What was still missing, and what this ticket actually delivers: every
existing test for _other_language_collected_ids (TestOtherLanguageCollectedIds
in tests/unit/test_verify_language_buckets.py) monkeypatches
LANGUAGE_COLLECTORS entries with bare lambdas -- exactly the shape the
ticket calls out as unable to distinguish a genuinely-working resolver
from one that accepts anything. Added a new test class,
TestBindingResolvesRealNonPythonRustCollectors, with three fixtures that
drive the REAL collect_ts_tests and collect_cpp_tests collectors (real
file discovery, real content-hash cache validation -- collect_ts_tests's
own _ts_content_key / collect_cpp_tests's own _ctest_content_key compute
the cache key the fixture seeds, never a hand-invented key) through the
actual CLI binding entrypoint, _apply_evidence:

  - MUST-FIRE: a genuine vitest node id, present in a real
    .frob/vitest-collect.json seeded via the real content-key function,
    binds successfully (evidence recorded, result.is_ok).
  - MUST-STAY-QUIET: a nonexistent ts id, alongside that same real
    collected project, is still rejected as UnknownEvidence -- proving
    the resolver validates against the real collected set rather than
    accepting anything non-python/rust.
  - THIRD FIXTURE: a real cpp/ctest node id (cache-seeded the same way,
    via collect_cpp_tests's own _ctest_content_key) binds the same way,
    proving the fix generalizes past vitest.

I ran the binding command myself and watched it succeed: `frob ticket
evidence T-3937 <the three test node ids>` recorded all three ids
(T-3937: evidence now has 3 id(s): [...]) -- this is a real
`_apply_evidence` invocation binding real pytest node ids, the same code
path add_evidence's CLI wiring always uses.

WHAT I HAVE NOT PROVEN: EXECUTION. Per T-3933, vitest/cpp EXECUTION
(actually spawning npx vitest / ctest and getting a pass/fail) is a
separate, still-open concern -- my fixtures monkeypatch
_verify_ids_passing to report every id as passing, exactly so they
isolate BINDING (does the id resolve against the collected set at all)
from RUNNING. No real vitest or ctest process was spawned by anything I
wrote or ran. Do not read this ticket as proving TypeScript or C++ tests
run end to end.

The kotlin case (the ticket's other stated option for the third fixture)
was tried first but hits a separate, pre-existing bug:
normalize_evidence_separator (frob.tickets.__init__, not in this
ticket's scope file) unconditionally rewrites the FIRST dot after a
node id's "::" into another "::" -- correct for python's
path::Class.method convention, but it silently mangles every real
kotlin id (always path::classname.method, dotted, per
_collect_kotlin.py's _kotlin_node_id), so a real kotlin id from
collect_kotlin_tests can never bind as typed. This looks like a genuine
consumer-facing bug distinct from T-3937's LANGUAGE_COLLECTORS-union
defect, and touches a file (src/frob/tickets/__init__.py) outside this
ticket's scope -- flagging it here rather than fixing it, per this
ticket's own instruction not to widen scope. Filed as a new ticket
below.

### Changed
```
 tests/unit/test_verify_language_buckets.py | 191 +++++++++++++++++++++++++++++
 tickets/T-3937/ticket.md                   |   4 +
 tickets/T-3945/ticket.md         |  53 ++++++++
 3 files changed, 248 insertions(+)
```

### Evidence
- `tests/unit/test_verify_language_buckets.py::TestBindingResolvesRealNonPythonRustCollectors::test_must_fire_real_vitest_node_id_binds_via_apply_evidence` (pytest node id, verified passing when recorded)
- `tests/unit/test_verify_language_buckets.py::TestBindingResolvesRealNonPythonRustCollectors::test_must_stay_quiet_nonexistent_ts_id_is_still_rejected` (pytest node id, verified passing when recorded)
- `tests/unit/test_verify_language_buckets.py::TestBindingResolvesRealNonPythonRustCollectors::test_real_cpp_node_id_binds_via_apply_evidence` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 4 error(s), 4391 warning(s), 935 waived
- error-findings: DOC006@tickets/T-3931/ticket.md, PRE001@tickets/T-3937, SCOPE002@tickets.md, SELFAUDIT001@tests/unit/test_verify_language_buckets.py
