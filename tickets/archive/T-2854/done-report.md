## Done report

Changed:
tests/unit/test_coordinator_scripts.py::TestFleetStatusLarge001WaiverParses.test_waiver_still_suppresses_large001 (docstring only)
tests/unit/test_coordinator_scripts.py::TestOwnDocstringHasNoMalformedDirective.test_no_malformed_directives_in_this_file
tests/unit/graph/test_dsl_mention_escape.py::TestDocstringMentionEscape.test_unescaped_docstring_prose_is_malformed
tests/unit/graph/test_dsl_mention_escape.py::TestDocstringMentionEscape.test_escaped_docstring_prose_produces_no_malformed_or_edge
tests/unit/graph/test_dsl_mention_escape.py::TestDocstringMentionEscape.test_real_directive_inside_a_docstring_still_parses

Evidence:
tests/unit/test_coordinator_scripts.py::TestOwnDocstringHasNoMalformedDirective::test_no_malformed_directives_in_this_file (designated repro, FAILED_AT_PARENT verified against 6cdf21a9d)
tests/unit/graph/test_dsl_mention_escape.py::TestDocstringMentionEscape::test_unescaped_docstring_prose_is_malformed
tests/unit/graph/test_dsl_mention_escape.py::TestDocstringMentionEscape::test_escaped_docstring_prose_produces_no_malformed_or_edge
tests/unit/graph/test_dsl_mention_escape.py::TestDocstringMentionEscape::test_real_directive_inside_a_docstring_still_parses

Premise verified before fixing: called frob.graph.dsl.parse_directives
directly against tests/unit/test_coordinator_scripts.py's real content --
confirmed exactly 1 MalformedDirective at line 5110 ("bad attribute
syntax: 'still parses as one directive and still binds,'"), matching the
ticket's reported symptom exactly. This is case (a) from the ticket body:
a genuine scanner false positive on prose, not a case where the scanner
is correctly firing on a real malformed directive.

Root cause: Python docstrings are directive-scannable by design (T-0342,
frob.lang._walk_python._walk_python_docstring_comments), so a docstring
line whose SHAPE matches a directive (starts with "frob:<verb>") is
indistinguishable from a genuine one-line directive to frob.graph.dsl's
per-line _LINE_RE matcher. T-1970 already fixed the identical shape of
problem for #-comment prose, shipping the canonical frob:quote(...)
escape (frob.graph.dsl.mask_frob_mentions). This ticket found the same
problem in a comment-carrier (docstrings) T-1970's own fixtures never
exercised, and applies the SAME existing escape rather than inventing a
new mechanism or weakening the per-line matcher.

Fix: wrapped the mention in the offending docstring line with
frob:quote(frob:waive reason) ... -- three-line docstring reflow, no
behavior change to the DSL parser itself.

Positive controls (both directions), tests/unit/graph/test_dsl_mention_escape.py::TestDocstringMentionEscape:
- test_unescaped_docstring_prose_is_malformed: an unescaped docstring line shaped like a directive DOES still report malformed.
- test_escaped_docstring_prose_produces_no_malformed_or_edge: the same content, escaped, produces neither a malformed finding nor a spurious edge.
- test_real_directive_inside_a_docstring_still_parses: a GENUINE directive written inside a docstring still binds after the fix -- the scanner was not weakened.

Scope: added tests/unit/graph/test_dsl_mention_escape.py via frob ticket scope --add (reason recorded on the ticket).

Filed: none -- no out-of-scope work discovered.

Gates: frob check findings on the two touched files were limited to PRE001/SCOPE001 (resolved once frob ticket start/sweep recognized the in-progress ticket) -- no DSL001/COV/AFFECT findings on either touched file. All other findings observed in an unscoped frob check run are pre-existing red-tree fallout (T-2846 Rust split / frob-core doc drift, tracked as T-2855) unrelated to this ticket's two files.

### Changed
```
 tests/unit/graph/test_dsl_mention_escape.py | 74 +++++++++++++++++++++++++++++
 tests/unit/test_coordinator_scripts.py      | 35 ++++++++++++--
 tickets/T-2854/ticket.md                    | 29 ++++++++++-
 3 files changed, 133 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/unit/test_coordinator_scripts.py::TestOwnDocstringHasNoMalformedDirective::test_no_malformed_directives_in_this_file` (pytest node id, verified passing when recorded)
- `tests/unit/graph/test_dsl_mention_escape.py::TestDocstringMentionEscape::test_unescaped_docstring_prose_is_malformed` (pytest node id, verified passing when recorded)
- `tests/unit/graph/test_dsl_mention_escape.py::TestDocstringMentionEscape::test_escaped_docstring_prose_produces_no_malformed_or_edge` (pytest node id, verified passing when recorded)
- `tests/unit/graph/test_dsl_mention_escape.py::TestDocstringMentionEscape::test_real_directive_inside_a_docstring_still_parses` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 45 error(s), 668 warning(s), 795 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@frob-core/src/callgraph.rs, COV001@frob-core/src/exact_regions.rs, COV001@frob-core/src/lib.rs, COV001@frob-core/src/r3.rs, COV001@frob-core/src/r4.rs, COV001@frob-core/src/r5.rs, COV001@src/frob/graph/callgraph.py, CYCLE001@src/frob/__init__.py, DOC006@docs/audits/test005-zero-classification-t1418.md, DOC006@docs/modules/dup-sota-survey.md, DOC006@docs/modules/dup.md, DOC011@docs/investigations/T-2796-backlog-reproduction.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/dup.md, DRIFT002@docs/modules/tickets-data-storage.md, DRIFT002@frob-core/src/lib.rs, DRIFT002@tests/test_arch_near_duplicate_native.py, DRIFT002@tests/unit/test_dup_core.py, OPAQUE001@src/frob/gates/_refs.py, PERF004@src/frob/strata/_selfconform_binding_rules.py, PERF004@src/frob/strata/_selfconform_surface_rules.py, PERF004@src/frob/tickets/_evidence.py, PRE001@tickets/T-2854, REF001@frob-core/src/callgraph.rs, REF001@frob-core/src/exact_regions.rs, REF001@frob-core/src/r3.rs, REF001@frob-core/src/r4.rs, REF001@frob-core/src/r5.rs, REG002@docs/design/registry/check-coverage.yaml, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, SYS003@src/frob/check/__init__.py, TEST001@frob-core/src/exact_regions.rs, TEST001@frob-core/src/lib.rs, TEST001@frob-core/src/r3.rs, TEST001@frob-core/src/r4.rs, TEST001@frob-core/src/r5.rs, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md
