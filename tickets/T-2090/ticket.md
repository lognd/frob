---
id: T-2090
title: Evidence collection discards the missing_natives it already computed, so a
  fresh worktree reports UnknownEvidence and advises deleting the cache instead of
  building natives
state: done
kind: bug
origin: agent
created: '2026-08-10'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/testing/_collect.py
- src/frob/tickets/_evidence.py
- src/frob/app/ticket_runner/_verify.py
- src/frob/testing/__init__.py
- docs/modules/testing.md
- tests/test_tickets.py
- tests/test_testing.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_evidence.py
  reason: AC2 requires the UnknownEvidence message to distinguish missing-natives
    from genuinely-absent test, which is only surfaced from _check_evidence_resolution
    in this file
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/app/ticket_runner/_verify.py
  reason: AC1 requires 'frob ticket evidence' CLI path to surface the missing-native+build_cmd
    detail on a collection failure; _apply_evidence's error log currently prints only
    the enum, discarding python_collection_failure_detail()
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/testing/__init__.py
  reason: export python_collection_missing_natives, the new public accessor collect_python_tests
    writes on every return path
  actor: logan
  at: '2026-08-10'
- op: add
  glob: docs/modules/testing.md
  reason: COV001 doc-edge requirement for new public symbol python_collection_missing_natives
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/test_tickets.py
  reason: unit-level repro/regression coverage for AC0-2, and test_unresolvable_id_warning_names_no_nonexistent_flag
    in test_tickets.py asserts the exact 'self-refreshes' wording this ticket intentionally
    changes for the natives-present case
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/test_testing.py
  reason: unit-level repro/regression coverage for AC0-2, and test_unresolvable_id_warning_names_no_nonexistent_flag
    in test_tickets.py asserts the exact 'self-refreshes' wording this ticket intentionally
    changes for the natives-present case
  actor: logan
  at: '2026-08-10'
evidence:
- tests/test_testing.py::TestCollectPythonTests::test_autorebuild_attempted_and_failure_names_native_when_still_missing
- tests/test_testing.py::TestCollectPythonTests::test_no_autorebuild_attempted_when_natives_already_built
- tests/test_tickets.py::TestEvidence::test_unresolvable_id_warning_names_no_nonexistent_flag
- tests/test_tickets.py::TestEvidence::test_unresolvable_id_with_missing_native_names_it_and_build_cmd
designated_repro_test: tests/test_testing.py::TestCollectPythonTests::test_autorebuild_attempted_and_failure_names_native_when_still_missing
acceptance:
- text: given a worktree whose declared natives are unbuilt, when frob ticket evidence
    is given a valid node id, then it either builds the missing natives and resolves
    the id, or fails naming the missing native and its build_cmd -- this test MUST
    fail against current main
  evidence:
  - tests/test_testing.py::TestCollectPythonTests::test_autorebuild_attempted_and_failure_names_native_when_still_missing
  - tests/test_testing.py::TestCollectPythonTests::test_no_autorebuild_attempted_when_natives_already_built
  - tests/test_tickets.py::TestEvidence::test_unresolvable_id_warning_names_no_nonexistent_flag
  - tests/test_tickets.py::TestEvidence::test_unresolvable_id_with_missing_native_names_it_and_build_cmd
- text: given natives are present and the node id genuinely does not exist in the
    tree, when evidence binding fails, then the message says the test is absent and
    does NOT advise deleting the collection cache
  evidence:
  - tests/test_testing.py::TestCollectPythonTests::test_autorebuild_attempted_and_failure_names_native_when_still_missing
  - tests/test_testing.py::TestCollectPythonTests::test_no_autorebuild_attempted_when_natives_already_built
  - tests/test_tickets.py::TestEvidence::test_unresolvable_id_warning_names_no_nonexistent_flag
  - tests/test_tickets.py::TestEvidence::test_unresolvable_id_with_missing_native_names_it_and_build_cmd
