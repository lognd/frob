## Done report

Enumerated all four named candidates and their inbound references before
touching anything, per the ticket's own method:

1. FROBLEMS.md (repo root, tracked): frob's own `frob.clean` module
   (src/frob/clean/__init__.py, _rules.py) already treats FROBLEMS.md as
   a generated, .gitignore'd artifact removed by `frob clean --deep` in
   every normal checkout -- this repo's own root copy was force-added
   against that convention (per its own header) and had gone stale (last
   substantive entry 2026-07-21, superseded by the ticket queue since).
   No source, test, or doc requires this specific file to exist:
   tests/test_clean.py exercises the removal mechanism against synthetic
   temp fixtures, and every other inbound reference
   (docs/modules/clean.md, docs/audits/docs-staleness-2026-07-29.md,
   src/frob/gates/__init__.py, tests/unit/strata/test_selfconform.py,
   test_code_binding.py) is a generic description of the mechanism or a
   historical citation in a comment, not a dependency on the tracked
   file. DEAD -- removed.

2. agents/** (7 dirs: debugger, implementer, interface-auditor, planner,
   prover, reviewer, security-auditor) and skills/** (6 dirs: audit,
   document, fix, next, plan, prove): found to be LIVE, not vestigial.
   docs/rework.md's "Agents and skills redesign" section documents this
   exact 7-agent/6-skill roster as the deliberate, already-completed
   redesign (reworked/new/kept per-role, with a stated list of DELETED
   agents/skills that are correctly already gone: architect, oracle,
   orchestrator, refactorer, smart-start, tester, integration-tester,
   system-tester, develop, implement, write-tests, review).
   docs/guides/agentic-workflow.md documents 5 of the 6 skills and all 7
   agents as the operative dispatch roles a coordinator uses (matches
   this very session's own live Skill/agent tooling). src/frob/
   _cli_parsers/_ticket/_query.py carries a frob:doc anchor directly onto
   agentic-workflow.md's #skills/next and #skills/plan sections. Every
   file present matches the rework table exactly -- no stray/orphaned
   file beyond what's documented. CLAUDE.md's opening line ("remove
   agents/ and skills/ or at least REALLY rework them") predates this
   already-completed rework; treating it as still-open would delete
   load-bearing, actively-referenced tooling. Per this ticket's own rule
   ("anything central to frob tooling stays, however scruffy") and the
   direct instruction to keep anything central and file a ticket rather
   than delete when in doubt: KEPT in full, no deletion.

Filed: T-1610 and T-1611 (already queued, next in this series) cover the
follow-up doc-completeness/detector-gap work this finding surfaces --
specifically that skills/document and skills/fix are undocumented in
agentic-workflow.md's own role table, a gap for T-1610 to record.

Gates: `frob check --ticket T-1612` clean after `frob ticket sweep
T-1612` refresh (0 errors, 1 note-only warning). Deletion-filter check
(`git diff main --diff-filter=D --stat`) shows exactly one deleted path,
FROBLEMS.md, matching this ticket's explicit scope.

### Changed
```
 FROBLEMS.md | 26 --------------------------
 tickets.md  |  5 +++--
 2 files changed, 3 insertions(+), 28 deletions(-)
```

### Evidence
- `tests/test_clean.py::test_clean_deep_removes_frob_state` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 0 error(s), 2777 warning(s), 711 waived
- error-findings: none (measured, zero errors)
