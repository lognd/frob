---
id: T-4517
title: Collect NUnit [Test]/[TestCase] and [UnityTest] methods as frob:tests-bindable
  node ids
state: done
kind: feature
origin: agent
created: '2026-09-16'
priority: medium
parent: T-4516
tier: ticket
sprint: v0.533.0
runs_last: false
milestone: v0.533.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/testing/_collect_csharp.py
- src/frob/testing/_collect.py
- src/frob/testing/__init__.py
- src/frob/lang/_support.py
- tests/test_testing.py
- tests/fixtures/lang/csharp/tests/
- docs/modules/testing.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/testing/_collect.py
  reason: wire new collect_csharp_tests into dispatch/exports and add tests+fixtures
    per brief
  actor: logan
  at: '2026-09-16'
- op: add
  glob: src/frob/testing/__init__.py
  reason: wire new collect_csharp_tests into dispatch/exports and add tests+fixtures
    per brief
  actor: logan
  at: '2026-09-16'
- op: add
  glob: src/frob/lang/_support.py
  reason: wire new collect_csharp_tests into dispatch/exports and add tests+fixtures
    per brief
  actor: logan
  at: '2026-09-16'
- op: add
  glob: tests/test_testing.py
  reason: wire new collect_csharp_tests into dispatch/exports and add tests+fixtures
    per brief
  actor: logan
  at: '2026-09-16'
- op: add
  glob: tests/fixtures/lang/csharp/tests/
  reason: wire new collect_csharp_tests into dispatch/exports and add tests+fixtures
    per brief
  actor: logan
  at: '2026-09-16'
- op: add
  glob: docs/modules/testing.md
  reason: collect_csharp_tests needs a frob:doc anchor like the other collect_*_tests
    functions
  actor: logan
  at: '2026-09-16'
evidence:
- tests/test_testing.py::TestCollectCsharpTests::test_collect_csharp_tests_collects_test_and_unitytest
- tests/test_testing.py::TestCollectCsharpTests::test_collect_csharp_tests_collapses_parameterized_test_case
designated_repro_test: null
acceptance:
- text: GIVEN a C# test class with a [Test] method, WHEN collection runs, THEN it
    emits a stable node id an frob:tests directive can bind to.
  evidence:
  - tests/test_testing.py::TestCollectCsharpTests::test_collect_csharp_tests_collects_test_and_unitytest
- text: GIVEN a [TestCase(1, 2)] parameterized NUnit test, WHEN collection runs, THEN
    each case is represented (or the parameterized method is represented once with
    a documented id scheme) without erroring.
  evidence:
  - tests/test_testing.py::TestCollectCsharpTests::test_collect_csharp_tests_collapses_parameterized_test_case
- text: GIVEN a MonoBehaviour test class using [UnityTest] (a coroutine-based test),
    WHEN collection runs, THEN it is collected distinctly from a plain [Test] method.
  evidence:
  - tests/test_testing.py::TestCollectCsharpTests::test_collect_csharp_tests_collects_test_and_unitytest
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Add src/frob/testing/_collect_csharp.py (modeled on _collect_ts.py/_collect_kotlin.py) that walks .cs test files and emits stable node ids for [Test], [TestCase], [TestCaseSource] (NUnit) and [UnityTest] (Unity Test Framework) methods, wired into frob.testing's collector dispatch alongside the other per-language collectors.

GIVEN a C# test class with a [Test] method, WHEN collection runs, THEN it emits a stable node id an frob:tests directive can bind to.
GIVEN a [TestCase(1, 2)] parameterized NUnit test, WHEN collection runs, THEN each case is represented (or the parameterized method is represented once with a documented id scheme) without erroring.
GIVEN a MonoBehaviour test class using [UnityTest] (a coroutine-based test), WHEN collection runs, THEN it is collected distinctly from a plain [Test] method.