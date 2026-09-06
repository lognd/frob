---
id: T-3996
title: 'required_file: declared surface for untracked-but-mandatory artifacts'
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
- src/frob/gates/_refs_schema.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given a design note settling when required_file is checked (build vs deploy
    vs both) and how it composes with refs.entrypoint, when this ticket's design step
    completes, then the note is attached before implementation
  evidence: []
- text: given a declared required_file entry whose path is missing at the checked
    point, when the check runs, then it is flagged
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
F-208 (T-3984 item 13). VERIFIED: git grep for required_file across src/frob found nothing. [[refs.entrypoint]] (src/frob/gates/_refs_schema.py, REFSCHEMA001) already declares code entrypoints that must exist and be justified; there is no inverse declaration for an untracked-but-mandatory NON-code artifact.

FINDING THIS WOULD HAVE CAUGHT: a policy artifact (a config file, a required security header file, a deployment manifest) that must exist on disk at deploy/build time but is not itself tracked in git (generated, fetched, or provisioned out-of-band) and has no declared surface at all -- so its absence is invisible to every existing gate, none of which know it is supposed to exist. Proposed `required_file` construct: the inverse of refs.entrypoint -- declares a path that must exist (checked at the point it matters, e.g. build/deploy time) without requiring it be git-tracked, each entry individually justified the same way refs.entrypoint entries are.
