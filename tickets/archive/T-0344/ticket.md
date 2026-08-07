---
id: T-0344
title: R5 real-CFG per-language coverage table missing from dup.md (T-0196 follow-up)
state: done
kind: docs
origin: agent
created: '2026-07-20'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/modules/dup.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- cmd:python3 /tmp/verify_dup_r5_table.py exit=0 sha256=a324feb9a679
designated_repro_test: null
threat: null
component: null
---
T-0196 widened _BLOCK_LABELS/_ASSIGNMENT_LABELS/_DECLARATOR_LABELS in src/frob/dup/_pipeline.py so R5's real def-use/control-flow path (_real_dataflow_graph) now covers python, rust, typescript/tsx, c, and cpp (previously python-only via a hardcoded 'block' label check), with the co-occurrence proxy (_build_dataflow_graph) demoted to a true fallback for grammars not yet listed (e.g. strata) or unparseable regions. docs/modules/dup.md's 'Deviations from docs/modules/dup.md' section (the find_clones paragraph around R4/R5) still describes the OLD state (co-occurrence proxy as the only R5 graph, no per-language breakdown) and needs updating to disclose the new per-grammar real-vs-fallback coverage honestly, per docs/modules/dup-sota-survey.md items 7/8's ADAPT disposition. docs/modules/dup.md is NOT in T-0196's declared scope (src/frob/dup/**, src/frob/lang/**, frob-core/**, tests/**, tickets.md only), so the doc update was not made there -- filed separately rather than silently expanding scope.