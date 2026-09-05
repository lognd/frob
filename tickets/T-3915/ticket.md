---
id: T-3915
title: generalize VERSION001 into a REL-family rule for any sibling-distribution pin,
  not just frob-core/strata-core
state: queued
kind: feature
origin: human
created: '2026-09-05'
priority: low
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_version_coupling.py
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
found while working T-3903.

T-3903 fixed VERSION001's PIN-SITE coverage (match by package name across the whole root pyproject, not by table name) but left the RULE itself hardcoded to two package names (frob-core, strata-core) specific to this repo. typani's T-026 proposed the correct generalization: 'a REL-family rule that checks every <pkg>==<version> pin naming a sibling distribution in the same repo equals the repo version' -- i.e. detect sibling-distribution pins structurally (any path-dependency/workspace-member pyproject.toml under the repo root whose package name is also pinned in the root pyproject) instead of naming them.

This is the portability defect class this repo has a standing rule about (see T-3903's own MEMORY note on portability-is-a-gate-property): a rule hardcoded to two names in one repo cannot be reused by a consumer repo with different sibling packages, and if this repo ever adds a third native crate, VERSION001 needs another hardcoded name added -- the same shape of gap T-3903 just closed one level up.

DECIDING NOW (per T-3903's acceptance criterion) rather than leaving it implicit: not folding this into T-3903 itself -- generalizing the rule to detect sibling packages structurally (via path-dependency entries under [tool.uv.sources] or workspace members) is materially more design work than widening pin-site enumeration, and T-3903 is scoped narrowly to unblock the pending version bump. Filing this as a separate, lower-priority follow-up so the generalization question is answered, not silently dropped.

Cross-ref: T-3903 (pin-site coverage fix this generalizes further), typani T-026 (proposed this exact generalization).