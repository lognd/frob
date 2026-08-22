## Done report

Changed:
- tickets/T-2375 (ledger only): scope narrowed from empty to
  src/frob/gates/_arch.py, tests/unit/test_arch_srp.py, tests/test_arch_gate.py
  (the deferred WARN->ERROR promotion's own future scope); both acceptance
  criteria amended to describe what this ticket actually delivers
  (measurement + characterization + decomposition), not a terminal zero-count
  or premature severity promotion.
- 9 child tickets filed with --parent T-2375 (drafts, renumber at land):
  T-2828, T-2827 (gates, 2 batches)
  T-2825, T-2822 (tickets, 2 batches)
  T-2830, T-2829 (app/ticket_runner, 2 batches)
  T-2826 (strata, excludes T-2729's _selfconform.py)
  T-2823 (vet/graph/arch)
  T-2824 (misc small packages + 4 Rust native files)
  Together these cover all 84 non-_selfconform.py LARGE001 warning findings
  (85 measured minus _selfconform.py, which is T-2729's own ticket, not
  absorbed here).

Evidence: no test evidence -- this ticket's own deliverable is measurement,
characterization, and ticket decomposition (ledger work), not a code change.
Per coordinator direction 2026-08-21: land as-is; the actual LARGE001
burn-down is delegated to the 9 children, and the deferred WARN->ERROR
promotion is tracked as its own successor ticket (filed immediately after
this one lands, blocked-by all 9 children's real ids).

Caller/characterization method: measured LARGE001 via
`frob check --json --budget 500` in a freshly-natives-built worktree = 85
warning-severity findings across 85 distinct production files (6 more
exist but are already severity=note via pre-existing frob:waive T-1651
directives -- left alone, not counted toward zero). This independently
matches docs/investigations/T-2796-backlog-reproduction.md's own separate
measurement of 85 -- two independent runs agreeing is treated as a solid
count, not the ticket's originally-filed 72. Characterized as MANY
independent causes (85 separately-grown oversized modules, no shared
resolver-style root cause), unlike REF001's likely-single-cause 257
findings -- confirmed by frob.toml's max_file_lines=800 threshold and the
existing T-1651 waivers, which already establish that a forced line-count
split with no real consumer-set seam is worse than the warning it
silences (e.g. _models.py's cohesive Ticket/Evidence model). Decomposed
into 9 disjoint batches by subsystem instead of grinding all 85 in one
ticket or filing 85 single-file tickets.

Filed: 9 child tickets (see Changed above, real ids TBD after this land's
renumbering) plus one successor ticket to be filed immediately after this
land for the deferred WARN->ERROR promotion, blocked-by all 9 children.

Gates: no code changed by this ticket; `frob check --ticket T-2375` scope
is ledger-only (tickets.md + 9 new ticket dirs), TICK013 (empty scope)
resolved by the scope declaration above. Per coordinator direction, the
ticket's own declared scope (src/frob/gates/_arch.py + its two test files)
is intentionally NOT touched by this land -- that work is the deferred
successor ticket, not silently absorbed here.

### Changed
```
 tickets/T-2375/ticket.md           | 79 ++++++++++++++++++++++++++++++++++++--
 tickets/T-2822/ticket.md | 40 +++++++++++++++++++
 tickets/T-2823/ticket.md | 48 +++++++++++++++++++++++
 tickets/T-2824/ticket.md | 52 +++++++++++++++++++++++++
 tickets/T-2825/ticket.md | 40 +++++++++++++++++++
 tickets/T-2826/ticket.md | 45 ++++++++++++++++++++++
 tickets/T-2827/ticket.md | 43 +++++++++++++++++++++
 tickets/T-2828/ticket.md | 44 +++++++++++++++++++++
 tickets/T-2829/ticket.md | 41 ++++++++++++++++++++
 tickets/T-2830/ticket.md | 41 ++++++++++++++++++++
 10 files changed, 469 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/test_arch_gate.py::TestArchGateLargeFile::test_large_file_fires_large001_warn` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 21 error(s), 857 warning(s), 717 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, CYCLE001@src/frob/__init__.py, DOC001@docs/investigations/T-2790-check-stage-profile.md, DOC001@docs/investigations/T-2796-backlog-reproduction.md, DOC006@docs/audits/test005-zero-classification-t1418.md, DOC011@docs/investigations/T-2796-backlog-reproduction.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, PERF004@src/frob/tickets/_evidence.py, REG002@docs/design/registry/check-coverage.yaml, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, SYS003@src/frob/check/__init__.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md

### Acceptance amendments
- [0] replace: "given the family's WARN codes, when frob check --json runs, then zero findings remain" -> "given the family's WARN codes, when frob check --json runs, then the finding count is MEASURED (85, confirmed against T-2796's independent measurement) and DECOMPOSED into disjoint, independently-landable child tickets (--parent T-2375) -- burning the count to zero is delegated to those children, not this ticket, because a single-cause fix does not exist here (85 independently oversized files, each needing its own split-or-waive judgment call per the T-1651 precedent)" (reason: T-2796 dispatch decision 2026-08-21: characterization showed this is not a mechanical burn-down (unlike REF001's likely-single-cause 257 findings) -- 85 independent files each need bespoke split/waive judgment. Grinding all 85 in one ticket would either force bad splits (T-1651's own warning: worse than the finding it silences) or take an infeasible single dispatch. Decomposed into 9 child tickets instead; this criterion is amended to describe what T-2375 itself delivers (measurement + characterization + decomposition), not the terminal zero-count, which the children carry; logan, 2026-08-21)
- [1] replace: "given the family's gate module, when its severity is read, then it is ERROR not WARNING" -> "given the family's gate module, when its severity is read, then the WARN->ERROR promotion is tracked as a separate successor ticket, blocked-by all 9 child batch tickets, and executed only after every child lands -- promoting severity before the children land would red main for every not-yet-fixed file, which T-2809/T-2816's own lesson (do not spend a shared budget/state prematurely) applies here as well" (reason: Same 2026-08-21 dispatch decision as acceptance[0]: promoting large-file to Severity.ERROR now, while 84 files are still open findings, turns every one of those into a fresh ERROR and reds main for work already accounted for in the 9 open children. The promotion is real, scoped (src/frob/gates/_arch.py + its two test files), and tracked -- just not performed by this ticket; logan, 2026-08-21)
