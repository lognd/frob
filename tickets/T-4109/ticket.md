---
id: T-4109
title: 'consumer round-3 backend audit: ten defects frob or strata should have caught,
  each with a proposed rule (F-307)'
state: queued
kind: bug
origin: auditor
created: '2026-09-06'
priority: critical
parent: null
tier: epic
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: true
no_scope_declared_reason: 'tier=epic: a decomposition container. Its ten leaves span
  the declaration/glob subject-count surface, the docstring-claim lint, and five new
  rule families across gates and strata; scope belongs on the leaves, where it can
  be disjoint enough to dispatch in parallel'
designated_repro_test: null
acceptance:
- text: given the ten findings in F-307, when this epic is decomposed, then each has
    its own leaf ticket with a must-fire fixture built from the consumer's code shape
    rather than frob's
  evidence: []
- text: given a declaration glob that matches zero files on the current branch, when
    the gate runs, then that is its own finding distinct from an unobserved capability
    and is not suppressed by a capability waiver
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
A CONSUMER'S SECURITY AUDITOR ENUMERATED TEN THINGS FROB OR STRATA SHOULD HAVE
CAUGHT AND DID NOT, each with a proposed rule. Reported as logand.app-v2 F-307
(backend round-3 audit, 2026-09-06). This is the most valuable single report the
queue has received: it is not a list of frob bugs, it is a list of DEFECTS FROB
LET THROUGH, written by someone who found them by hand and then worked out which
gate should have found them first. That is the exact inverse of our usual input.

READ THE VERBATIM SECTION BELOW BEFORE DECOMPOSING. My classification follows it
and is secondary to their words.

WHY EVERY ITEM HERE IS DOGFOODING-INVISIBLE, which is the structural reason we
did not find these ourselves: all ten concern a web backend -- routes, response
models, rate limits, outbound flows to foreign hosts, deployment filesystems.
frob has none of those. For features frob does not itself use, our green is
evidence of nothing (the dogfooding-blindness class, now five instances). A
consumer running a real backend audit is the only instrument that reaches them.

MY CLASSIFICATION, for decomposition -- three groups that want different fixes:

  GROUP A, THE SILENT-ZERO GROUP. H3-10 is the sharpest finding in the report
  and should be worked first. A declaration whose glob matches ZERO files on the
  current branch is accepted silently, and the only signal is "capability
  unobserved" -- which waivers then suppress. Their sentence is exact: it is the
  difference between "the code is here and does not use the capability" and "the
  code is not here at all", and today both collapse into one waivable signal. We
  ALREADY BUILT THE PRIMITIVE FOR THIS: T-3985 landed subject-count reporting,
  where zero subjects on an enforcing gate is its own finding rather than a pass.
  This is that primitive applied to declaration globs. Do not design a new
  mechanism; extend the one that exists.

  GROUP B, CLAIM WITHOUT EVIDENCE. H3-4 and H3-9 are one defect seen twice: a
  docstring asserting never/always/idempotent with no invariant bound to it.
  Their framing is better than ours -- a cheap lint that flags the CLAIM is not
  the same as full invariant coverage, and it catches the case where the claim is
  false. They note the phrase appears three times in one file, bound to nothing.
  H3-9 adds that our doc-drift checking compares doc FILES against acked refs and
  never a module docstring against its own module's code.

  GROUP C, THE MISSING-RULE GROUP -- five proposed rules for properties no gate
  models today. H3-1 wants a call-graph closure check (a guard that READS a
  lockout with no reachable writer), and they point out we already have the
  resolver, since it is what our wiring gate uses. H3-2 wants a rate bound on
  writes, not only the time bound retention gives. H3-3 wants an outbound
  destination constrained to the declared node, plus a lint for an outbound flow
  to a foreign node with no rate clause. H3-5 wants a relative-path default on a
  config path field flagged. H3-7 wants a route-inventory check: every route
  returning a dict literal has a response model.

  H3-6 SITS APART and is a process rule, not a code rule: a failure-injection
  test must assert on every field of the response, not just the one the test-plan
  row happened to name. Note what happened there -- the test-plan row was written
  loosely, the fix satisfied it LITERALLY, and the roll-up field stayed constant.
  That is the wrong-incentive class expressed in a test plan.

DECOMPOSITION GUIDANCE
- Each of the ten becomes its own leaf. They share a report, not a mechanism.
- Group A first: it is the sharpest, it has an existing primitive to extend, and
  a declaration that silently matches nothing undermines every rule built on
  declarations -- including the five Group C proposes.
