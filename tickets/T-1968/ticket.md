---
id: T-1968
title: 'frob:waive in markdown is silently ignored: waivers written by a burn-down
  suppress nothing and nothing says so'
state: done
kind: bug
origin: human
created: '2026-08-10'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/graph/dsl.py
- src/frob/graph/__init__.py
- design/frob.strata
- docs/modules/graph.md
- tests/test_graph.py
- tests/unit/gates/test_negexist.py
- tests/unit/graph/test_dsl_markdown_waive.py
- tests/unit/graph/test_dsl_mention_escape.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/gates/
  reason: 'Corrected scope after implementation: the markdown frob:waive fix lives

    in frob.graph.dsl/__init__, not frob.gates. Narrowing to the files the

    committed change actually touches (T-1968).

    '
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/graph/dsl.py
  reason: 'Corrected scope after implementation: the markdown frob:waive fix lives

    in frob.graph.dsl/__init__, not frob.gates. Narrowing to the files the

    committed change actually touches (T-1968).

    '
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/graph/__init__.py
  reason: 'Corrected scope after implementation: the markdown frob:waive fix lives

    in frob.graph.dsl/__init__, not frob.gates. Narrowing to the files the

    committed change actually touches (T-1968).

    '
  actor: logan
  at: '2026-08-10'
- op: add
  glob: design/frob.strata
  reason: 'Corrected scope after implementation: the markdown frob:waive fix lives

    in frob.graph.dsl/__init__, not frob.gates. Narrowing to the files the

    committed change actually touches (T-1968).

    '
  actor: logan
  at: '2026-08-10'
- op: add
  glob: docs/modules/graph.md
  reason: 'Corrected scope after implementation: the markdown frob:waive fix lives

    in frob.graph.dsl/__init__, not frob.gates. Narrowing to the files the

    committed change actually touches (T-1968).

    '
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/test_graph.py
  reason: 'Corrected scope after implementation: the markdown frob:waive fix lives

    in frob.graph.dsl/__init__, not frob.gates. Narrowing to the files the

    committed change actually touches (T-1968).

    '
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/unit/gates/test_negexist.py
  reason: 'Corrected scope after implementation: the markdown frob:waive fix lives

    in frob.graph.dsl/__init__, not frob.gates. Narrowing to the files the

    committed change actually touches (T-1968).

    '
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/unit/graph/test_dsl_markdown_waive.py
  reason: 'Corrected scope after implementation: the markdown frob:waive fix lives

    in frob.graph.dsl/__init__, not frob.gates. Narrowing to the files the

    committed change actually touches (T-1968).

    '
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/unit/graph/test_dsl_mention_escape.py
  reason: 'Corrected scope after implementation: the markdown frob:waive fix lives

    in frob.graph.dsl/__init__, not frob.gates. Narrowing to the files the

    committed change actually touches (T-1968).

    '
  actor: logan
  at: '2026-08-10'
evidence:
- tests/unit/graph/test_dsl_markdown_waive.py::TestUnhandledMarkdownWaiveDirective::test_waive_of_a_genuinely_unhonored_rule_is_reported_unparsed
- tests/unit/graph/test_dsl_markdown_waive.py::TestUnhandledMarkdownWaiveDirective::test_waive_of_each_honored_rule_produces_no_finding
- tests/unit/graph/test_dsl_markdown_waive.py::TestUnhandledMarkdownWaiveDirective::test_multiple_unhonored_waivers_each_reported
- tests/unit/graph/test_dsl_markdown_waive.py::TestUnhandledMarkdownWaiveDirective::test_recognized_verbs_produce_no_unhandled_finding
- tests/unit/graph/test_dsl_markdown_waive.py::TestUnhandledMarkdownWaiveDirective::test_unknown_verb_entirely_is_reported
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
`frob:waive` directives written inside markdown files are never parsed,
so they suppress nothing. They are accepted silently as ordinary prose --
no error, no warning, no "unknown directive" -- so an author has no way
to learn their waiver does nothing.

