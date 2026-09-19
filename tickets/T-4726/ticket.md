---
id: T-4726
title: docs/modules/vet.md rule rows VET006/008/009/010 describe unimplemented designs
  under live rule ids; align with gates.md and the emitting sites
state: in-progress
kind: docs
origin: human
created: '2026-09-19'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/modules/vet.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/modules/vet.md
  reason: align rule rows with implemented gates.md and emitting sites
  actor: logan
  at: '2026-09-19'
body_changes:
- mode: set
  reason: add description/plan/acceptance for docs alignment
  actor: logan
  at: '2026-09-19'
  old_length: 0
  new_length: 2163
designated_repro_test: null
acceptance:
- text: vet.md VET006/008/009/010 rows read identically in substance to gates.md's
    descriptions of those rule ids.
  evidence: []
- text: No unimplemented design (artifact/source divergence, stylometric self-similarity,
    sandbox detonation, cadence/maintainer signals) appears under a live VET0xx id
    anywhere in vet.md.
  evidence: []
- text: Unimplemented designs are either linked to an existing backlog ticket or listed
    under a clearly labelled Planned detectors (no rule id yet) heading with no rule
    ids.
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Description
docs/modules/vet.md rows for VET006 (line ~229) and VET008/VET009/VET010 (lines ~452-454)
plus a "signals" row describe design-wishlist detectors written 2026-07-17 (commit d9387a9602):
VET006 as "lockfile and manifest disagree", VET008 as artifact/source divergence, VET009 as
stylometric self-similarity, VET010 as dynamic/static divergence. These do not match what is
implemented today:
- gates.md (commit 3abdbd2c41, 2026-08-06, T-1088) documents the real meanings.
- src/frob/vet/_scan_violations.py:140 emits VET006 for a CVE fingerprint match.
- src/frob/vet/_supplychain.py:279/300 emits VET008 for a data_files path escape.
- src/frob/vet/_supplychain.py:385 emits VET009 for a mutable action ref.
- src/frob/vet/_supplychain.py:440 emits VET010 for a committed binary blob.

vet.md currently makes live-looking rule ids describe detectors that do not exist, which will
mislead anyone reading the rule table to understand what VET006/8/9/10 actually fire on.

## Plan
1. Rewrite vet.md's VET006/VET008/VET009/VET010 rows to match gates.md's wording (gates.md as the
   single source of truth for what each rule id means).
2. Check `git grep -l "detonation\|stylometric" -- tickets/` for an existing backlog ticket
   describing the unimplemented designs (artifact/source divergence, stylometry, sandbox
   detonation, cadence/maintainer signals).
   - If found: move the unimplemented-design text into a one-line pointer to that ticket.
   - If not found: create a "Planned detectors (no rule id yet)" list in vet.md with no live-looking
     rule ids, containing the moved design text.
3. No code changes. Docs only (--no-behavior-change close).

## Acceptance criteria
- vet.md VET006/008/009/010 rows read identically in substance to gates.md's descriptions of those
  rule ids.
- No unimplemented design (artifact/source divergence, stylometric self-similarity, sandbox
  detonation, cadence/maintainer signals) appears under a live VET0xx id anywhere in vet.md.
- Unimplemented designs are either linked to an existing backlog ticket or listed under a clearly
  labelled "Planned detectors (no rule id yet)" heading with no rule ids.
