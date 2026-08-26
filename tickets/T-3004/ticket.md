---
id: T-3004
title: 'Epic: strata as the language of software development -- typed V-model spec
  graph, multi-modal redesign, enforced TDD'
state: queued
kind: feature
origin: human
created: '2026-08-26'
priority: high
parent: null
tier: ticket
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
OWNER DESIGN DECISION, 2026-08-26. Recorded here ONCE so children reference it
rather than restating it -- restating it in six ticket bodies would be the same
narrative bloat epic T-2994 exists to stop.

GOAL: frob gains a partial-waterfall-into-agile development model, expressed as
a TYPED, TYPE-CHECKED GRAPH rather than scattered markdown. Strata becomes the
language of software development, not merely of system architecture, and is
REDESIGNED rather than extended -- the owner's assessment is that the current
model has good pieces but is half-baked as an idea.

--------------------------------------------------------------------
1. THE ENFORCEABLE CORE: the V pairing
--------------------------------------------------------------------
The V-model's real content is that every left-side artifact NAMES ITS OWN
VERIFICATION LEVEL. The owner's own pairing:

    requirements (elicitation/analysis)  <-> customer test
    requirement specification            <-> customer test plan
    system specification                 <-> system integration test plan
    system design                        <-> subsystem integration test plan
    component design                     <-> component unit test

Everything else about waterfall is ceremony. That pairing is the part a machine
can check, and frob already implements a ONE-LEVEL version of it: `frob:tests`
binds code to tests, `frob:doc` binds code to docs, evidence binds tickets to
test nodes. This work GENERALISES an existing binding from one level to N. It is
not a greenfield system.

--------------------------------------------------------------------
2. STRUCTURAL CLOSURE, NOT QUALITY -- the key constraint
--------------------------------------------------------------------
The owner: "I want *a* specification (although likely not a GOOD ONE) to be
finished before any code starts being implemented."

That parenthetical is what makes this mechanically enforceable. Quality is not
checkable; STRUCTURAL CLOSURE is. The gate is that every customer goal has a
typed, unbroken path down to a test. A bad-but-complete specification passes; a
brilliant-but-dangling one fails.

Four closure rules, checked in BOTH directions (the same doctrine frob already
applies to scope: doc+code edge closure both ways):
  1. every requirement is satisfied by >=1 design element -- no orphan requirement
  2. every design element traces to >=1 requirement       -- no unjustified code
  3. every requirement has >=1 verification AT ITS PAIRED LEVEL -- no untested requirement
  4. every test verifies something                        -- no orphan test

--------------------------------------------------------------------
3. A GRAPH, NOT BLOCKS
--------------------------------------------------------------------
The owner explicitly does not want `blocked_by` as the organising relation.
Blocking is a SCHEDULING fact; what is wanted is SEMANTIC edges:

    refines, allocates, satisfies, verifies, decides, supersedes

`blocked_by` survives as ONE edge type among many -- sequencing is real -- just
not the organising one.

--------------------------------------------------------------------
4. WHERE THE KERNEL LIVES: strata-core, as a new layer
--------------------------------------------------------------------
Measured 2026-08-26:
  - `frob-core` is a SOURCE-CODE kernel: py_function_metrics, called_names,
    resolve_call_edges, near_duplicate_indices, scan_python_capabilities,
    extract_tree_python/rust/cpp. A spec graph there is a category error.
  - `strata-core` is a LANGUAGE FRONT-END: ~4,700 lines, almost entirely parser
    (lexer, grammar_core/flow/infra/node/policy, parse/mod.rs at 1,747 lines).
    It owns declarative-language syntax but has no graph or semantic layer.

So the graph kernel is a NEW layer BESIDE the parser, not an extension of it:

    strata-core::graph   NEW -- typed nodes, typed edges, closure, reachability,
                         level constraints, cycle detection. Generic.
    strata-core::parse   exists -- strata language front-end

Specs, decisions, tickets and the existing architecture model then become
INSTANCES of one graph instead of four bespoke stores. That is what buys the
type checking, and it removes the scattered-markdown problem structurally rather
than by convention.

