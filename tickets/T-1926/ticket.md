---
id: T-1926
title: 'decide: drop ''frob sys check'' from roadmap.md''s CLI surface (duplicates
  ''frob sys audit'')'
state: done
kind: docs
origin: human
created: '2026-08-09'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- docs/strata/roadmap.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tickets/T-1926/**
  reason: explicit self-scope so SCOPE001's cross-ticket exemption (frob.gates._commit_exempts_file)
    recognizes this ticket's own shard commit and does not flag it against the filing
    ticket T-1480
  actor: logan
  at: '2026-08-09'
- op: remove
  glob: tickets/T-1926/**
  reason: this self-scope grant never actually fixed SCOPE001 (frob.gates.__init__._TICKET_REF_RE
    only matches T-#### 4-digit ids in commit subjects, never a T-draft-<hex> id,
    so the cross-ticket exemption could never engage regardless) and land-parity already
    reports 0 unscoped errors without it; removing to reduce surface for the T-1918
    sibling-draft-finalize lease-collision land bug
  actor: logan
  at: '2026-08-09'
evidence:
- cmd:grep -c "sys check" docs/strata/roadmap.md exit=0 sha256=4355a46b19d3
- cmd:grep -n "sys check" docs/strata/roadmap.md exit=0 sha256=b34e291c71ce
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
docs/strata/roadmap.md's "CLI surface (target)" names `frob sys check`
("parse + elaborate + prove + report") as a phase-5 verb. T-1480
investigated and found this premise already satisfied by the existing
`frob sys audit` (`sys_runner.py::_run_audit`): it parses, elaborates,
runs the full exhaustiveness/self-conformance/resource-contention/mode-
conformance/reliability conjunction, and reports pass/fail with named
gaps.

Adding a second, narrower `check` verb duplicating this would cut
against the standing "prefer deleting a verb over adding one" directive
this repo already applies elsewhere (e.g. the T-1870 sync-interface
removal), not serve it. Recommendation: drop `check` from
docs/strata/roadmap.md's phase-5 CLI-surface list rather than build a
duplicate of `audit` -- a docs-only decision, not a code change, so it
needs whoever owns docs/strata/roadmap.md to make the call. Filed as a
residue of T-1480.

## Done report

Changed: docs/strata/roadmap.md (CLI surface list, phase-5 section)

Decision: drop `frob sys check` from the roadmap's CLI-surface target
list. It duplicates the already-shipped `frob sys audit`
(`sys_runner.py::_run_audit`), which already parses, elaborates, and
runs the full exhaustiveness/self-conformance/resource-contention/
mode-conformance/reliability conjunction with named-gap reporting --
exactly the "parse + elaborate + prove + report" role `check` would
have filled. Building a second, narrower verb for the same role cuts
against this repo's standing "prefer deleting a verb over adding one"
directive (see the T-1870 sync-interface removal). Recorded the
reasoning inline in roadmap.md so the decision is not silently lost.

Evidence: docs-only change, no code path affected; no pytest evidence
applicable. Verified via `frob check --ticket T-1926` -- scope/prework/
diff-driven checks (gate:SCOPE, gate:PREWORK, gate:COV diff-driven,
gate:FMT, gate:AFFECT) all pass. Repo-wide FAILs present in the same
run (ruff-check, ruff-format, gate:DSL, gate:SELFAUDIT, gate:TEST) are
unscoped baseline findings unrelated to docs/strata/roadmap.md -- none
touch this ticket's file.

Filed: none
Gates: frob check --ticket T-1926 clean on all ticket-scoped checks
(gate:SCOPE/PREWORK/COV-diff/FMT/AFFECT); other gate families are
repo-wide baseline, not attributable to this change.

### Changed
```
 tickets/T-1926/ticket.md | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: DSL001@CHANGELOG.md, F401@/home/logan/projects/frob/.claude/worktrees/strata-cli-surface/tests/unit/test_tickets_evidence_only_scope.py, SELFAUDIT001@design, TEST001@src/frob/app/ticket_runner/_new.py