- text: given natives are already built, when frob ticket evidence runs, then no native
    rebuild is triggered -- the build happens only when missing_natives is non-empty
  evidence:
  - tests/test_testing.py::TestCollectPythonTests::test_autorebuild_attempted_and_failure_names_native_when_still_missing
  - tests/test_testing.py::TestCollectPythonTests::test_no_autorebuild_attempted_when_natives_already_built
  - tests/test_tickets.py::TestEvidence::test_unresolvable_id_warning_names_no_nonexistent_flag
  - tests/test_tickets.py::TestEvidence::test_unresolvable_id_with_missing_native_names_it_and_build_cmd
threat: null
component: testing
anchor: false
anchor_reason: null
land_commit: null
---
## Measured evidence (my own session, verbatim)

Binding evidence for T-2084 in a fresh worktree:

    $ frob ticket evidence T-2084 <two valid node ids> --path <worktree>
    ERROR: collect_python_tests: pytest --collect-only exited 2 in
      /home/logan/projects/frob/.claude/worktrees/t2084-state-color
    ERROR: ticket evidence: pytest collection failed: CollectFailed

The real cause was that a fresh worktree has no built natives. Nothing in
that output says so. The remedy was `uv run frob natives build`, which is
not mentioned.

Worse, the sibling failure on the same path actively misdirects:

    ERROR: ticket evidence failed: UnknownEvidence: Evidence id does not
      resolve to a collected test (the collection cache self-refreshes on
      the next `frob test` / `frob check` run; if it still does not
      resolve, delete .frob/pytest-collect.json ... or fix the id)

I followed that advice, deleted `.frob/pytest-collect.json`, and it did not
help, because the cache was never the problem. Two wasted cycles on a
one-command fix.

## Root cause, read from source

1. `_maybe_autorebuild_natives` ALREADY EXISTS (`src/frob/gates/__init__.py:7381`)
   and already does exactly the right thing. Its callers are:
     - `src/frob/app/ticket_runner/_land_cmd.py:323` (via
       `_worktree_natives_verifiably_healthy`)
     - `src/frob/gates/__init__.py:7518` (inside `run_gates`)
   It is NOT called on the evidence/collection path.

2. `collect_python_tests` (`src/frob/testing/_collect.py:444`) ALREADY
   COMPUTES the answer and carries it in its own result:

       natives = _load_natives_or_empty(root)
       missing = _missing_natives(natives)
       ...
       return Ok(CollectedTests(node_ids=cached, missing_natives=missing))

   `src/frob/testing/_models.py:103` states the intent outright:
   "`missing_natives` lets COV003 name the real remedy (build the native)".

3. COV003 does exactly that (`src/frob/gates/__init__.py:2020-2023`),
   formatting `f"{spec.name} (run: {spec.build_cmd})"`.

So the information is computed, carried, and already used correctly by one
consumer -- and then DISCARDED at the point where an agent actually hits the
wall. This is the same shape as T-1669's `allocator_lock`: a correct
primitive wired into too few call sites.

## Cost, and why a brief is not the fix

Every agent brief in this session tells agents to build natives first, and
the playbook covers it. Agents still hit it, and so did I, an hour after
writing the memory about it. A rule that must be remembered before the tool
will work is not enforcement. Per the standing audit rule: if a written rule
was not followed, the rule is not the fix.

## DO NOT FIX IT THIS WAY

- **Do not just reword the error string.** A better sentence still costs the
  agent a full round trip. The information is already in hand at the moment
  of failure; act on it.
- **Do not make every `frob ticket evidence` call build natives
  unconditionally.** A native build is slow, and land cost is already the
  fleet's throughput ceiling (~210s inside the land lock). Build only when
  `missing_natives` is non-empty, i.e. only when it is known to be the cause.
- **Do not silently swallow a genuine absent-test case into a natives
  rebuild.** After a rebuild, if the id still does not resolve, the correct
  answer is "this test does not exist in this tree" -- which must be said
  distinctly from "collection failed". I hit BOTH cases in one session and
  they were indistinguishable in the output; that is what made the diagnosis
  take three attempts.
- **Do not delete or weaken the cache-invalidation advice** for the case
  where it IS the cache; just stop offering it when `missing_natives` says
  otherwise.

## The general rule

