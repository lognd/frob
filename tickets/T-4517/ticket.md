---
id: T-4517
title: Collect NUnit [Test]/[TestCase] and [UnityTest] methods as frob:tests-bindable
  node ids
state: queued
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
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
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