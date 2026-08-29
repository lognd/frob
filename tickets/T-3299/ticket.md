---
id: T-3299
title: SCOPE002/AFFECT001 fan out to every anchor on a shared subsystem doc
state: queued
kind: bug
origin: human
created: '2026-08-28'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/__init__.py
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
REPORTED FROM REAL CONSUMER USE (../diax FROBLEMS.md F-010, F-050, F-047).

ROOT CAUSE (as diagnosed independently by two different reports, consistent
with each other): SCOPE002's doc-anchor scope closure treats a shared
subsystem doc (one page describing many symbols under many headings) as a
single indivisible unit. Touching ANY symbol the doc describes pulls a
warning for EVERY OTHER symbol/anchor on that same page, and AFFECT001's
doc-must-be-touched requirement inherits the same all-or-nothing shape
against the SAME page, which is exclusively lease-held by one ticket at a
time.

THREE REPORTS:
  - F-010: docs/index.md#public-api describes the whole scaffold surface as
    one anchor; touching one file pulled a 21-entry scope onto a narrow
    bug-fix ticket, two rounds of `scope --add`.
  - F-050: docs/subsystems/model.md describes five modules
    (schema/io/ids/defaults/errors); a ticket touching one section got 35
    SCOPE002 warnings, one per anchor for symbols the ticket never touched.
    The gate's own suggested remediation ("scope --add
    src/diax/model/schema.py") is literally the scope inflation SCOPE001
    exists to prevent -- the gate's remedy for one rule fights another rule.
  - F-047: same doc, same shape, but hits AFFECT001 instead: the doc is
    leased whole-page by whichever ticket holds it (only one at a time), so
    a DIFFERENT ticket that legitimately changed four documented symbols
    could not satisfy AFFECT001's "touch the doc in the same diff" demand
    while the lease was held elsewhere. Only exit was four in-source
    `frob:waive AFFECT001 follow_up=` waivers plus a filed doc ticket --
    exactly the doc drift AFFECT001 exists to prevent, forced by the gate's
    own page-granularity.

WHAT NOT TO DO: do not just raise SCOPE002's warning threshold or silence it
wholesale -- it exists to catch real doc-drift risk when a ticket's scope
genuinely diverges from what a doc describes; the defect is GRANULARITY
(whole-page), not the check's existence. Do not solve AFFECT001's lease
conflict by making subsystem docs droppable/unleased either -- that
reintroduces exactly the concurrent-edit races leases exist to prevent.

WHAT TO BUILD:
  1. SCOPE002 closure/warnings should stop at the HEADING(S) the diff
     actually touches, not fan out to every other heading on the same page
     (per F-050's specific ask). If a doc has no heading structure granular
     enough to do this, that is itself worth surfacing as a docs
     organization problem, not solved by suppressing the gate.
  2. AFFECT001 should offer a PER-HEADING (anchor-level) lease on subsystem
     docs, or -- if that is too large a change to bundle here -- an explicit
     exemption path: when the target doc is provably leased by another
     in-progress ticket, AFFECT001 auto-files (or accepts, without a manual
     waive dance) the follow-up doc ticket F-047's workaround had to build
     by hand.

MUST-FIRE FIXTURE: a doc with two headings, H1 (describing module A) and H2
(describing module B); a ticket that edits only module A must get 0 SCOPE002
warnings for H2's anchors.

MUST-STAY-QUIET is the wrong frame here -- the important REGRESSION check is
that a ticket which touches BOTH modules A and B, or whose scope genuinely
diverges from the whole doc, still gets the SCOPE002 warning it should.