--------------------------------------------------------------------
5. MULTI-MODAL STRATA -- IN SCOPE (owner decision)
--------------------------------------------------------------------
VHDL's entity/architecture/configuration split is the model:

  BEHAVIOUR (entity)      what a component MUST do -- obligations, invariants,
                          interface contract, capability ceiling. Declarative,
                          verifiable, no implementation.
  IMPLEMENTATION (arch)   how it is realised -- `code=` bindings, subcomponents,
                          flows. Today's `.strata` is ONLY this half.
  CONFIGURATION           which architecture binds where.

One entity, MANY architectures. That is what makes incremental releases fall out
for free (section 6) rather than needing separate machinery.

The owner's assessment is that current strata is half-baked, so this is a
REDESIGN. Current surface, for reference: grammar is node/flow/store/module/may/
code/clearance/assume/listens/pipe/carries; rules are SYS001-004 (directive
binding, undeclared cross-component import, parse failure), SYS100-112
(declared-vs-observed self-conformance), SYS200-205 (resource conflicts). The
SYS200-205 family catches real system bugs and should survive the redesign; the
SYS100-112 bookkeeping family is the part already being narrowed to a
shrink-only ratchet under T-2920, and the redesign must not reintroduce a
sync-shaped ceiling.

--------------------------------------------------------------------
6. INCREMENTAL RELEASES
--------------------------------------------------------------------
frob itself is fine requiring a full build before release. OTHER projects built
with frob need milestones that ship half-baked-but-usable increments.

With entity/architecture this is not new machinery: a milestone selects a
CONFIGURATION binding a PARTIAL architecture satisfying a DECLARED SUBSET of the
entity's obligations, with the remainder marked as an explicit gap. Release
gating checks THAT MILESTONE's closure, not the whole graph. This is the
KNOWN_GAP pattern from `frob.lang._support` generalised: tracked, not silent.

--------------------------------------------------------------------
7. TDD, ENFORCED
--------------------------------------------------------------------
The owner emphasised test-first: plan tests before implementing; unit tests
before implementation.

This is checkable from git history -- a verification node's introducing commit
must precede its implementation node's. frob already does a special case:
BUG002 requires a repro that fails at the parent commit. Generalising that from
bug-repros to every specification level yields MECHANICALLY ENFORCED TDD, which
is rare in practice and is the highest-value single piece of this epic.

Related: invariants are currently FLAT (INV001 needs standing evidence, INV002
needs a code anchor -- no level concept). They become MULTI-LEVEL: an invariant
declared at level L must be verified by a test at L's paired level. That kills a
real and common lie -- a system property nominally verified by a unit test that
structurally cannot observe it.

--------------------------------------------------------------------
8. CHANGE JUSTIFICATION, NOT IN-LINE
--------------------------------------------------------------------
Changing a higher waterfall layer requires justification, and the owner was
explicit that it must NOT be in-line. It is a typed `supersedes` edge carrying a
reason on the DECISION node. This is epic T-2994's doctrine applied upward:
artefacts carry utility, the graph carries narrative.

--------------------------------------------------------------------
9. DEFERRED BY OWNER DECISION
--------------------------------------------------------------------
- THE WATERFALL GATE (no implementation until the spec closes) is explicitly
  saved for later. Build the graph, the specs, and the TDD ordering first; the
  hard gate comes after.
- TICKET MIGRATION into the graph kernel is deferred and must NOT be first. The
  ticket ledger is the most load-bearing and most-contended machinery in the
  system -- on 2026-08-26 alone it produced a state=done with zero code on main,
  tip-drift refusals, a DirtyMain deadlock, a quarantine deadlock needing five
  land attempts, and multiple timeouts. Migrate it LAST, once the kernel is
  proven by the spec instance.

--------------------------------------------------------------------
10. RISKS, RECORDED SO THEY ARE NOT REDISCOVERED
--------------------------------------------------------------------
- CEREMONY. The V-model dies when artefacts exist and nobody reads them. The
  enforcement is what saves it and also what makes it expensive.
- BLOAT. `src/` is already 39.8% prose and docs are 44% ticket-narrative. A
  specification graph is another prose surface. Epic T-2994 should land first or
  this becomes the next bloat vector.
- BOOTSTRAPPING. frob has no requirements documents; retrofitting is archaeology.
  New projects should get this from `frob sys init`; frob adopts per-subsystem.
