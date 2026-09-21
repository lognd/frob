---
id: T-draft-330aa06d
title: unity-project scaffold's design/*.strata fragments have no root module declaration,
  unparseable standalone
state: queued
kind: bug
origin: human
created: '2026-09-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/scaffold/_unity_project.py
- src/frob/scaffold/data/types/unity-project/**
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
Found while working T-4509 (Unity capstone e2e proof): render_unity_project (T-4503) writes one design/<node_id>.strata file per asmdef via render_unity_fragment/write_unity_fragment (T-4512), but render_unity_fragment emits only 'node {...}'/'flow ...' blocks, never a leading 'module ...;' declaration. frob check's strata loader then fails each fragment standalone: 'strata-core rejected source at line=4 col=1: statement before module declaration'. Repro: scaffold unity-project onto tests/fixtures/unity_sample (T-4509's fixture) and run frob check --only dead_symbols (or any strata-parsing gate) against it -- every design/unity_*.strata file logs a ParseFailed warning. docs/strata/surface.md's own T-4512 section says this output is 'loaded and merged the same T-1196 multi-file way any other independently-named root .strata file already is', which requires SOME design/*.strata file in the tree to carry the module declaration -- but neither T-4503's scaffold manifest nor T-4512's writer ever emits one for a fresh unity-project scaffold. Fix: either render_unity_project's manifest should also scaffold a starter design/frob.strata with a module declaration, or render_unity_fragment should emit one itself when used as this scaffold's sole design/ output. Does not block T-4509's own acceptance criteria (dead_symbols and other python-callable gates still ran clean; only strata-parsing-dependent gates are affected), so filed as a follow-up rather than fixed in T-4509's own out-of-scope files.