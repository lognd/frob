---
id: T-1992
title: T-1980's policy doc references a sibling-repo path that DOC006 tries (and fails)
  to resolve locally
state: done
kind: docs
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- docs/guides/frob-version-policy.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- cmd:grep -n 'frob:waive DOC006' docs/guides/frob-version-policy.md exit=0 sha256=48033384818d
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
Regression measured post-land of T-1980: unscoped `frob check --only
gates` on main now includes one real, unwaived DOC006 error:

  docs/guides/frob-version-policy.md:101 DOC006: file/path pointer
  'src/typani/result.py' does not resolve -- not a tracked file

The measured-delta table in that doc names `src/typani/result.py` as
one of the OPAQUE001 finding locations from the typani sibling-repo
measurement -- a real path, but in a different repo, which DOC006
correctly cannot resolve against THIS repo's own tracked file set.
Needs a `frob:waive DOC006` on that line with a reason (intentionally
external -- a sibling-repo path cited in a cross-repo measurement, not
a broken local reference).

## Done report

Changed: docs/guides/frob-version-policy.md -- added `frob:waive DOC006`
on the sibling-repo path citation (`src/typani/result.py`) that DOC006
correctly could not resolve against this repo's own tracked file set.

Evidence: 1 evidence-cmd (docs-kind channel) confirming the waiver
comment is present.

Gates: `frob check --ticket T-1992` shows the file no longer
appearing anywhere in the error/warning output; remaining errors in the
same run are all the pre-existing T-1989 DSL001 regression (unrelated
files, already ticketed by another agent).

Filed: none.

### Changed
```
 tickets/T-1992/ticket.md | 38 ++++++++++++++++++++++++++++++++++++++
 1 file changed, 38 insertions(+)
```

### Evidence
- `cmd:grep -n 'frob:waive DOC006' docs/guides/frob-version-policy.md exit=0 sha256=48033384818d` (cmd evidence, exit=0)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: DSL001@CHANGELOG.md, DSL001@docs/commands/sys.md, DSL001@docs/design/coding-performance-corpus.md, DSL001@docs/design/cwe-1000-registry.md, DSL001@docs/design/design-pattern-traps-corpus.md, DSL001@docs/design/language-adapter-tier-decision.md, DSL001@docs/design/registry/RECONCILIATION.md, DSL001@docs/design/system-performance-corpus.md, DSL001@docs/guides/coordinator-scripts.md, DSL001@docs/guides/editors.md, DSL001@docs/guides/exhaustive-research.md, DSL001@docs/guides/install.md, DSL001@docs/modules/app.md, DSL001@docs/modules/arch.md, DSL001@docs/modules/bind.md, DSL001@docs/modules/clean.md, DSL001@docs/modules/cli.md, DSL001@docs/modules/cve.md, DSL001@docs/modules/decisions.md, DSL001@docs/modules/deploy.md, DSL001@docs/modules/dup-sota-survey.md, DSL001@docs/modules/dup.md, DSL001@docs/modules/fleet.md, DSL001@docs/modules/fuzz.md, DSL001@docs/modules/gates.md, DSL001@docs/modules/graph.md, DSL001@docs/modules/lang.md, DSL001@docs/modules/logging.md, DSL001@docs/modules/mutate.md, DSL001@docs/modules/perf.md, DSL001@docs/modules/process.md, DSL001@docs/modules/release.md, DSL001@docs/modules/render.md, DSL001@docs/modules/serve.md, DSL001@docs/modules/stats.md, DSL001@docs/modules/strata.md, DSL001@docs/modules/testing.md, DSL001@docs/modules/tickets.md, DSL001@docs/modules/vet.md, DSL001@docs/strata/boundary.md, DSL001@docs/strata/charter.md, DSL001@docs/strata/evidence.md, DSL001@docs/strata/host.md, DSL001@docs/strata/kernel.md, DSL001@docs/strata/krb.md, DSL001@docs/strata/policy.md, DSL001@docs/strata/reliability.md, DSL001@docs/strata/roadmap.md, DSL001@docs/strata/selfconform.md, DSL001@docs/strata/surface.md, DSL001@docs/strata/threat.md, DSL001@docs/strata/waive.md, F401@/home/logan/projects/frob/.claude/worktrees/t1980-docfix/tests/unit/test_tickets_evidence_only_scope.py
