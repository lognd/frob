---
id: T-0418
title: 'perf: analyze_project runs TWICE per frob check (frob-arch stage + archgate
  gate); wire the DEAD _arch_violations_from_suggestions (~112s)'
state: done
kind: bug
origin: human
created: '2026-07-20'
priority: medium
parent: T-0410
tier: ticket
sprint: null
scope:
- src/frob/check/
- src/frob/gates/
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_memo.py::test_analyze_project_second_call_is_memo_hit
designated_repro_test: null
threat: null
component: null
---
User spotted from frob check output: frob-arch appears as its own stage AND archgate=112.81s appears in the gates timing -- arch is analyzed TWICE. Confirmed: check/_python.py::_run_arch (the advisory frob-arch stage) calls analyze_project once (~line 440); gates/_arch.py::arch_gate independently calls analyze_project again for ARCH001 (the archgate timing). The helper written to prevent exactly this -- check/_python.py::_arch_violations_from_suggestions (builds ARCH001 Violations from the already-computed suggestions "without re-running analyze_project a second time") -- is DEAD CODE, grep finds zero callers. FIX: wire the gates stage to build ARCH001 from the suggestions _run_arch already computed (via the dead helper), so analyze_project runs ONCE per check. Verify the same ARCH001 violation set is produced (byte-identical gate output) and archgate drops toward 0 (the work moves into the single frob-arch run). CHECK dup too: _run_dup calls find_duplicates for the frob-dup stage; confirm dup_gate does not ALSO re-run detection (it is default-off so may already skip -- verify). This is the exact "same expensive input recomputed across stages" class T-0413 (PERF meta-gap) must catch. Measured target: ~112s saved.