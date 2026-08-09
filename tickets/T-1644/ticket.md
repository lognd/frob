---
id: T-1644
title: Bind src/frob/yaml_io.py into the strata self-model and waive INV006 on the
  T-1420 TS split
state: queued
kind: docs
origin: human
created: '2026-08-06'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- design/frob.strata
- src/frob/vet/_capability_typescript_bindtable.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- cmd:grep -q 'src/frob/yaml_io.py' design/frob.strata exit=0 sha256=e3b0c44298fc
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
Two mechanical consequences of the wave-8 lands, both caught by the gates on main:

SELFAUDIT001 (SYS102): T-1204 added src/frob/yaml_io.py (the shared fast_yaml_loader factory that stops a fifth re-derivation of loader selection) but no strata node's code= glob covered it, so the file was outside the self-model entirely. Bound to the cli node alongside the other src/frob root-level modules, and frob sys sync-interface then declared fast_yaml_loader in that node's interface=.

INV006: T-1420 split _capability_typescript.py by pipeline phase, and the new _capability_typescript_bindtable.py header carries the module's historical narrative -- 'X only ever inspected identifier/member_expression', past tense, describing a round-1 gap that round 2 closed. The real recursion invariants live on the functions themselves in the sibling module as frob:invariant terminates edges. Waived at file level with that reasoning rather than reworded, because rewording history to dodge a keyword makes the narrative worse without making the code safer. Whether INV006 should read explanatory prose at all is T-1640.