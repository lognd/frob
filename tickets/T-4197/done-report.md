## Done report

Changed:
- src/frob/graph/dsl.py::_resolve_target_and_attrs (new, extracted from _parse_line for ARCH001)
- src/frob/graph/dsl.py::_tests_quoted_title_error (new)
- src/frob/graph/dsl.py::_parse_line (now calls both of the above)
- tests/unit/graph/test_dsl.py::TestQuotedTestsTitleMustNamePath (3 new tests)

Home decision (per this ticket's own instruction to read T-4260's precedent first): T-4260
concluded a malformed frob:tests/frob:waive directive is wrong the moment it is written and
belongs at parse time (frob.graph.dsl), not inside the gate that later consumes the resulting
edge, but left that move out of scope because its own ticket declared src/frob/gates only.
This ticket widened scope to add src/frob/graph/dsl.py (frob ticket scope --add, reasoned)
and the fix lives there, matching that precedent directly rather than adding a second,
gate-side symptom check.

Premise verified on main before building, per finding:

F-318 (free-text symref in frob:tests parses silently, TEST002 counts go to zero): CONFIRMED
real and current. `_parse_target`'s quoted-target convention (T-3893, F-047: a `frob:tests`
target with spaces is a vitest describe/it title, quoted as one value) accepts ANY quoted
string as a valid target with no shape check at all -- pure prose with no leading test-file
path parses to a perfectly normal Edge whose target simply never resolves to any collector,
degrading TEST002's count for the file silently. Fixed: a quoted `frob:tests` target must now
lead with a real path token (contains a file extension, e.g. `"src/x.test.ts describes a
thing"` -- the shape every genuine instance of the documented convention already has, this
repo's own docs/tests included). An unquoted, single-token target (the widespread bare
`TestFoo.test_bar` self-reference convention, T-0265) is untouched -- the check only fires
when the target contains a space (i.e., was quoted).

F-333 (multi-line frob:waive whose continuation lines lack the # prefix silently fails to
attach): premise did NOT hold on current main -- empirically re-verified with three
constructed repros matching the reported shape (reason="..." left open across a missing-#
continuation; target-only backslash with the reason attribute entirely on the missing-#
line; a third attr split the same way) and all three already produce a MalformedDirective
today, via the existing leftover-attrs-syntax and mandatory-attribute checks (most likely
landed after the original incident, since neither T-0313 -- the ticket F-333 cites -- nor
any other located ticket is actually about this mechanism). The ONE case that stays silent
(a bare single-token target like `frob:ticket T-0042\`, no attrs at all) is a DELIBERATE,
test-locked design decision (T-0286, `test_dangling_backslash_on_last_comment_line_is_
literal` / `test_unrelated_directives_on_consecutive_lines_do_not_fold`): a dangling trailing
backslash with nothing to fold into is treated as literal content, not malformed, specifically
because the very next physical comment line being a genuinely independent, valid directive
(the T-0286 corruption repro) is structurally indistinguishable from "the intended
continuation line is simply missing its # prefix" -- there is no parser-visible signal to tell
the two apart, and reversing the design would risk new false positives against an already-
accepted convention. Not fixed, and not force-fit: F-333 half of this ticket is dropped as no
longer reproducing / already covered, per the "verify the premise before building" and
"open a new ticket only for a deliberate deferral, never invent work" instructions -- there is
no live discovery here to file, since re-verification found nothing outstanding to defer.

Fixture-testable repro: confirmed fail-then-pass. `--designate-repro` bound against the
test-only commit (727193e6e, test committed alone, still-unfixed parser) -- FAILED_AT_PARENT
verdict recorded.

Evidence:
- tests/unit/graph/test_dsl.py::TestQuotedTestsTitleMustNamePath::test_pure_prose_quoted_target_is_malformed_not_a_free_pass

Filed: none (F-333 dropped with the measurement above, not deferred to a new ticket).

Gates: `frob check --ticket T-4197` clean of errors attributable to this diff (ARCH001/
LANDPARITY002 fixed by extracting `_resolve_target_and_attrs`; COV002 fixed by binding
`frob:ticket T-4197` on each new/changed symbol). Remaining --ticket-scoped FAIL rows
(gate:ARCH ARCH103 in src/frob/graph/cache.py, gate:TODO T-4298 binding, gate:WIRE T-4274
waiver, gate:SCOPE closure warnings against the module-wide scope glob declared at filing)
are pre-existing and unrelated to this diff. `gate:TEST` (repo-wide, unscoped) is clean (0
errors) -- confirms the new parse-time check does not silently break any existing frob:tests
directive in the corpus (verified the only other quoted-target usages repo-wide are this
module's own test fixtures and the documented example in docs/guides/extending/comment-dsl-
directives.md, both of which already lead with a real path).

### Changed
```
 src/frob/graph/dsl.py        | 89 +++++++++++++++++++++++++++++++++++++-------
 tests/unit/graph/test_dsl.py | 56 ++++++++++++++++++++++++++++
 tickets/T-4197/ticket.md     | 16 +++++++-
 3 files changed, 145 insertions(+), 16 deletions(-)
```

### Evidence
- `tests/unit/graph/test_dsl.py::TestQuotedTestsTitleMustNamePath::test_pure_prose_quoted_target_is_malformed_not_a_free_pass` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 6 error(s), 4687 warning(s), 949 waived
- error-findings: ARCH103@src/frob/graph/cache.py, PRE001@tickets/T-4197, SCOPE002@tickets.md, SELFAUDIT001@design, TODO002@src/frob/gates/_land_format.py, WIRE002@tests/test_ci_workflow_timeout.py
