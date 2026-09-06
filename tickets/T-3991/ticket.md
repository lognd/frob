---
id: T-3991
title: 'GEN001: declared-generated-files block plus drift gate'
state: queued
kind: feature
origin: agent
created: '2026-09-06'
priority: low
parent: T-3984
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/policy/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given a design note for the declared-generated-files schema (source, generator
    command, output) and at least one candidate first-adopter case in this repo, when
    this ticket's design step completes, then the note is attached before implementation
  evidence: []
- text: given a declared generated-file entry whose generator output no longer matches
    the checked-in file, when the new gate runs, then GEN001 fires
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
F-203 (T-3984 item 8). VERIFIED: git grep for GEN001 across src/frob found nothing -- no existing declared-generated-files construct or gate.

FINDING THIS WOULD HAVE CAUGHT: three hand-written drift tests, each independently re-verifying that a generated file matches its generator's current output, duplicating the same check-command-and-diff logic three times (the exact "two copies of a rule is a bug waiting to desync" shape this repo's own CLAUDE.md names). Proposed: a declared-generated-files block (source file -> generator command -> output file) plus one gate that runs each declared check command and diffs the result, replacing the three hand-written tests with one data-driven mechanism.

FIRST STEP: identify which three hand-written drift tests the consumer means is not directly determinable from our side (this is their repo's shape) -- so this ticket's first task is designing the declared-generated-files schema generically, then finding this repo's OWN analogous hand-written generated-file drift tests (if any) as a first adopter/proof of concept before rolling it out as a general frob feature.
