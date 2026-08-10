---
id: T-1900
title: 'SYS-IFACE-ORDER Tier-A auto-fix corrupts design/frob.strata on every land:
  empty interface=[] parsed as a name called ''[]'''
state: done
kind: bug
origin: agent
created: '2026-08-09'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_fix_engine_sync.py
- tests/unit/gates/test_sys_interface_canonical_order.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_fix_engine_sync.py
  reason: T-1900 fix lives in the SYS-IFACE-ORDER handler; test-file scope pending
    T-1896 lease
  actor: logan
  at: '2026-08-09'
- op: add
  glob: tests/unit/gates/test_sys_interface_canonical_order.py
  reason: T-1900's new round-trip/refusal tests live here
  actor: logan
  at: '2026-08-09'
evidence:
- tests/unit/gates/test_sys_interface_canonical_order.py::TestSysInterfaceCanonicalOrder::test_empty_interface_one_line_form_is_not_read_as_a_name
- tests/unit/gates/test_sys_interface_canonical_order.py::TestSysInterfaceCanonicalOrder::test_round_trip_every_node_shape_reparses
- tests/unit/gates/test_sys_interface_canonical_order.py::TestSysInterfaceCanonicalOrder::test_rewrite_that_would_not_parse_is_refused
- tests/unit/gates/test_sys_interface_canonical_order.py::TestSysInterfaceCanonicalOrder::test_groups_by_kind_then_alpha
- tests/unit/gates/test_sys_interface_canonical_order.py::TestSysInterfaceCanonicalOrder::test_order_only_multiset_preserved_and_idempotent
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
MEASURED 2026-08-09, coordinator, on main. design/frob.strata FAILED TO PARSE during two separate lands:

  ERROR: strata-core rejected source at line=1333 col=9: expected attribute value inside [..]
  ERROR: strata parse failed for /home/logan/projects/frob/design/frob.strata

The corrupted node body was:

    node testsuite : trusted {
        attr interface=[
            [],
        ];

DIAGNOSIS. T-1872 (landed d241bcd7201c) added fix_sys_interface_canonical_order / _reorder_node_interface_block in src/frob/gates/_fix_engine_sync.py, wired as SYS-IFACE-ORDER in TIER_A_HANDLERS. For a node with an EMPTY interface -- written 'attr interface=[];' on one line, exactly what _render_interface_block itself emits for the empty case (line 954-955) -- _iface_find_spans extracts the token '[]' as a declared NAME. declared becomes ['[]'], ordered becomes ['[]'], and _render_interface_block then re-renders it as a multi-line block whose body line is '        [],' -- invalid strata syntax.

WHY THE ORDER-ONLY GUARD DOES NOT CATCH IT. The Counter(declared) != Counter(ordered) assertion at line 983 compares ['[]'] against ['[]'] -- identical. The guard proves the NAME MULTISET is preserved, which it is; it does not and cannot prove the RESULT PARSES. The invariant was under-specified.

SEVERITY: CRITICAL, and this is the important part -- it recurs on EVERY LAND. Commit f184bb172 ('repair malformed interface=[[],] emitted by T-1883s land') already fixed the file once by hand, and the very next land (T-1892, c8e50a3d878d) re-emitted it. I have repaired it a second time. Any land that runs the Tier-A pass over this file re-breaks the self-model, and a broken self-model degrades every sys/SELFAUDIT gate silently -- the land still SUCCEEDS and prints LAND-PROOF verified=True while emitting the parse error as mere stderr noise.

REQUIRED FIX (all four parts):
1. _iface_find_spans must treat 'interface=[]' as ZERO declared names, never a name called '[]'.
2. Round-trip test: for every node kind including the empty case, rewrite output must re-parse. Assert the empty node is left byte-identical (single_clean should be True for it).
3. Strengthen the guard from 'multiset preserved' to 'multiset preserved AND result parses' -- re-parse the rewritten block and refuse the rewrite if strata-core rejects it. A rewriter that can emit unparseable output must verify its own output, not just its name set.
4. A land that emits a strata parse error must NOT report success. Landing while the self-model is unparseable is a false green: investigate whether this should refuse the land or at minimum surface as a land-blocking error rather than stderr noise.

Related: T-1872 (introduced), f184bb172 and the follow-up repair commit (both hand repairs), T-1895 (the shared brace-depth scanner extraction from the same handler).