---
id: T-4157
title: 'consumer round-4 engine audit: findings frob or strata should have caught,
  including a waiver whose stated premise expired unnoticed'
state: queued
kind: bug
origin: auditor
created: '2026-09-07'
priority: critical
parent: null
tier: epic
sprint: v0.543.0
runs_last: false
milestone: v0.543.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given the findings in this epic, when it is decomposed, then each has its
    own leaf ticket or recorded evidence on an existing open ticket, with the choice
    stated per finding
  evidence: []
- text: given a waiver whose stated reason is contingent on tree state, when the tree
    changes so the reason no longer holds, then the waiver stops suppressing its finding
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
A CONSUMER'S FOURTH ROUND AUDIT, verbatim, on their rendering engine. Same shape
as the round-3 backend audit filed as T-4109, which produced nine leaves: findings
the auditor made by hand, each paired with the frob or strata rule that should
have caught it first.

DECOMPOSE IT THE SAME WAY -- one leaf per finding, real scope per leaf, and an
explicit note per leaf saying whether the rule can be fixture-tested in frob's own
tree at all. Read every item's own text before trusting my summary below.

THE ONE I WANT LOOKED AT FIRST, because it is not about their engine at all and it
indicts a mechanism this whole system rests on:

  H4-1 records a `frob:waive` whose stated reason was "the file is absent on this
  branch". That reason STOPPED BEING TRUE the moment a merge brought the file in,
  and NOTHING RE-EVALUATED THE WAIVER against the merged tree. The waiver kept
  suppressing a real finding on a premise that had expired.

That is the intent-in-prose class at its most consequential. This repo has already
recorded four instances in one session of an intention stated in prose being
treated as if it were enforced -- a waiver reason, a doc paragraph, an expired
lease premise, and a runs-last declaration. Here the prose is a waiver's
justification, and the cost is a suppressed finding on live code.

Their proposed rule is the right shape and worth quoting: a waiver whose reason
names a BRANCH CONDITION must carry that condition as a CHECKABLE PREDICATE and
fail once it no longer holds. Note what that implies -- not every waiver needs a
predicate, only those whose justification is contingent on tree state. Working out
which reasons are contingent is the interesting part of the leaf, and it should be
answered by reading real waiver reasons in this repo rather than theorising: we
carry hundreds, and they are the honest sample.

THE SECOND THEME, spanning H4-2 and H4-3: both defects live in the INTERACTION
between two components' state, and their point is that per-symbol test binding
structurally cannot see a cross-component interaction. That is a real limit of the
obligation graph rather than a bug in it, so the leaf should establish what the
honest scope of a fix is before proposing one -- a rule that claims to verify
cross-component behaviour and cannot would be worse than the current silence.

DOGFOODING NOTE, same as the round-3 epic: this is a rendering engine with
components, bundles and touch input. frob has none of those. For every leaf, our
own green is evidence of nothing, and a fixture built from our tree will not
exercise the rule. Say so per leaf rather than discovering it during
implementation.

CHECK THE EXISTING QUEUE BEFORE FILING EACH LEAF. The waive-expiry idea in
particular may overlap work already open on waiver auditing; attaching evidence to
an open ticket is worth more than a duplicate.

VERBATIM REPORT FOLLOWS.

## F-357 -- engine round-4 audit: what frob/strata should learn (verbatim from docs/security/audit-2026-09-07-engine-round4.md; tickets T-0363..T-0367)


- H4-1 (dynamic import by source path). design/logand-app.strata
  models capability ceilings per node but has no concept of "a module
  specifier that must resolve in the PRODUCTION bundle". frob check
  saw only an OPAQUE001 finding and accepted a frob:waive whose
  stated reason ("the file is absent on this branch") stopped being true
  the moment the demo merge existed -- nothing re-evaluates a waive
  against a merged tree. Two rules would have caught it: (1) a gate that
  fails when a @vite-ignore dynamic import's specifier resolves to a
  path under src/ that is not reachable from the built output --
  cheaply approximated as "no built artifact may contain the literal
  /src/"; (2) a waive-expiry rule -- a frob:waive whose reason names a
  branch condition must carry the condition as a checkable predicate and
  fail once it no longer holds.
- H4-2 / H4-3 (tooltip overlap, inert touch buttons). Both are
  interactions BETWEEN two components' render/state gates
  (userHasControl vs showTouchControls; stopPropagation vs
  onEngage). frob's per-symbol test binding cannot see a cross-component
  invariant, and every unit test passes. A frob:invariant on DoomLite of
  the form "at most one bottom-centre panel is visible" and "any input
  path that writes inputRef first disengages attract mode", bound to a
  test that renders the component in the coarse-pointer configuration,
  would have. The general rule: any component with two mutually exclusive
  UI modes should be required to declare the exclusivity as an invariant,
  not as a JSX comment ("the two never show at once",
  DoomLite.tsx:685).
- H4-4 (keyboard capture). No gate models "this component installs a
  window-level keydown listener", which is a page-wide capability, not a
  component-local one. strata could carry a may: dom.global_key_capture
  capability on SUB-17 nodes, with the ceiling requiring a declared
  focus-scoping predicate; a node that captures global keys without one
  fails SYS100.
- H4-5 (fallback parity). Renderer's optional methods
  (renderer.ts:214,235,254) make an incomplete implementation
  type-legal, so nothing at build or check time notices that
  fallback/index.ts satisfies only 6 of 9. A frob rule binding an
  interface to its implementations ("every optional member of a
  frob:invariant-marked port must be implemented by every declared
  adapter, or the adapter must declare the omission") would have flagged
  it; failing that, a required parity test per Renderer method.
- H4-6 (settle gate). The docstring states the degrade behaviour
  ("one-time initial measurement") that the code does not deliver. This is
  exactly the class frob:invariant + a bound test exists for, but no
  invariant is declared on useResponsiveGrid -- invariants/ is empty
  on this branch (noted in useFrameLoop.ts's own comment). Rule: a
  hook whose docstring promises a degrade path for a missing browser API
  must have a test bound to that path; gate:TEST could require it whenever
  a typeof X === "undefined" branch exists.
- H4-7 (localStorage). SPEC-023 says "no storage" and the code stores;
  strata declares capability ceilings per node, so a
  may: browser.local_storage capability on the SUB-17 engine node would
  have made SYS100 fail on motionPreference.ts and forced the decision
  record. That is the single highest-value rule to add here: browser
  storage is a privacy surface and should be a declared capability, not
  an unremarkable import.
- H4-8 (attract mutates real state). A purity/ownership rule --
  "a controller documented as Pure: reads world, never mutates it"
  (doomAttract.ts:177-179) must not be wired to a caller that applies
  its outputs to the same buffers it read" -- is beyond current gates;
  the practical rule is a frob:invariant on DoomLite that enemy state at
  first-engage equals DEFAULT_ENEMIES, bound to a test.

