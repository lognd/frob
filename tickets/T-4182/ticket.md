---
id: T-4182
title: 'consumer round-5 shell audit: findings written as why the gates, the design
  language and the sibling tool each missed them'
state: queued
kind: bug
origin: auditor
created: '2026-09-07'
priority: critical
parent: null
tier: epic
sprint: v0.539.0
runs_last: false
milestone: 0.539.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: true
no_scope_declared_reason: 'tier=epic: a decomposition container; scope belongs on
  the leaves'
designated_repro_test: null
acceptance:
- text: given the findings in this epic, when it is decomposed, then each has its
    own leaf or recorded evidence on an existing open ticket, with the choice stated
    per finding
  evidence: []
- text: given the five other open audit epics, when a leaf is cut here, then it is
    checked against them for a duplicated mechanism first
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
A CONSUMER'S FIFTH-ROUND SHELL AUDIT, verbatim, written the same way as their
round-4 backend audit: each entry states why the gates missed the finding rather
than merely reporting it.

DECOMPOSE ONE LEAF PER FINDING, real scope per leaf, and an explicit note per leaf
saying whether the rule can be fixture-tested in frob's own tree at all.

BEFORE CUTTING ANY LEAF, READ THE OTHER OPEN AUDIT EPICS. There are now five of
them from this consumer covering backend round 3 and 4, engine round 4, shell
round 4, and a mixed backlog. At least two mechanisms are already known to be
duplicated across them -- a waiver whose premise expires unchecked appears in two
independent audits, and a call-reachability blind spot appears in three separate
findings. Attaching evidence to an existing leaf is worth more than a new
duplicate, and this queue has already had to consolidate five separate tickets
against one mechanism in a single day.

DOGFOODING NOTE, unchanged and still binding: this audit covers a web shell. frob
has no routes, no bundles, no browser surface. For most of these leaves our own
green is evidence of nothing and a fixture built from our tree will not exercise
the rule. Say so per leaf rather than discovering it during implementation.

VERBATIM REPORT FOLLOWS.

## F-386 (2026-09-07) shell round 5 audit: why the gates, apollo and the strata missed each finding (verbatim from docs/security/audit-2026-09-07-shell-round5.md)
Why the gates missed it: frob check has no model of "an npm script chain's failure modes as a function of host state". The one artifact that does encode this coupling -- cli-runner.test.ts:75-95's 20-line describe.skipIf comment -- resolves it by disabling itself, which is exactly the shape round 4's own "what frob should learn" section proposed a rule for (a skipIf naming a production command is an obligation, not a 

Why the gates missed it: three separate blind spots line up. (1) The CSP is a string in a Caddy snippet -- frob check has no gate that reads it, and frob sys audit reasons about *code* capabilities (design/logand-app.strata's may "fetch_url" grants), not about the edge policy that would permit or deny them at runtime; nothing connects the browser node's declared media loads to the header that governs them. 

Why the gates missed it: gate:TEST binds a test to a symbol via frob:tests, and routes.tsx:38 does carry frob:tests frontend/tests/unit/routes.test.tsx -- so the symbol *has* bound evidence and the gate is satisfied. What no gate checks is whether the bound test asserts the property the docstring claims. This is the "docstring claims a behaviour" class round 4 already proposed a gate:INV 

Why the gates missed it: the fix and the miss are in two different tickets' scopes (T-0370 owned static-assets.ts/licenses.ts/cli.ts; T-0374 owned media-manifest.ts), and frob has no notion of "these three call sites implement one contract, so a change to the contract obliges all three". The frob:doc edges all point at COMP-1608, which is the right anchor -- a DRIFT/COV rule keyed on "symbols sharing a frob:doc anchor 

Why the gates missed it: FROBLEMS F-039 again -- gates evaluate main, and this file lives on a branch that cannot land. But the specific miss is self-inflicted: the totality test's oracle (backend/openapi.json) is a committed artifact of the *same* branch being tested, so the test is a fixed point rather than a check. The rule: a totality test whose reference set is a committed snapshot needs a second, cheap assertion that the 

Why the gates missed it: AdminGuard predates redirectToLogin.ts and was never in the scope of the ticket (T-0347) that created the shared contract, so no AFFECT/COV edge connects them; from frob's view AdminGuard.tsx is a documented symbol with a frob:doc anchor and bound tests, all green. The claim that is false lives in a *different* file's module comment ("Both now go through this module"), and nothing binds a 

Why the gates missed it: as round 4 already noted, design/logand-app.strata grants the build node reach to api.github.com but carries no attribute saying the data behind that reach is third-party-owned and volatile, so no SYS rule can object to it grounding a build-failing equality check. T-0370 implemented the fix as a hand-picked field allowlist rather than as a volatility classification, which is why the field partition is a judgement 

Why the gates missed it: the invariant is a real one and is written in prose in a module comment, with no frob:invariant directive to bind it -- so gate:INV has nothing to discharge and gate:TEST sees three bound, passing tests (footerHeightPublisher.test.tsx:76,125,175), each of which exercises a *single* publisher lifecycle. The property that fails is a two-publisher interleaving, which no single-component unit test shape 


## F-387 (2026-09-07, T-0412) bug002 confirmatory-only refusal on a live-deployment-only prodtest assertion
