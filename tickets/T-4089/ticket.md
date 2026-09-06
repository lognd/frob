---
id: T-4089
title: 'F-296: engine round-3 audit -- contracts stated in prose, enforced on one
  side of an ABI boundary and unenforced on the other'
state: queued
kind: security
origin: human
created: '2026-09-06'
priority: high
parent: null
tier: epic
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
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
Consumer logand.app-v2 F-296 (engine round-3 audit, 2026-09-06), verbatim in
their FROBLEMS.md. NINTH audit list from that repo. Prior eight: T-3919, T-3920,
T-3928, T-3942, T-3984, T-4025, T-4036, T-4071.

READ THE FULL TEXT under "## F-296" in ../logand.app-v2/FROBLEMS.md. As with
T-4071 the auditor names a candidate rule per finding, so most of the design work
is done.

THE RECURRING STRUCTURE IN THIS ROUND is contracts stated in PROSE that hold on
one side of a boundary and are unenforced on the other:

  H3-1  Strata SYS-031 states "engine functions operate on caller-owned buffers
        with explicit cols/rows/count parameters" -- ENFORCED IN RUST BY HAND AND
        UNENFORCED IN TYPESCRIPT. A fallback implementation of a wasm ABI entry
        point should refuse a length mismatch the same way its wasm twin does.
  H3-3  COMP-1703/1712 say "time-decaying" WITHOUT NAMING THE EPOCH, so the
        caller was free to pass a different clock than the callee assumed. They
        propose a units/epoch obligation on a time-typed ABI parameter.
  H3-2  gate:DOC verified getGridRect's pointer is FRESH; nothing checks that the
        row it points at stays dimensionally coherent once ANOTHER row's
        acceptance criterion writes a transform onto the same container. A
        cross-row contradiction inside ONE spec table that no gate reads as a
        pair.

H3-2 IS THE SECOND ARRIVAL OF "NO GATE COMPARES TWO L5 ROWS AGAINST EACH OTHER"
-- T-4075 was filed from T-4071's M-2 for exactly that shape. CROSS-REFERENCE
T-4075 rather than filing a third; this instance strengthens it with a
dimensional/coordinate-system example rather than a role-permission one.

H3-1's SECOND HALF IS SEPARABLE AND CHEAPER: "a subscriber's throw killing the
loop" needs only a frob:invariant on createSharedFrameLoop ("the RAF chain re-arms
on every tick regardless of what a subscriber does") with evidence bound to a test
whose subscriber throws. That is a concrete, testable obligation with no new rule
kind required -- file it as its own child, ahead of the ABI-parity work.

H3-1 ALSO NAMES A TESTING TRAP WORTH RECORDING BEYOND THIS AUDIT: the bound
evidence drives React through `act()`, "which flushes passive effects
SYNCHRONOUSLY, so the render/effect window the real scheduler opens SIMPLY DOES
NOT EXIST UNDER TEST". So a test can be genuinely bound, genuinely passing, and
structurally incapable of observing the defect it is cited for. That is the
doubles/adapter-divergence shape already tracked as T-3933 and T-4025 item 11 --
note it there, because it is the clearest statement of the problem yet: the test
harness does not merely approximate the runtime, it ELIMINATES the window.

H3-4/H3-5 REPORT `frob check --ticket` GREEN ON ALL THREE TOUCHED FILES while the
defect lived in their interaction -- each file individually consistent. That is
T-4062's territory (a scoped check used as a prediction of a wider one) seen from
a new angle: not scoped-vs-unscoped, but PER-FILE-vs-INTERACTION. Read T-4062
before filing; if it is distinct it deserves its own child, and the distinction is
worth stating either way.

GUIDANCE, unchanged: DO NOT BUILD ALL OF IT. Decompose, keep the audit's ordering,
name the finding each child would have caught, and VERIFY EACH AGAINST WHAT
EXISTS FIRST -- six items across the earlier epics turned out already implemented
or partially so.

ACCEPTANCE
- The createSharedFrameLoop re-arm invariant filed first as the cheapest concrete
  obligation.
- H3-2 cross-referenced to T-4075, not refiled.
- The act()-eliminates-the-window observation appended to T-3933.
- H3-4/H3-5 checked against T-4062 before filing.