DISCOVERED as a side-disclosure inside T-1942's residue (T-1964, a docs
ticket scoped to one file). Filed separately because this is a
silent-no-op DIRECTIVE class, not a docs task.

MEASURED:
- Real, intended-to-be-live waivers exist in HTML-comment form:
    docs/modules/fuzz.md:28,36
      <!-- frob:waive DOC006 reason="illustrative downstream-project
      filename convention, not a path this repo ships" -->
    docs/modules/deploy.md:4,5
      <!-- frob:waive INV003 reason="T-1023 INV003/INV004 burn-down:
      ... incidental scope-cut/design-rationale prose ..." -->
      <!-- frob:waive INV004 reason="... same disposition ..." -->
  The deploy.md pair were written as part of an explicit T-1023
  burn-down -- deliberate work product, not a stray comment.
- No parser support exists. `git grep` finds `<!-- frob:... -->` handled
  for `ticket:` markers (frob.gates.__init__) and for
  `frob:generated-start/end` fences (frob.gates._docblocks), but nothing
  reads `frob:waive` out of markdown.
- Corroborating measurement: `frob check --only gates` reports
  `gate:DOC  0 errors, 558 warnings, 0 waived` -- ZERO waived, despite
  fuzz.md carrying DOC006 waivers that should register.

WHY IT MATTERS: either the findings these waivers name are still firing
(buried among 558 warnings, so a burn-down's output was silently
discarded), or they were never needed (so the burn-down was wasted
effort). Both readings mean someone did accounted-for work that had no
effect and no feedback said so. This is the catalogued-is-not-enforced
failure applied to the waiver DSL itself: the one construct whose entire
purpose is to be read by a gate is, here, read by nothing.

385 markdown files contain `frob:waive`-shaped text, but the large
majority are audit reports and CHANGELOG entries DESCRIBING waivers in
prose. Do not treat 385 as the defect count -- the real population is
waivers in HTML-comment form intended to suppress a finding on that file.
Establishing that exact set is part of the work.

DO NOT FIX IT THIS WAY:
- Do NOT mass-delete the markdown waivers to "clean up". Each one
  encodes a reviewed judgement (the deploy.md pair cite their burn-down
  ticket by id). Deleting them destroys the reasoning and, if the
  directives are later honored, silently un-waives real findings -- the
  shape of the incident where a "safe" cleanup deleted 55 live waivers.
- Do NOT simply start honoring them repo-wide in one step. If they have
  been dead since they were written, some may waive findings that no
  longer exist or were never real; switching them on blind changes gate
  results in unreviewed ways.

FIX DIRECTION, preferred order:
(a) REFUSE AT THE MOMENT: make an unparseable/ignored `frob:` directive
    in any file type a loud error, so writing a dead waiver is
    impossible rather than merely useless. This is the general fix --
    it covers every future directive/file-type combination, not just
    this one.
(b) Then decide, per the enumerated real set, whether markdown waivers
    should be honored or whether the directive belongs elsewhere.

ACCEPTANCE: first test must FAIL before the fix -- place a
`<!-- frob:waive DOC006 reason="..." -->` in a markdown file and assert
the tool reports it as unparsed/ignored rather than accepting it
silently. Then enumerate and report the real population of
intended-live markdown waivers (file:line, rule, reason), separated from
prose mentions, with a per-entry disposition.

## Done report

CORRECTION TO THE TICKET BODY: the ticket as filed claimed markdown
frob:waive is silently ignored, citing "gate:DOC 0 waived" as proof.
That claim was wrong. DOC006, DOC004, INV003, INV004 (plus REF001/
REF002/BUG002) already had dedicated per-rule markdown-waiver mechanisms
before this ticket, so the two examples the ticket cited
(docs/modules/fuzz.md's DOC006 waiver, docs/modules/deploy.md's INV003/
INV004 waivers) were working all along. The "0 waived" count undercounts
because those mechanisms suppress the violation before it is ever
emitted, so no graph-edge WaiverRef is ever produced to count -- not
because the waivers do nothing.

