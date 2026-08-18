## Done report

Added a permanent, corpus-wide regression test for T-2187's
grammar-vs-locator reconciliation, replacing the manual-verification-only
prose in T-2187's Done report.

design/frob.strata: added tests/unit/test_lang_strata.py to the
`testsuite` node's `may "exec"` and `may "fs.read"` via-lists (T-1870
scope note: this is a deliberate, reviewed capability grant matching
exactly what the new test needs -- subprocess.run for `git ls-files
'*.strata'` and Path.read_text() to load each file -- not an automated
or unreviewed surface expansion).

tests/unit/test_lang_strata.py: new
TestGrammarAuthoritativeSymbolsCorpusWide class. Walks every
`git ls-files '*.strata'` result and compares walk_strata's own returned
symbol count against `_declared_items`' independent grammar-authoritative
count for that same source. A weaker version that only checked
`walk_strata(...).is_err` was tried first and rejected: T-2187's own
pre-fix code never returns Err on a grammar-vs-locator disagreement, it
silently returns an undercounted symbol set and downgrades the mismatch
to a log warning -- so an is_err-only test would pass against BOTH the
fixed and the unfixed code (verified directly: 0 of 64 corpus files
raised Err against T-2187's pre-fix _walk_strata.py). The count
comparison genuinely distinguishes the two: verified failing (17 of 64
files mismatched) against 64b747e4e~1 (T-2187's land parent, pre-fix
_walk_strata.py, loaded via importlib from a temp file since the old
module lacks _declared_items/other T-2187 symbols the test module
imports), and passing (0 mismatches) against the current fixed tree.

SELFAUDIT001 note: this ticket's own capability grant pushes the
`testsuite` node's SYS111 exec/fs.read via-list site counts over the
committed capability-via-ratchet.lock.json ceiling by one each
(confirmed: absent against main's unmodified design/frob.strata, present
after adding the two via-list entries). Per playbook section 0 item 5,
`frob ticket land`'s Tier-A auto-fix sweep
(fix_sys111_capability_ratchet_sync) absorbs and re-baselines this file
automatically as part of land's pre-merge wip-commit -- not hand-edited
here. This is a deliberate, ticket-scoped grant, not the T-1870-flagged
"rubber-stamp an unreviewed surface expansion" case T-2323 was warned
about separately.

### Changed
```
 tickets/T-2194/ticket.md | 4 +++-
 1 file changed, 3 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_lang_strata.py::TestGrammarAuthoritativeSymbolsCorpusWide::test_every_tracked_strata_file_symbol_count_matches_grammar_declared_count` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/release/_cli.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/tickets/_land_git_ops.py, COV001@src/frob/verify/_drain.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, DOC001@docs/commands/release.md, DOC002@src/frob/app/verify_runner.py, DOC002@src/frob/verify/_drain.py, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/gates/_fmt_directives.py, DRIFT002@scripts/fleet_status.py, DRIFT002@src/frob/verify/_drain.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PERF004@src/frob/app/ticket_runner/_new.py, PRE001@tickets/T-2194, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK004@tickets.md, WIRE003@docs/modules/cli.md
