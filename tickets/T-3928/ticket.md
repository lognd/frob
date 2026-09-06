---
id: T-3928
title: the edge/ops and frontend audit lists, and the five asks that four independent
  audits converged on
state: queued
kind: security
origin: human
created: '2026-09-05'
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
Two further audit lists from the same consumer repo (logand.app-v2), both
2026-09-05: the EDGE/OPS/ENGINE audit (their F-109..F-117, sourced from
docs/security/audit-2026-09-05-edge-ops-engine.md) and the FRONTEND SHELL audit
(their F-148..F-155, sourced from docs/security/audit-2026-09-05-frontend-shell.md).
Both READ-ONLY over there.

T-3919 covers the BACKEND audit and T-3920 the THREAT-MODEL pass. This ticket
covers the other two, and exists mainly to carry the CONVERGENCES -- because
four independent audits of one codebase, by different passes over different
subsystems, asked for some of the same things.

THE CONVERGENT ASKS ARE THE HIGHEST-CONFIDENCE WORK IN ANY OF THE FOUR LISTS.
Where two audits independently reach the same proposal from different
directions, that is far stronger evidence than one auditor's preference:

  1. DOCSTRING CLAIMS SHOULD BECOME TRACKED OBLIGATIONS.
     backend item 4: "in one transaction", "can be reached", "per-IP lockout
       check", "no loop is ever nested" were all FALSE CLAIMS; auto-propose
       frob:invariant obligations from keywords (atomic/transaction/idempotent/
       single-use/constant-time/always/never).
     frontend item 3: a docstring stating a FAILURE behaviour ("cleared on
       failure so the next mutation gets to retry") that the code does not
       implement, with frob:tests satisfied by a HAPPY-PATH test. Proposes
       `frob:tests <symbol>::<test> covers="failure-path"` and reporting a
       conditional-behaviour claim with no covers= evidence.
     SAME ASK, TWO ROUTES. The frontend framing is the more implementable one
     because it binds a SENTENCE to a TEST rather than inferring an invariant.

  2. TRUST/PROVENANCE HAS NO CONSTRUCT.
     backend item 6: provenance for PII atoms, a derived_from edge so SYS100
       can require a single helper produce every client IP.
     threat-model item 6: the capability ratchet polices what code may DO;
       nothing polices what it may TRUST AS IDENTITY.
     Already recorded on T-3920 as its deepest item; noted here because the
     second independent arrival is what makes it the strongest signal.

  3. A SHELL GRAMMAR FOR ops/**.
     threat-model item 3 and edge/ops item 2 both request it; edge/ops adds two
     findings that need nothing else (a database password in pg_dump's argv --
     a REGRESSION of the very ticket that fixed the identical bug for rclone in
     the same file -- and an unwrapped destructive rm -rf in a script
     documenting itself as printing-only under DRY_RUN). Their key caveat:
     ship a STARTER POLICY CATALOGUE with the grammar, because "the grammar
     alone only makes rules possible".

  4. AN INVARIANT WAIVER/PROPOSED PATH.
     threat-model item 8 and edge/ops item 6 both report that INV001/INV002
     have no waiver path (unlike INV003/INV004), so an invariant describing a
     KNOWN, TICKETED, NOT-YET-FIXED gap cannot be committed. edge/ops adds the
     cost: `invariants/` is therefore EMPTY AND THE INVARIANT GATE PASSES
     VACUOUSLY ON EVERY RUN -- a silent zero in frob's own invariant system.

  5. A KNOWN-DANGEROUS-COMPARISON-IDIOM RULE.
     backend item 10 (a lint for substring tests over request paths) and
     threat-model item 5 (semantic authorization bugs, substring vs prefix)
     are the same rule kind, both called cheap.

ITEMS UNIQUE TO THESE TWO LISTS, worth their own children:

  EDGE/OPS
   - xfail/xpass/skip MUST NOT SATISFY a frob:tests or ticket evidence binding.
     Catches a process gate that pytest-xfails away every violation and can
     never fail, and a component whose whole suite skips when a toolchain is
     absent. Default to outcome==passed; provide an explicit opt-in that shows
     up as a distinct, COUNTABLE state rather than as green. THIS ONE BEARS ON
     FROB'S OWN EVIDENCE INTEGRITY -- if xfail satisfies evidence here, every
     "fail-then-pass" claim in this repo is weaker than it reads.
   - a YAML grammar (or compose/workflow scanner) -- four findings are pure
     YAML: one env_file shared by five services of different trust levels, no
     cap_drop/read_only/no-new-privileges, dev stores bound to 0.0.0.0.
   - extend frob vet to GitHub Actions `uses:` -- ALREADY ACTED ON, see T-3922
     (measured: 0 of frob's own 8 actions are SHA-pinned) and T-3923.
   - a policy.pattern for length-validation-by-unchecked-multiply in Rust; no
     new grammar needed, and the CORRECT pattern exists three modules from the
     broken one.

  FRONTEND
   - "fetch result consumed without checking .ok" -- a structural tree-sitter
     shape over ts/tsx with near-zero false positives; generalises to any
     promise-returning API with a status field.
   - VERBATIM-COPY BUILD DIRECTORIES AS A DECLARED SURFACE. frontend/public/**
     is outside every strata code glob and every frob entrypoint, yet ships to
     production byte-for-byte. Proposes `refs.artifact` alongside
     refs.entrypoint, each file individually justified. Their claim, worth
     taking seriously: "files that reach production without passing through a
     compiler is the highest-leverage unwatched surface in any frontend repo".
   - "the assertion is about the pointer, not the pointee" as a TEST SMELL:
     asserting href == "#main" without ever asserting #main exists. Mechanical.
   - CROSS-LANGUAGE CONSTANT PAIRS: a `frob:mirror` directive asserting literal
     equality across languages (a TS constant and a Python constant that must
     agree forever). This is CLAUDE.md's own "two copies of a rule is a bug
     waiting to desync" made checkable, and needs no taint analysis.
   - `frob:pending T-####` to distinguish RED-BECAUSE-UNIMPLEMENTED from
     RED-BECAUSE-BROKEN. Note this pairs with the TDD pincer already recorded
     (TDD001 pushes tests first, --check-repro requires them red, DRIFT002 then
     fires on the red test's own directive): spec-first ordering currently
     destroys the suite's signal, and this is the missing half.

GUIDANCE, same as T-3919's: DO NOT BUILD ALL OF IT. Decompose, keep each
audit's own ordering as its priority order, and file each child naming the
finding it would have caught. VERIFY EACH AGAINST WHAT EXISTS FIRST -- several
may be partially implemented, and this repo's rule is that "nothing enforces X"
is a claim about code that must be grepped before it is believed.

START WITH THE FIVE CONVERGENCES. They are the only items with independent
corroboration, and two of them (the invariant waiver path, xfail-satisfying-
evidence) are about FROB'S OWN GUARANTEES being weaker than they read -- which
outranks new detection.
