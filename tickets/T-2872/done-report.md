## Done report

Rebound all 12 COV003 findings on main (2026-08-22 unbudgeted `frob
check --json` measurement: 12 -> 0) to a single root cause: every
finding cited the identical dead node id
`tests/test_arch_gate.py::TestArchGateLargeFile::test_large_file_fires_large001_warn`.
`git log -S` on that id showed exactly one hit: T-2831 renamed it to
`test_large_file_fires_large001_error` as part of its documented,
intentional WARN->ERROR severity promotion -- same class, same file,
same assertion shape (LARGE001 fires on an oversized production
file). None of the 12 citing tickets' original claims were specific
to WARN severity; each cited this test as general "the LARGE001 gate
exists and fires" evidence, so the renamed successor genuinely proves
the same property for all 12. This was a single disposition (RENAME)
applied 12 times via `frob ticket evidence <id> --replace OLD NEW
--reason ...`, using `--archived` for the two tickets (T-1102,
T-1651) that live under tickets/archive/ -- never hand-edited an
archived ticket.md directly, per the documented DuplicateId
corruption hazard. Scope was widened +2 globs after discovering the
archive path, recorded via `frob ticket scope --add --reason`. No
coverage gap found -- this was not a case of a deleted test with no
successor. Filed no new tickets: root cause was one already-landed
intentional rename, not a live defect needing follow-up. Re-measured
`frob check --json` unbudgeted (gate-summary present) before/after:
COV003 12 -> 0 repo-wide; `frob check --json --ticket T-2872` shows
zero COV003/PRE001/SCOPE001, with its remaining 38 errors identical
in rule/count to the unbudgeted full-repo run (all pre-existing,
out of this ticket's scope).

frob:no-behavior-change reason="Pure ticket-ledger evidence-citation correction across 12 tickets (rebinding a dead test node id to its actual T-2831 rename) -- no production code path changed, so there is no behavior difference for a designated repro test to exercise between the parent commit and this fix. The renamed successor test already exists and passes unchanged at both commits."

### Changed
```
 tickets/T-1656/ticket.md         | 11 ++++++++++-
 tickets/T-2375/ticket.md         | 15 ++++++++++++---
 tickets/T-2822/ticket.md         | 13 +++++++++++--
 tickets/T-2823/ticket.md         | 13 +++++++++++--
 tickets/T-2824/ticket.md         | 13 +++++++++++--
 tickets/T-2825/ticket.md         | 13 +++++++++++--
 tickets/T-2826/ticket.md         | 13 +++++++++++--
 tickets/T-2829/ticket.md         | 13 +++++++++++--
 tickets/T-2830/ticket.md         | 13 +++++++++++--
 tickets/T-2839/ticket.md         | 11 ++++++++++-
 tickets/T-2872/ticket.md         | 15 +++++++++++++++
 tickets/archive/T-1102/ticket.md | 22 ++++++++++++++++++++--
 tickets/archive/T-1651/ticket.md | 20 +++++++++++++++++++-
 13 files changed, 163 insertions(+), 22 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 15 error(s), 466 warning(s), 799 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@design/frob.strata, CYCLE001@src/frob/__init__.py, DOC006@docs/guides/claude-hooks.md, DOC011@docs/investigations/T-2796-backlog-reproduction.md, DOCENUM001@docs/modules/gates.md, DRIFT002@docs/modules/tickets-landing.md, DSL001@docs/modules/tickets-landing.md, OPAQUE001@src/frob/gates/_refs.py, PERF004@src/frob/strata/_selfconform_binding_rules.py, PERF004@src/frob/strata/_selfconform_surface_rules.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md
