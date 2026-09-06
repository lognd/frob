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
body_changes:
- mode: set
  reason: 'DOC006 fails CI against this ticket''s own body: the PROPOSED refs.artifact
    section written in literal TOML form parses as a live config pointer and no such
    key exists. Rewritten as prose, same fix as T-3931'
  actor: logan
  at: '2026-09-06'
  old_length: 1243
  new_length: 1463
designated_repro_test: null
acceptance:
- text: given a design note deciding what watched means for an artifact glob (annotation-required
    vs content-scanned), when this ticket's design step completes, then the note is
    attached before implementation
  evidence: []
- text: 'given the proposed refs.artifact construct is implemented (named in prose,
    not in double-bracket TOML form: as a literal section header it parses as a live
    config pointer and DOC006 correctly refuses it, because no such key exists yet),
    when a file under a declared artifact glob changes with no reasoned annotation,
    then it is flagged the same way an undeclared entrypoint change is today'
  evidence: []
acceptance_amendments:
- op: replace
  index: 1
  old_text: given [[refs.artifact]] is implemented, when a file under a declared artifact
    glob changes with no reasoned annotation, then it is flagged the same way an undeclared
    entrypoint change is today
  new_text: 'given the proposed refs.artifact construct is implemented (named in prose,
    not in double-bracket TOML form: as a literal section header it parses as a live
    config pointer and DOC006 correctly refuses it, because no such key exists yet),
    when a file under a declared artifact glob changes with no reasoned annotation,
    then it is flagged the same way an undeclared entrypoint change is today'
  reason: 'DOC006 fails CI against this criterion''s own text: a PROPOSED config section
    written in literal TOML section form is indistinguishable from a live config pointer,
    and no such key exists. Rewritten as prose, matching the same fix applied to T-3931'
  actor: logan
  at: '2026-09-06'
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-3928 frontend-unique item. VERIFIED: git grep confirms [[refs.entrypoint]] exists (src/frob/gates/_refs_schema.py, REFSCHEMA001) as a declared-surface concept, but it is for CODE entrypoints -- nothing declares a build-output/static-asset surface.

FINDING THIS WOULD HAVE CAUGHT: frontend/public/** (or equivalent verbatim-copy build directories) is outside every strata code glob and every frob entrypoint, yet ships to production byte-for-byte. The consumer's framing, worth preserving: "files that reach production without passing through a compiler is the highest-leverage unwatched surface in any frontend repo" -- these files get zero review pressure from anything frob does today because nothing treats them as reachable/shippable at all.

Proposed: a refs.artifact construct alongside the existing refs.entrypoint one (both named in prose here, not in literal double-bracket TOML form -- refs.artifact does not exist yet, so as a literal section header it parses as a live config pointer and DOC006 correctly refuses it), each file individually justified (mirroring entrypoint's own per-entry reason= discipline visible in _refs_schema.py), declaring a verbatim-copy build/static directory as a watched surface. What "watched" means in practice (min: a change to a declared artifact glob requires a reasoned annotation; ambitious: some content check e.g. no obvious secret/credential pattern) is a design decision to make explicit before implementing.
