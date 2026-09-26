## Done report

Root cause (corrected after re-verification): crunk pins ruff 0.16.5,
which changed `ruff format --check`'s "would reformat" grammar. It no
longer prints "Would reformat[:] <path>" -- instead it emits an
"unformatted: File would be reformatted" diagnostic header, a
"  --> <path>:<line>:<col>" locator line, and a diff block, followed by
a trailing "N files would be reformatted, M files already formatted"
summary. `src/frob/process/parsers/ruff.py::parse_ruff_would_reformat_
paths` did not recognise this `-->` grammar and returned zero paths, so
`src/frob/check/_python.py::_ruff_format_result` built a ToolResult with
`exit_code=1` and `diagnostics=[]` -- which the T-2521 completeness
check (`_verify.py::_incomplete_tool_results`, unmodified and already
correct) then, correctly given that empty-diagnostics input, classified
as a crashed/silent tool stage rather than measured format drift. The
completeness check itself needed no change; the parser did.

Changed: `parse_ruff_would_reformat_paths` now also matches ruff
0.16.5's `--> <path>:<line>:<col>` locator line (discarding line/col),
alongside the existing colon and colon-less "Would reformat" forms,
de-duplicated and sorted. Scope widened (with reason, `frob ticket
scope --add`) to `src/frob/process/parsers/ruff.py` and
`tests/unit/test_ruff_reformat_parser.py`, the shared parser's own
module and test file, once the root cause was re-localised there.

Positive controls added: `TestRuff0165UnformattedArrowGrammar` in
tests/unit/test_ruff_reformat_parser.py -- one fixture string in the
exact 0.16.5 shape resolves to the real path
(`test_arrow_line_yields_the_real_path`); a whole-run `ToolResult` built
from that output the way `_ruff_format_result` builds one carries a
real, non-empty diagnostics list on `exit_code=1`
(`test_whole_run_tool_result_carries_diagnostics_on_nonzero_exit`); and
a mixed-grammar regression control
(`test_multiple_files_both_arrow_and_colon_forms_mixed`). The earlier
`tests/unit/verify/test_worker.py::TestDefaultVerifyFnRuffFormatDriftIs
Measured` end-to-end verify-worker controls (added before this
re-verification) are kept unchanged -- they still lock in that the
completeness check itself reads any nonzero-exit diagnostic, warning
included, as measured.

Filed: none.

### Changed
```
 src/frob/process/parsers/ruff.py        | 50 +++++++++++++-----
 tests/unit/test_ruff_reformat_parser.py | 75 ++++++++++++++++++++++++++
 tests/unit/verify/test_worker.py        | 93 +++++++++++++++++++++++++++++++++
 tickets/T-draft-cbdee0d3/done-report.md | 50 ++++++++++++++++++
 tickets/T-draft-cbdee0d3/ticket.md      | 31 +++++++++--
 5 files changed, 281 insertions(+), 18 deletions(-)
```

### Evidence
- `tests/unit/verify/test_worker.py::TestDefaultVerifyFnRuffFormatDriftIsMeasured::test_warning_only_diagnostic_yields_a_measured_result` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_worker.py::TestDefaultVerifyFnRuffFormatDriftIsMeasured::test_zero_diagnostics_is_still_unmeasurable` (pytest node id, verified passing when recorded)
- `tests/unit/test_ruff_reformat_parser.py::TestRuff0165UnformattedArrowGrammar::test_arrow_line_yields_the_real_path` (pytest node id, verified passing when recorded)
- `tests/unit/test_ruff_reformat_parser.py::TestRuff0165UnformattedArrowGrammar::test_whole_run_tool_result_carries_diagnostics_on_nonzero_exit` (pytest node id, verified passing when recorded)
