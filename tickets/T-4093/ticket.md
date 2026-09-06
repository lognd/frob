---
id: T-4093
title: 'H3-4/H3-5: ticket-referenced exhaustive-deps disables, per-file-vs-interaction
  gap'
state: queued
kind: security
origin: agent
created: '2026-09-06'
priority: medium
parent: T-4089
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_waive.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given this ticket's design step, when it completes, then it states explicitly
    why this is distinct from T-4062 (per-file-vs-interaction, not scoped-vs-unscoped)
  evidence: []
- text: given an eslint-disable-next-line exhaustive-deps comment with free prose
    and no ticket reference, when the new check runs, then it is flagged
  evidence: []
- text: given a policy.pattern for the specific getGridRect-in-useEffect shape, when
    this ticket is scoped, then it is recorded as a separable second piece, not required
    for the first
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
H3-4/H3-5 (F-296). READ T-4062 FIRST, per the coordinator's explicit instruction, before deciding whether this is distinct. VERDICT: DISTINCT, filed as its own child.

T-4062's shape: two check SURFACES (frob check --ticket, scoped, vs. land's unscoped pre-commit sweep) disagree because they examine different SUBJECT SETS -- more files/symbols vs fewer. The fix direction there is documenting/aligning what each surface covers.

THIS ITEM'S SHAPE IS DIFFERENT: `frob check --ticket` was GREEN on all three touched files (SpinningShape.tsx, useEngineSurface.tsx, ParticleLayer.tsx) -- EVERY file that was touched WAS in scope and WAS individually checked, and each one individually satisfied DOC/TEST. The defect lived entirely in their INTERACTION: every consumer of a newly-added API (surface.getGridRect(...), a hook-returned closure) needed to adopt the SAME usage pattern, and nothing checks that cross-file consistency even when the full correct subject set was examined. This is not a scoped-vs-unscoped subject-set gap (T-4062) -- it is a PER-FILE-CORRECTNESS-vs-CROSS-FILE-INTERACTION-CORRECTNESS gap: every file passed every single-file check that exists, and the defect was still invisible, because no gate reads MULTIPLE files' USES of one API together.

FINDING THIS WOULD HAVE CAUGHT: every call site of surface.getGridRect(...) (or any hook-returned closure) from inside a useEffect whose dependency array omits it carries an eslint-disable-next-line exhaustive-deps suppression with a hand-written justification -- true for some sites (refs, which are stable) and FALSE for others (getGridRect, which is not stable across renders) -- and nothing distinguishes a correct suppression from an incorrect one because the justification is free prose.

Proposed, the smallest version per the consumer: require a frob:waive-style TICKET REFERENCE on each exhaustive-deps disable comment, rather than free prose -- turning an unverifiable hand-written justification into a tracked, reviewable exception the same way frob:waive already works for frob's own rules. The FULLER version -- a [[policy.pattern]] flagging exactly the getGridRect-in-useEffect-with-missing-dep shape -- is the more complete fix; scope the ticket-reference requirement as the cheap first step and the specific pattern as a second, separable piece.