A diagnostic must name the remedy it already knows. This repo has the
precedent written down and enforced elsewhere: T-1664, "Semantic checks must
report UNRESOLVED, never silently pass when they cannot" -- same principle,
different surface. Here the check does not silently pass, but it reports the
wrong reason, which costs the same debugging session.

## Done report

Changed:
- src/frob/testing/_collect.py::collect_python_tests (calls the new
  _autorebuild_missing_natives when missing_natives is non-empty, and
  enriches the recorded failure detail with the missing native + build_cmd
  when collection still fails afterward)
- src/frob/testing/_collect.py::_autorebuild_missing_natives (new)
- src/frob/testing/_collect.py::python_collection_missing_natives (new
  public accessor, mirrors python_collection_failure_detail's module-state
  pattern)
- src/frob/testing/_collect.py::_set_collection_missing_natives (new)
- src/frob/testing/__init__.py (exports python_collection_missing_natives)
- src/frob/tickets/_evidence.py::add_evidence (new missing_natives= param)
- src/frob/tickets/_evidence.py::_check_evidence_resolution (missing_natives
  param picks which of two distinct UnknownEvidence messages fires)
- src/frob/app/ticket_runner/_verify.py::_apply_evidence (threads
  python_collection_missing_natives() into add_evidence; surfaces
  python_collection_failure_detail() on a collection-Err log line)
- docs/modules/testing.md (T-2090 public-API paragraph + frob:describes)

Evidence:
- tests/test_testing.py::TestCollectPythonTests::test_autorebuild_attempted_and_failure_names_native_when_still_missing
  (designated repro: FAILED_AT_PARENT at e13105e46425fd2c49fc84d3fdd803db54c2f671,
  confirmed via frob ticket evidence --check-repro)
- tests/test_testing.py::TestCollectPythonTests::test_no_autorebuild_attempted_when_natives_already_built
- tests/test_tickets.py::TestEvidence::test_unresolvable_id_warning_names_no_nonexistent_flag
  (updated to assert the new "does not exist in this tree" wording and the
  absence of the cache-deletion advice for the natives-already-built case)
- tests/test_tickets.py::TestEvidence::test_unresolvable_id_with_missing_native_names_it_and_build_cmd
- tests/test_testing.py::TestCollectPythonTests::test_python_collection_missing_natives_reflects_last_call
All bound to acceptance criteria 0, 1, 2 via --accepts.

Filed: none -- no out-of-scope work found.

Gates: `frob check --ticket T-2090 --only affect_drift --only prework --only test`
clean (0 errors, matched pre-existing warning set only) after adding the
doc paragraph, frob:tests edge, and its unit test. `frob check
--land-parity` clean (0 unscoped errors). `frob ticket evidence
--check-repro` confirmed FAILED_AT_PARENT (genuine repro) against the
test-only commit. TEST016 mutation check initially flagged one
confirmatory-only survivor (a dead `or ''` fallback in the new
enrichment code); removed the unreachable fallback rather than waiving it,
re-ran, close succeeded clean.

### Changed
```
 docs/modules/testing.md               |  23 ++++++
 src/frob/app/ticket_runner/_verify.py |  25 ++++++-
 src/frob/testing/__init__.py          |  12 +--
 src/frob/testing/_collect.py          |  86 ++++++++++++++++++++++
 src/frob/tickets/_evidence.py         |  68 ++++++++++++++---
 tests/test_testing.py                 | 134 ++++++++++++++++++++++++++++++++++
 tests/test_tickets.py                 |  38 +++++++++-
 tickets/T-2090/ticket.md              |  73 ++++++++++++++++--
 8 files changed, 432 insertions(+), 27 deletions(-)
```

### Evidence
- `tests/test_testing.py::TestCollectPythonTests::test_autorebuild_attempted_and_failure_names_native_when_still_missing` (pytest node id, verified passing when recorded)
- `tests/test_testing.py::TestCollectPythonTests::test_no_autorebuild_attempted_when_natives_already_built` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestEvidence::test_unresolvable_id_warning_names_no_nonexistent_flag` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestEvidence::test_unresolvable_id_with_missing_native_names_it_and_build_cmd` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: none (measured, zero errors)
