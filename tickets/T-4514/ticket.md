---
id: T-4514
title: Unity API capability map (UnityEngine, Editor-only APIs, MonoBehaviour/coroutine
  roots)
state: done
kind: feature
origin: agent
created: '2026-09-16'
priority: medium
parent: T-4513
tier: story
sprint: v0.533.0
runs_last: false
milestone: v0.533.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/vet/_capability_registry/_unity_api.py
- src/frob/lang/_walk_csharp.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/test_lang.py::TestCSharpUnityEntryPoints::test_private_lifecycle_method_is_public
- tests/test_lang.py::TestCSharpUnityEntryPoints::test_private_coroutine_is_public
- tests/vet_suite/test_capability_registry_unity.py::TestUnityApiRegistry::test_unity_web_request_maps_to_net
- tests/vet_suite/test_capability_registry_unity.py::TestUnityApiRegistry::test_unity_editor_namespace_usage_flagged_as_eval_with_clear_name
designated_repro_test: null
acceptance:
- text: GIVEN a MonoBehaviour with Start/Update/OnEnable/etc. and no visible caller
    in the file, WHEN the callgraph/dead-code detectors run, THEN these lifecycle
    methods are treated as roots, not flagged as dead code.
  evidence:
  - tests/test_lang.py::TestCSharpUnityEntryPoints::test_private_lifecycle_method_is_public
- text: GIVEN a method using 'yield return' (a coroutine) started via StartCoroutine,
    WHEN scanned, THEN the coroutine method is treated as reachable from its StartCoroutine
    call site, not orphaned.
  evidence:
  - tests/test_lang.py::TestCSharpUnityEntryPoints::test_private_coroutine_is_public
- text: GIVEN a call to UnityEngine.Networking.UnityWebRequest.Get, WHEN scanned,
    THEN it maps to the net capability.
  evidence:
  - tests/vet_suite/test_capability_registry_unity.py::TestUnityApiRegistry::test_unity_web_request_maps_to_net
- text: GIVEN a call to UnityEditor.AssetDatabase from a file under an Editor/ folder
    or Editor-only asmdef, WHEN scanned, THEN the finding is tagged editor-only, distinguishing
    it from an identical runtime-code finding.
  evidence:
  - tests/vet_suite/test_capability_registry_unity.py::TestUnityApiRegistry::test_unity_editor_namespace_usage_flagged_as_eval_with_clear_name
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Story: a registry mapping Unity's own API surface to frob capabilities, plus teaching the C# walker/callgraph that MonoBehaviour lifecycle methods and coroutines are roots (Unity invokes them via reflection/reflection-like dispatch, not a visible call site). blocked_by T-4505 (the C# resolver must exist first).

Map: UnityEngine.Networking.UnityWebRequest -> net; Application.OpenURL -> net/exec; PlayerPrefs -> fs.write; File/Resources.Load/AssetDatabase/Addressables -> fs.read; System.Diagnostics usage inside an Editor/ script flagged distinctly from runtime code; Unity Editor-only APIs (UnityEditor.* namespace) flagged by assembly location (Editor/ folder or an Editor-only asmdef).

GIVEN a MonoBehaviour with Start/Update/OnEnable/etc. and no visible caller in the file, WHEN the callgraph/dead-code detectors run, THEN these lifecycle methods are treated as roots, not flagged as dead code.
GIVEN a method using 'yield return' (a coroutine) started via StartCoroutine, WHEN scanned, THEN the coroutine method is treated as reachable from its StartCoroutine call site, not orphaned.
GIVEN a call to UnityEngine.Networking.UnityWebRequest.Get, WHEN scanned, THEN it maps to the net capability.
GIVEN a call to UnityEditor.AssetDatabase from a file under an Editor/ folder or Editor-only asmdef, WHEN scanned, THEN the finding is tagged editor-only, distinguishing it from an identical runtime-code finding.

## Unblock log
- 2026-09-16: unblocked by T-4505 -- blocker landed as T-4536 (duplicate id T-4505 dropped)