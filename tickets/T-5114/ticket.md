---
id: T-5114
title: 'multi-file module litmus with golden findings: private-name import, one-sided
  flow, import cycle, templated assume'
state: queued
kind: feature
origin: human
created: '2026-09-19'
priority: critical
blocked_by:
- T-5125
- T-5102
- T-5087
- T-5105
parent: T-5081
tier: ticket
sprint: null
runs_last: false
milestone: 0.536.0
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
- design/litmus/modules/**
- tests/system/test_litmus_modules.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.536.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
designated_repro_test: null
acceptance:
- text: Given design/litmus/modules/ and the golden findings file, when the litmus
    suite runs, then the legal case passes and each of the four refusal cases (private-name
    import, one-sided flow, import cycle, templated assume) produces exactly its golden
    finding, matched by rule id and message.
  evidence: []
- text: Given any one of leaves 1-5 reverted, when the litmus suite runs, then the
    corresponding golden flips -- the goldens are positive controls, not snapshots
    of whatever the code currently prints.
  evidence: []
- text: Given the pre-existing 7 single-module litmus files, when the suite runs,
    then their results are unchanged.
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Multi-file litmus with golden findings. There is NO multi-file litmus today --
all 7 design/litmus/*.strata files declare their own independent `module` root
and zero use `part of`. Add a litmus program under design/litmus/modules/ that
is genuinely multi-module, plus golden expected findings for each refusal:
  (a) a legal import + export path that must pass;
  (b) an import of a private (unexported) name -> refusal naming the id and its
      owning module;
  (c) a one-sided cross-module flow (importer declares, exporter has no
      `accepts`) -> refusal;
  (d) an import cycle -> refusal printing the full path;
  (e) a templated assume (two assumes identical modulo node name) -> refusal.
Each golden is the positive control for one of leaves 1-5: if a leaf regresses,
its golden flips.
