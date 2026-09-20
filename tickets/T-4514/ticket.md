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
body_changes:
- mode: append
  reason: 'T-4718 sweep: move narrative out of over-length comment run in _unity_api.py'
  actor: logan
  at: '2026-09-19'
  old_length: 1524
  new_length: 3210
- mode: append
  reason: 'T-4718 sweep: move narrative out of over-length comment run in _unity_api.py'
  actor: logan
  at: '2026-09-19'
  old_length: 3209
  new_length: 4895
- mode: append
  reason: 'T-4718 sweep: move narrative out of over-length comment run in _unity_api.py'
  actor: logan
  at: '2026-09-19'
  old_length: 4894
  new_length: 6580
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

T-4718 sweep (condensed from
src/frob/vet/_capability_registry/_unity_api.py:68-89, trimmed for
DOCARCH002's 12-line cap): the trimmed block's full original text, kept
verbatim below.

    # T-4554: the bare coarse "net" capability_kind these four entries
    # used (T-4514's own acceptance criterion names "the net capability"
    # specifically for `UnityWebRequest.Get`) is a RETIRED scanner kind
    # (`_effects.py::_KIND_MAP`'s own module docstring: "the old bare
    # `net`:`net` entry is retired since no registry entry emits the
    # unqualified `net` vet-kind anymore" -- T-0771's precise net-connect/
    # net-listen split). It slipped through unnoticed at T-4514 land time
    # because nothing enforced that claim until
    # `TestExtendedKindsDriftLock::test_extended_kinds_is_disjoint_from_
    # kind_map` (tests/unit/strata/test_selfconform.py) started failing
    # on dev: `all_pattern_kinds` (every kind any registry entry emits)
    # then contained a bare "net" neither `_EXTENDED_KINDS` nor
    # `_KIND_MAP` accounts for. Recategorized to `net-connect` -- the SAME
    # precise kind `_dotnet_bcl.py`'s `Dns.GetHostAddresses`/etc already
    # use for an outbound-network-reach signal with no listen-side
    # semantics, and (`_kinds.py`'s `WIRED_MODE_FAMILIES`) a coarse
    # `may "net"` declaration still covers `net-connect` exactly as it
    # covered the retired bare `net`, so no resolver behavior change: a
    # node that already declared `may "net"` for these call sites keeps
    # passing; only the raw scanner-kind bucket these needles land in
    # changes, from an unenforceable orphan to a normalized, drift-lock-
    # accounted-for one.

T-4718 sweep (condensed from
src/frob/vet/_capability_registry/_unity_api.py:68-89, trimmed for
DOCARCH002's 12-line cap): the trimmed block's full original text, kept
verbatim below.

    # T-4554: the bare coarse "net" capability_kind these four entries
    # used (T-4514's own acceptance criterion names "the net capability"
    # specifically for `UnityWebRequest.Get`) is a RETIRED scanner kind
    # (`_effects.py::_KIND_MAP`'s own module docstring: "the old bare
    # `net`:`net` entry is retired since no registry entry emits the
    # unqualified `net` vet-kind anymore" -- T-0771's precise net-connect/
    # net-listen split). It slipped through unnoticed at T-4514 land time
    # because nothing enforced that claim until
    # `TestExtendedKindsDriftLock::test_extended_kinds_is_disjoint_from_
    # kind_map` (tests/unit/strata/test_selfconform.py) started failing
    # on dev: `all_pattern_kinds` (every kind any registry entry emits)
    # then contained a bare "net" neither `_EXTENDED_KINDS` nor
    # `_KIND_MAP` accounts for. Recategorized to `net-connect` -- the SAME
    # precise kind `_dotnet_bcl.py`'s `Dns.GetHostAddresses`/etc already
    # use for an outbound-network-reach signal with no listen-side
    # semantics, and (`_kinds.py`'s `WIRED_MODE_FAMILIES`) a coarse
    # `may "net"` declaration still covers `net-connect` exactly as it
    # covered the retired bare `net`, so no resolver behavior change: a
    # node that already declared `may "net"` for these call sites keeps
    # passing; only the raw scanner-kind bucket these needles land in
    # changes, from an unenforceable orphan to a normalized, drift-lock-
    # accounted-for one.

T-4718 sweep (condensed from
src/frob/vet/_capability_registry/_unity_api.py:68-89, trimmed for
DOCARCH002's 12-line cap): the trimmed block's full original text, kept
verbatim below.

    # T-4554: the bare coarse "net" capability_kind these four entries
    # used (T-4514's own acceptance criterion names "the net capability"
    # specifically for `UnityWebRequest.Get`) is a RETIRED scanner kind
    # (`_effects.py::_KIND_MAP`'s own module docstring: "the old bare
    # `net`:`net` entry is retired since no registry entry emits the
    # unqualified `net` vet-kind anymore" -- T-0771's precise net-connect/
    # net-listen split). It slipped through unnoticed at T-4514 land time
    # because nothing enforced that claim until
    # `TestExtendedKindsDriftLock::test_extended_kinds_is_disjoint_from_
    # kind_map` (tests/unit/strata/test_selfconform.py) started failing
    # on dev: `all_pattern_kinds` (every kind any registry entry emits)
    # then contained a bare "net" neither `_EXTENDED_KINDS` nor
    # `_KIND_MAP` accounts for. Recategorized to `net-connect` -- the SAME
    # precise kind `_dotnet_bcl.py`'s `Dns.GetHostAddresses`/etc already
    # use for an outbound-network-reach signal with no listen-side
    # semantics, and (`_kinds.py`'s `WIRED_MODE_FAMILIES`) a coarse
    # `may "net"` declaration still covers `net-connect` exactly as it
    # covered the retired bare `net`, so no resolver behavior change: a
    # node that already declared `may "net"` for these call sites keeps
    # passing; only the raw scanner-kind bucket these needles land in
    # changes, from an unenforceable orphan to a normalized, drift-lock-
    # accounted-for one.