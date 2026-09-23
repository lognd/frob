---
id: T-4509
title: Unity fixture project + e2e proof + docs/guides/unity.md
state: done
kind: feature
origin: agent
created: '2026-09-16'
priority: medium
parent: T-4513
tier: story
sprint: null
runs_last: false
milestone: 0.533.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/fixtures/unity_sample/**
- tests/system/test_unity_e2e.py
- docs/guides/unity.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/system/test_unity_e2e.py::TestUnityScaffoldAndAsmdefNodes::test_scaffold_succeeds_and_nodes_match_the_two_asmdefs
- tests/system/test_unity_e2e.py::TestMonoBehaviourAndCoroutineAreNotDeadCode::test_dead_symbols_gate_reports_zero_findings
- tests/system/test_unity_e2e.py::TestExpectedCapabilityFindings::test_runtime_script_finds_net_fs_write_and_exec
- tests/system/test_unity_e2e.py::TestExpectedCapabilityFindings::test_editor_script_finds_eval_and_fs_write_tagged_editor_only
- tests/system/test_unity_e2e.py::TestExpectedCapabilityFindings::test_frob_vet_cli_runs_cleanly_against_the_fixture
- tests/system/test_unity_e2e.py::TestNUnitAndUnityTestCollection::test_both_test_attribute_families_collected
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Story: capstone proof for the whole epic. blocked_by every prior story -- this is the final integration check and doc, run last after the resolver, capability maps, project model, and test evidence all exist.

Deliverables:
1. tests/fixtures/unity_sample/ -- a small Unity-shaped fixture: Assets/Scripts/ with a MonoBehaviour (Update + a coroutine via StartCoroutine), an Editor/ script using a UnityEditor-only API, a Runtime.asmdef and a Tests.asmdef with NUnit/[UnityTest] tests, and a minimal Packages/manifest.json + ProjectSettings/ProjectVersion.txt so project detection fires.
2. tests/system/test_unity_e2e.py -- scaffolds/inits the fixture, builds the graph, runs frob check and frob vet against it, and asserts the expected capability findings (net/fs.write/exec per the maps from stories 2-3) fire and that zero false positives appear on the fixture's clean code paths.
3. docs/guides/unity.md -- a user-facing guide: how to point frob at an existing Unity project, what gets detected, what capability findings to expect, how test evidence is gathered.

GIVEN the unity_sample fixture, WHEN 'frob scaffold unity-project' (or init detection) runs against it, THEN it succeeds and the asmdef-derived strata nodes match the fixture's two asmdef files.
GIVEN the fixture's MonoBehaviour and coroutine, WHEN frob check's dead-code/callgraph detectors run, THEN the lifecycle method and coroutine are NOT flagged as dead code (proves story 3's roots).
GIVEN the fixture's Editor-only API call and the fixture's BCL/Unity API calls (net, fs.write), WHEN frob vet runs, THEN exactly the expected findings appear, tagged correctly (editor-only vs runtime), with zero unexpected findings.
GIVEN the fixture's NUnit and [UnityTest] tests, WHEN test evidence collection runs (T-4517/T-4508), THEN both are collected and bindable, proving stories 1-5 compose end to end.

## Unblock log
- 2026-09-19: unblocked by T-4506 -- leaves landed or queued; capstone can proceed against dev
- 2026-09-19: unblocked by T-4511 -- leaves landed or queued; capstone can proceed against dev
- 2026-09-19: unblocked by T-4514 -- leaves landed or queued; capstone can proceed against dev
- 2026-09-19: unblocked by T-4518 -- leaves landed or queued; capstone can proceed against dev
- 2026-09-19: unblocked by T-4516 -- leaves landed or queued; capstone can proceed against dev