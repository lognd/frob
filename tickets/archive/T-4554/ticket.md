---
id: T-4554
title: 'T-4536 regression: tests/unit/strata/test_effects.py::TestExtendedKindsDriftLock::test_extended_kinds_is_disjoint_from_kind_map
  fails on dev (_PATTERNS/_KIND_MAP/_EXTENDED_KINDS drift from the C# resolver)'
state: done
kind: bug
origin: agent
created: '2026-09-17'
priority: high
parent: T-4513
tier: ticket
sprint: v0.533.0
runs_last: false
milestone: v0.533.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/vet/_capability_registry/_dangerous_ops_bash_csharp.py
- tests/unit/strata/test_effects.py
- src/frob/vet/_capability_registry/_unity_api.py
- tests/vet_suite/test_capability_registry_unity.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/strata/_effects.py
  reason: fix confined to _dangerous_ops_bash_csharp.py and test_effects.py; _effects.py
    leased by T-draft-d56bad34
  actor: logan
  at: '2026-09-17'
- op: add
  glob: src/frob/vet/_capability_registry/_unity_api.py
  reason: 'TestExtendedKindsDriftLock fails: T-4514''s UnityWebRequest/WWW/NetworkManager/Application.OpenURL
    entries use the bare retired capability_kind=net; recategorize to net-connect,
    consistent with the rest of the registry'
  actor: logan
  at: '2026-09-17'
- op: add
  glob: tests/vet_suite/test_capability_registry_unity.py
  reason: recategorizing _unity_api.py's 4 bare-net entries to net-connect breaks
    this file's own 4 existing assertions asserting kind==net; update them to net-connect,
    same behavior, no test rename/delete
  actor: logan
  at: '2026-09-17'
body_changes:
- mode: append
  reason: 'T-4718 sweep: move narrative out of over-length comment run in _unity_api.py'
  actor: logan
  at: '2026-09-19'
  old_length: 396
  new_length: 2082
- mode: append
  reason: 'T-4718 sweep: move narrative out of over-length comment run in _unity_api.py'
  actor: logan
  at: '2026-09-19'
  old_length: 2081
  new_length: 3767
- mode: append
  reason: 'T-4718 sweep: move narrative out of over-length comment run in _unity_api.py'
  actor: logan
  at: '2026-09-19'
  old_length: 3766
  new_length: 5452
evidence:
- tests/unit/strata/test_effects.py::TestNoRetiredBareKindEmitted::test_no_registry_entry_emits_a_retired_bare_kind
- tests/unit/strata/test_selfconform.py::TestExtendedKindsDriftLock::test_extended_kinds_is_disjoint_from_kind_map
designated_repro_test: tests/unit/strata/test_effects.py::TestNoRetiredBareKindEmitted::test_no_registry_entry_emits_a_retired_bare_kind
acceptance:
- text: GIVEN dev WHEN tests/unit/strata/test_effects.py runs THEN TestExtendedKindsDriftLock
    passes
  evidence:
  - tests/unit/strata/test_effects.py::TestNoRetiredBareKindEmitted::test_no_registry_entry_emits_a_retired_bare_kind
  - tests/unit/strata/test_selfconform.py::TestExtendedKindsDriftLock::test_extended_kinds_is_disjoint_from_kind_map
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Measured 2026-09-17 by the T-4495 implementer: 1 failure in tests/unit/strata/test_effects.py, TestExtendedKindsDriftLock::test_extended_kinds_is_disjoint_from_kind_map, traced to T-4536 (C# capability resolver) adding entries to _PATTERNS whose kinds overlap _EXTENDED_KINDS and _KIND_MAP. Fix the registry entries (or the drift lock) so the invariant holds; no behaviour change to the resolver.

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