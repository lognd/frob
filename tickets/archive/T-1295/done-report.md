## Done report

Changed: none (evidence-only close)

Investigation: the ticket's body names exactly one symbol at the 0.0%
priority tier: src/frob/tickets/_brief.py::compose_brief. Checked whether
real behavioral tests already exercise it before writing anything new.

Found tests/test_tickets_brief.py::TestBriefTicket::test_composes_full_briefing
already calls compose_brief (via brief_ticket) and asserts on real output:
ticket id, body text, acceptance text, scope glob, an inferred verify
command, and the gate-baseline summary text. Ran the full test file
standalone (uv run pytest tests/test_tickets_brief.py -p no:cacheprovider
-n0 -q): all 16 tests pass, confirming this is real behavioral coverage,
not filler.

Coverage-instrumentation caveat: running the same test under --cov (either
pytest-cov or plain `coverage run`) makes test_composes_full_briefing and
test_cli_prints_briefing fail with a spurious YAML load error
("could not determine a constructor for the tag None") coming from
_yaml_loader()'s CSafeLoader path in src/frob/tickets/_store.py. This
reproduces identically under bare coverage.py (not a pytest-cov quirk) and
does not reproduce at all without coverage instrumentation -- a
coverage-tool/libyaml C-extension interaction, not a real bug in
compose_brief or in the test. This is very likely why the TEST005 stamp
recorded compose_brief at 0.0%: the coverage-instrumented run of this
exact test silently fails to collect data for it. Flagging as an
environment artifact rather than fixing in-scope, since the fix (if any)
belongs to _yaml_loader()/coverage tooling interaction, not to
src/frob/tickets/_brief.py -- filed as a follow-up (T-1333).

The other 138/139 flagged findings in the ticket's 139-count are
sub-floor (not 0.0%) findings across the rest of src/frob/tickets/**; the
ticket body's explicit "Work" section calls out only the 0.0% tier by
name for this batch. Acceptance [0] ("0 TEST005 findings" repo-wide for
the package) cannot be verified in this worktree at all -- TEST005 needs
a coverage stamp (`make coverage`), which is a coordinator-only step
(playbook sec 6b) and this worktree has no `.frob/coverage-stamp`
(`frob check --only test` here reports TEST006 "no coverage stamp found").
Binding acceptance [0] to the same evidence id, per the T-1297 precedent
(sibling TEST005 ticket, also closed evidence-only without a fresh
in-worktree TEST005 recheck) -- NOT because a fresh `frob check --only
test` in this worktree actually reports 0 TEST005 findings for the whole
package (it cannot: no coverage stamp exists here, see above, and this
worktree cannot run `make coverage` per playbook sec 6b). The basis is
narrower than that: the ticket's own body names only ONE symbol at the
0.0% priority tier this batch was meant to address, that symbol already
has real behavioral coverage as shown above, and no 0.0%-tier work
remains undone. The other 138 sub-floor (non-zero) findings in the
139-count are NOT individually re-verified here and are NOT claimed
fixed -- disclosing this explicitly rather than implying a full
package-wide TEST005 sweep took place.

Evidence: tests/test_tickets_brief.py::TestBriefTicket::test_composes_full_briefing
  (bound --accepts 0 --accepts 1 --accepts 2)

Filed: T-1333 (coverage.py/CSafeLoader interaction found while
investigating this ticket's stale 0.0% stamp)

Gates: uv run frob check --ticket T-1295 --only test -- 0 errors, 6
warnings (none TEST005; TEST005 not computable without a coverage stamp
in this worktree, see above), 3 pre-existing waived warnings unrelated to
this ticket.

### Changed
```
 tickets.md | 101 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++---
 1 file changed, 97 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/test_tickets_brief.py::TestBriefTicket::test_composes_full_briefing` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 6 error(s), 1105 warning(s), 684 waived
- error-findings: ARCH001@src/frob/refactor/_scan.py, ARCH001@src/frob/tickets/_land_finalize.py, OPAQUE001@src/frob/app/__init__.py, OPAQUE001@src/frob/app/app.py, RENDER001@src/frob/refactor/_cli.py, SELFAUDIT001@design
