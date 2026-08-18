## Done report

Changed:
- src/frob/__main__.py::_GroupedHelpFormatter._format_grouped_subparsers
- src/frob/_cli_parsers/_ops.py::_add_ops_parser (help string only, second-order nit)
- tests/unit/test_main_entry.py::TestGroupedHelpFormatter (2 header-indent
  tests added, 2 pre-existing indent-level assertions updated for the new
  deeper entry indent)

Coordinator's prototype held up under an actual test, with one correction:
the original prototype text used `self._indent()`/`self._dedent()`
bracketing exactly as given and it produces correct output -- verified
directly by rendering `frob --help` and confirming the section headers
render at 2-space indent while every entry beneath them renders at
4-space indent (previously both were 2-space, the reported bug). The one
thing the prototype's own body flagged as a nit turned out to be real
and repro'd exactly as predicted: the narrower description column broke
`ops`'s help string as ".../doctor/c" / "lean/..." -- fixed by
shortening that string (comma-separated verb list instead of a
slash-run) and checked the other three verb-group help strings
(explore/quality/design) for the same failure mode; none of them break
mid-word at the new column width.

Verification method: rendered `parser.format_help()` directly and
`frob --help` via the CLI, diffed line-by-line for any line ending in a
single orphan letter glued to the next line with no space (the exact
signature of the original bug, "...clean/c" then "lean/..."). Zero such
lines after the fix. Added
`test_section_headers_indent_strictly_less_than_entries` (header
indent < first entry's indent, generically, not a golden string) and
`test_no_help_text_breaks_inside_a_word` (scans every rendered line for
the orphan-letter signature) as the acceptance[0] test surface,
matching this ticket's own instruction not to snapshot full output.

Waivers preserved unchanged (acceptance[1]): both `frob:waive WIRE001`
blocks on `_format_action` and `_format_grouped_subparsers` are
byte-identical to main (confirmed via `git diff main --
src/frob/__main__.py` -- only additions are two new `frob:tests`
directive lines and the loop body itself; no waiver text touched).
Also confirms T-1831 (the WIRE001 follow_up anchor) required no
change and was not touched.

Collapsed the two near-identical header-emitting branches into one
loop over `(header, acts)` pairs, per acceptance[1].

Filed: none (the ops-help second-order fix was already explicitly
in-ticket scope per this ticket's own body).

Gates: this ticket's diff-scoped checks are clean; full unscoped
`frob check` on this repo carries pre-existing ARCH/DRIFT/PERF findings
across unrelated files (measured, present on main before this change).

### Changed
```
 src/frob/__main__.py               | 24 +++++++++----
 src/frob/_cli_parsers/_ops.py      |  7 ++--
 tests/unit/test_main_entry.py      | 60 ++++++++++++++++++++++++++++++--
 tickets/T-2385/ticket.md           | 38 ++++++++++++++++++--
 tickets/T-2387/done-report.md      | 71 ++++++++++++++++++++++++++++++++++++++
 tickets/T-2387/ticket.md           |  8 ++++-
 tickets/T-2397/ticket.md | 48 ++++++++++++++++++++++++++
 7 files changed, 242 insertions(+), 14 deletions(-)
```

### Evidence
- `tests/unit/test_main_entry.py::TestGroupedHelpFormatter::test_verb_groups_listed_before_also_available_directly_section` (pytest node id, verified passing when recorded)
- `tests/unit/test_main_entry.py::TestGroupedHelpFormatter::test_non_group_verb_listed_after_also_available_directly` (pytest node id, verified passing when recorded)
- `tests/unit/test_main_entry.py::TestGroupedHelpFormatter::test_nested_subparser_help_is_unaffected` (pytest node id, verified passing when recorded)
- `tests/unit/test_main_entry.py::TestGroupedHelpFormatter::test_section_headers_indent_strictly_less_than_entries` (pytest node id, verified passing when recorded)
- `tests/unit/test_main_entry.py::TestGroupedHelpFormatter::test_no_help_text_breaks_inside_a_word` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: AFFECT001@src/frob/__main__.py, ARCH103@src/frob/release/_cli.py, COV001@src/frob/verify/_drain.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV005@src/frob/app/_config_external.py, DOC001@docs/commands/release.md, DOC002@src/frob/verify/_drain.py, DOC005@docs/modules/cli.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT002@docs/modules/vet.md, E501@/home/logan/projects/frob/.claude/worktrees/contention-cluster/src/frob/verify/_worker.py, F401@/home/logan/projects/frob/.claude/worktrees/contention-cluster/src/frob/vet/_capability.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_new.py, PRE001@tickets/T-2385, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md
