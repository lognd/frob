---
id: T-draft-9a7659d9
title: 'LAYOUT: stale review verdict must refuse frob check --ticket (auto-reverify
  cmd evidence)'
state: queued
kind: feature
origin: human
created: '2026-09-24'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: v0.537.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
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
Owner decision (CRUNK-GALLERY-TREE.md section 5, Q3): a crunk gallery
review verdict expires on ANY byte change of the component's source or
its fixture props -- source_hash is sha256(source_bytes +
fixture_props_bytes) (crunk's compute_source_hash), a byte hash, not a
visual diff. Any change to either input re-opens review.

Currently (T-5768) a review verdict is recorded as ticket evidence via
the existing --evidence-cmd channel (add_cmd_evidence, T-0215), and
re-verification of that recorded command's continued success is only
available through reverify_cmd_evidence (frob.tickets._evidence),
which is deliberately opt-in and NOT wired into a bare
`frob check --ticket <id>` run by default -- this is a catalogued-not-
enforced gap: a stale verdict is representable and detectable, but
nothing makes frob check --ticket actually refuse on it today.

This ticket wires that in: `frob check --ticket <id>` must call
reverify_cmd_evidence over the ticket's cmd: evidence entries and
refuse (non-zero exit, a real diagnostic) when a recorded verdict-check
command's evidence is stale, without changing reverify_cmd_evidence's
opt-in posture for every OTHER caller (T-0398/D-10's non-ticket
call sites keep their existing behavior; this only changes the
`--ticket` path's own default).

Positive control: bind --evidence-cmd evidence for a ticket to a
verdict-check command; change the command's underlying source (the
same script re-hashing to a different digest, simulating the manifest
entry's source_hash changing after the verdict was recorded); the SAME
command now produces different stdout, so a subsequent
`frob check --ticket <id>` run must refuse with a real diagnostic
naming the stale evidence -- not a silent pass.

Doc page: docs/strata/vmodel.md#layout-verification-node (update the
existing "NOTE, honestly" paragraph once this lands, since it currently
documents the opt-in-only limitation this ticket closes).

Cross-repo note: this is purely frob-side; no crunk dependency.
