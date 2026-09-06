---
id: T-3976
title: 'refs.artifact: declared surface for verbatim build-output directories'
state: queued
kind: security
origin: agent
created: '2026-09-06'
priority: medium
parent: T-3928
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_refs_schema.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given a design note deciding what watched means for an artifact glob (annotation-required
    vs content-scanned), when this ticket's design step completes, then the note is
    attached before implementation
  evidence: []
- text: given [[refs.artifact]] is implemented, when a file under a declared artifact
    glob changes with no reasoned annotation, then it is flagged the same way an undeclared
    entrypoint change is today
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-3928 frontend-unique item. VERIFIED: git grep confirms [[refs.entrypoint]] exists (src/frob/gates/_refs_schema.py, REFSCHEMA001) as a declared-surface concept, but it is for CODE entrypoints -- nothing declares a build-output/static-asset surface.

FINDING THIS WOULD HAVE CAUGHT: frontend/public/** (or equivalent verbatim-copy build directories) is outside every strata code glob and every frob entrypoint, yet ships to production byte-for-byte. The consumer's framing, worth preserving: "files that reach production without passing through a compiler is the highest-leverage unwatched surface in any frontend repo" -- these files get zero review pressure from anything frob does today because nothing treats them as reachable/shippable at all.

Proposed: `[[refs.artifact]]` alongside `[[refs.entrypoint]]`, each file individually justified (mirroring entrypoint's own per-entry reason= discipline visible in _refs_schema.py), declaring a verbatim-copy build/static directory as a watched surface. What "watched" means in practice (min: a change to a declared artifact glob requires a reasoned annotation; ambitious: some content check e.g. no obvious secret/credential pattern) is a design decision to make explicit before implementing.