The real, narrower gap this ticket fixes: _MD_WAIVE_HONORED_RULES did
not reflect the actual honored-rule set, so a frob:waive naming any
OTHER rule (or any verb outside the markdown-handled set) was accepted
silently as ordinary prose with no error, no warning, and no
"unknown directive" -- an author had no way to learn a mis-scoped
waiver did nothing. The fix corrects _MD_WAIVE_HONORED_RULES to the
real honored set and makes an unhandled markdown frob:waive produce a
MalformedDirective, markdown's half of DSL001's existing catch-all
contract for code comments.

Confirmed repo-wide before landing: frob check --only gates against the
current tree produced ZERO new findings, because every existing markdown
frob:waive in this repo already falls in the honored set -- this fix
changes nothing about any waiver already in the tree, only what happens
the next time someone writes one naming an unhandled rule.

### Changed
```
 design/frob.strata                          |   2 +-
 docs/modules/graph.md                       |  33 ++++++-
 src/frob/graph/__init__.py                  |   8 +-
 src/frob/graph/dsl.py                       | 132 +++++++++++++++++++++++++++-
 tests/test_graph.py                         |   6 +-
 tests/unit/gates/test_negexist.py           |  12 +--
 tests/unit/graph/test_dsl_markdown_waive.py |  92 +++++++++++++++++++
 tests/unit/graph/test_dsl_mention_escape.py |   6 +-
 tickets/T-1968/ticket.md                    | 111 ++++++++++++++++++++++-
 9 files changed, 381 insertions(+), 21 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: DSL001@CHANGELOG.md, DSL001@docs/commands/sys.md, DSL001@docs/design/coding-performance-corpus.md, DSL001@docs/design/cwe-1000-registry.md, DSL001@docs/design/design-pattern-traps-corpus.md, DSL001@docs/design/language-adapter-tier-decision.md, DSL001@docs/design/registry/RECONCILIATION.md, DSL001@docs/design/system-performance-corpus.md, DSL001@docs/guides/coordinator-scripts.md, DSL001@docs/guides/editors.md, DSL001@docs/guides/exhaustive-research.md, DSL001@docs/guides/install.md, DSL001@docs/modules/app.md, DSL001@docs/modules/arch.md, DSL001@docs/modules/bind.md, DSL001@docs/modules/clean.md, DSL001@docs/modules/cli.md, DSL001@docs/modules/cve.md, DSL001@docs/modules/decisions.md, DSL001@docs/modules/deploy.md, DSL001@docs/modules/dup-sota-survey.md, DSL001@docs/modules/dup.md, DSL001@docs/modules/fleet.md, DSL001@docs/modules/fuzz.md, DSL001@docs/modules/gates.md, DSL001@docs/modules/graph.md, DSL001@docs/modules/lang.md, DSL001@docs/modules/logging.md, DSL001@docs/modules/mutate.md, DSL001@docs/modules/perf.md, DSL001@docs/modules/process.md, DSL001@docs/modules/release.md, DSL001@docs/modules/render.md, DSL001@docs/modules/serve.md, DSL001@docs/modules/stats.md, DSL001@docs/modules/strata.md, DSL001@docs/modules/testing.md, DSL001@docs/modules/tickets.md, DSL001@docs/modules/vet.md, DSL001@docs/strata/boundary.md, DSL001@docs/strata/charter.md, DSL001@docs/strata/evidence.md, DSL001@docs/strata/host.md, DSL001@docs/strata/kernel.md, DSL001@docs/strata/krb.md, DSL001@docs/strata/policy.md, DSL001@docs/strata/reliability.md, DSL001@docs/strata/roadmap.md, DSL001@docs/strata/selfconform.md, DSL001@docs/strata/surface.md, DSL001@docs/strata/threat.md, DSL001@docs/strata/waive.md, F401@/home/logan/projects/frob/.claude/worktrees/t1968-only/tests/unit/test_tickets_evidence_only_scope.py