- Group C's five are new rules against a surface frob does not exercise. Each
  needs a real fixture built from the consumer's shape, not from ours; a rule we
  cannot fire in our own tree is a rule we have not tested. Say so per leaf.
- Do NOT collapse H3-4 and H3-9 into one leaf without checking: they may share a
  lint but they differ in what is compared (symbol docstring vs module docstring
  against module code).
- The perf-findings doctrine applies to the whole report: each root cause ships
  as a detector, not as a one-off fix in the consumer's repo.

VERBATIM REPORT FOLLOWS.


- H3-1 (guard records nothing). SYS101/WIRE gates check that a capability
  is *declared and observed*, never that a control is *effective*. The
  frob:tests binding on claim_preview_route points at
  test_claim_preview_rate_limited, which trips the bucket by calling
  record_failure directly, so the test proves the guard *reads* a lockout
  and says nothing about who writes one. Rule that would catch it: a
  frob:invariant on _rate_limit_guard of the form "every route class
  whose guard reads retry_after_seconds(class, ...) has at least one
  in-tree caller of record_failure for that same class *reachable from a
  route in that class*" -- a call-graph closure check, which frob already has
  the resolver for (it is what WIRE001 uses).
- H3-2 (unbounded event writes). Nothing in the gate set models write
  amplification. Strata knows auth_events carries
  behavioral.client_ip and has an attr "retention=7y"/SPEC-036 90-day
  bound, but retention is a *time* bound with no *rate* bound. Rule: require
  any carries-bearing store written from an unauthenticated route to have a
  declared rate on the inbound flow, the way outbound flows already must
  (REL201-style, applied to writes).
- H3-3 (SSRF surface). SYS100/SYS101 are file-granular: api/health.py
  was granted net.connect, and it does connect, so the gate is satisfied.
  The flow graph says backend -> media_host and nothing checks that the
  *destination* in code is constrained to that node. Rule: for a flow X -> Y
  where Y : foreign, require the granting file to contain a host constraint
  bound to a config field (an allowlist token frob can see), or a
  waive "SYS11x:destination-unconstrained". Also: f_backend_media has no
  rate clause while every sibling outbound flow does -- a lint for "outbound
  flow to a foreign node without rate" would have flagged it at line 339.
- H3-4 (docstring "never raises" vs KeyError). This is precisely what
  frob:invariant + the prove loop exist for, and no invariant was
  attached: the phrase "never raises" appears three times in health.py and is
  bound to no property test. Rule: flag docstrings asserting
  never/always/idempotent on a symbol with no frob:invariant (a
  claim-without-evidence lint), which is a cheaper version of INV coverage.
- H3-5 (relative default path). No gate compares an AppConfig default
  filesystem path against the deployment's filesystem, because there is no
  deployment manifest on main to compare against. Rule: flag a
  Field(default=...) on a *_path field whose value is a relative path --
  config paths should be absolute or None.
- H3-6 (constant status: "ok"). UT-0208's test-plan row was written as
  "reports db and redis", and the M-9 fix satisfied it literally. The
  test-plan rule the prior audit already named (audit-2026-09-05-backend.md:570
  -- "a health/probe component's test must inject a *failing* dependency")
  was applied to the db field but not to the roll-up. Rule: extend that
  process check to require the failure-injection test to assert on *every*
  field of the response, or at least on the field named status.
- H3-7 (4 routes missed). COV/WIRE gates see StatusResponse as
  referenced (three routes use it) so no gate notices the four that do not.
  Rule: a route-inventory check in the same family as SIT-011's guard
  inventory -- "every route returning a dict literal has a
  response_model" -- would have made the gap machine-visible; today it is
  only visible by reading the docstring against the decorators.
- H3-9 (docstring vs router-level dependency). Same class as H3-4:
  claim-in-prose, no binding. DRIFT001 checks doc *files* against acked refs,
  not module docstrings against their own module's code.
- H3-10 (declarations for absent files). This is the sharpest gap: a
  may "cap" via "path/glob" entry whose glob matches zero files on the
  current branch is accepted silently, and SELFAUDIT001 fires only about the
  *capability* being unobserved (which the T-0002 waivers then suppress).
  Rule: SYS1xx: via-glob matches no file on this branch as its own finding,
  distinct from "capability unobserved" -- it is the difference between "the
  code is here and does not use the capability" and "the code is not here at
  all", and today both collapse into the same waivable signal.

