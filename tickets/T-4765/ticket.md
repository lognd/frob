---
id: T-4765
title: 'Facet engine: extend the managed-block primitive into ownership, ordering,
  conflicts and removal, with an add verb, a facets listing and a post-new recommendation
  footer'
state: queued
kind: feature
origin: human
created: '2026-09-19'
priority: high
blocked_by:
- T-4760
- T-4761
parent: T-4757
tier: ticket
sprint: null
runs_last: false
milestone: 1.1.0
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
- src/frob/scaffold/_facets.py
- src/frob/scaffold/project.py
- src/frob/app/scaffold_runner.py
- src/frob/_cli_parsers/_core.py
- docs/commands/scaffold.md
- tests/unit/test_scaffold_facets.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.537.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
- field: sprint
  old_value: v0.537.0
  new_value: v1.1.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
designated_repro_test: null
acceptance:
- text: Given two facets contributing blocks to one file, when both are applied, then
    both blocks land in declared order, asserted on file content
  evidence: []
- text: Given a facet whose conflicts entry is already applied, when it is added,
    then it is refused and the message names both facets
  evidence: []
- text: Given a facet whose requires entry is absent, when it is added, then it is
    refused naming the missing facet
  evidence: []
- text: Given a facet whose block was hand-deleted, when the facets listing runs,
    then it reads as not applied
  evidence: []
- text: Given a fixture facet with a recommended_for entry, when a project of that
    base is created, then the footer lists it with its capability sentence and add
    command, with no runner change
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Facets before web-service. Adding web-service as an eighth monolithic type
would be a FIFTH fork of the python frob.toml, pyproject and CI workflow --
the exact mechanism that has already lost the refs block four times.

The managed-block engine in src/frob/scaffold/_managed.py is a sound
idempotent in-place text-region primitive (digest compare, never clobbers
user content, foreign git hooks left untouched -- all verified empirically).
It is NOT a facet system: audit 6.1 measures it as lacking per-facet
ownership, ordering, conflict refusal, removal and whole-file ownership.
Extend it; do not replace it.

A facet manifest carries: id (the argument to the planned add verb);
capability (the single one-line sentence that the help text, the post-new
footer and the facet listing all read, so it has one home); bases; requires;
conflicts; recommended_for (the field that makes the recommended set DERIVED
data rather than a hardcoded table in the runner); owned_files (whole files
the facet creates and can remove); blocks (target, block id, order, content
for the shared files it contributes to). Applied is DETECTED by the same
digest compare the engine already does over marker blocks and owned files --
never a separate stamp file, matching the engine's existing no-stamp
posture, so a hand-deleted facet reads as not-applied rather than lying.

Ordering matters now: the engine's own comment states order is irrelevant
because each block targets a distinct file, an assumption that dies the
moment two facets contribute to one file and one must precede the other.

New surface: an add verb applying one facet to an existing tree; a facets
verb listing applied, applicable and conflicting; and the new verb ending by
printing the applicable-not-applied facets, one line each with the
capability sentence and the exact add command, plus the recommended set for
that base. Today new prints only one created line per file and returns, and
the list verb prints bare type names with no metadata at all.

Types become presets over base plus facets.

Positive controls:
1. two facets contributing blocks to ONE file both land, in declared order,
   and the order is asserted on file content;
2. adding a facet whose conflicts entry is already applied is REFUSED, and
   the message names both facets;
3. adding a facet whose requires entry is absent is refused, naming the
   missing facet;
4. a facet whose block is hand-deleted reads as not-applied in the listing;
5. the post-new footer for a given base is generated purely from manifests
   -- a test adds a fixture facet with a recommended_for entry and asserts
   it appears in the footer with no runner change.
