## Done report

FIX: of the 5 (rule, file) identities this ticket named, only ONE was
still live at investigation time -- TEST001 on
src/frob/app/ticket_runner/_new.py::related_tickets (no frob:tests
directive, despite two real, passing tests already covering it in
tests/unit/test_ticket_new_related.py::TestRelatedTicketsSearch). Added
the frob:tests directive binding both existing tests. AFFECT001 (x2) and
REL002 had already been resolved by later, unrelated lands before this
ticket was worked (re-measured directly: .frob-release.json and
pyproject.toml agree on 0.441.0; no AFFECT001 finding against either
_new.py file in a fresh `frob check`).

ATTRIBUTION CORRECTION (with evidence): this ticket's title and body
name T-1977 (my own capability-ratchet wiring ticket) as the cause. That
attribution is WRONG. All 5 identities are in files T-1977 never
touched (src/frob/_cli_parsers/_ticket/_new.py,
src/frob/app/ticket_runner/_new.py, .frob-release.json) -- T-1977's own
diff (commit f3257572abbd7bf215b9cd66a9c6948c8c223df3) touched only
src/frob/gates/_sys_selfaudit.py, src/frob/gates/_waive.py,
src/frob/strata/__init__.py, src/frob/strata/_effects.py,
docs/modules/gates.md, docs/design/registry/capability-via-ratchet.lock.json,
and tests/test_gates.py (verified via `git show --stat`). Every one of
these 5 identities instead belongs to T-1995 ("related_tickets"/
"--ack-related" feature, the exact function this fix touches), which
landed concurrently with T-1977. The deferred post-land sweep (T-1684)
measures the WHOLE current tree whenever it runs, with no notion of
which land actually introduced a given finding -- T-1995's land landed
between T-1977's own pre-land baseline and the detached sweep that ran
after T-1977's land finished, so the sweep's diff (fresh vs baseline)
correctly found new findings, but filed them under whichever ticket's
sweep happened to fire next (T-1977), not the ticket whose diff actually
introduced them (T-1995). This is a structural misattribution gap in
the deferred sweep under concurrent lands -- filed separately with
measured evidence (this ticket) rather than fixed here, since fixing
the sweep is a different, larger change than fixing 1 real finding.

### Changed
```
 tickets/T-1998/ticket.md | 7 ++++++-
 1 file changed, 6 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_ticket_new_related.py::TestRelatedTicketsSearch::test_finds_an_archived_close_title_match` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_new_related.py::TestRelatedTicketsSearch::test_no_match_for_a_genuinely_distinct_title` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: DSL001@CHANGELOG.md, F401@/home/logan/projects/frob/.claude/worktrees/ticket-workflow/tests/unit/test_tickets_evidence_only_scope.py, SELFAUDIT001@design
