## Done report

Changed:
src/frob/process/parsers/ruff.py::_is_ruff_error_code
src/frob/process/parsers/ruff.py::_ruff_json_diagnostic
src/frob/process/parsers/ruff.py::parse_ruff_text
src/frob/gates/_waive.py::_KNOWN_GATE_RULES (I001 added)
src/frob/gates/__init__.py (ruff --fix reformat, 1 file, no symbol change)
src/frob/gates/_arch.py (ruff --fix reformat, 1 file, no symbol change)
src/frob/gates/_tickets_gate.py (ruff --fix reformat, 1 file, no symbol change)
src/frob/tickets/_setters.py (ruff --fix reformat, 1 file, no symbol change)
tests/unit/test_ticket_new_priority_inherit_t1960.py (ruff --fix reformat)
tests/unit/test_waive_audit_runner.py (ruff --fix reformat)
tests/unit/verify/test_attribution_module_scope.py (ruff --fix reformat)
tests/unit/verify/test_backpressure.py (ruff --fix reformat)
docs/modules/process.md (AFFECT001 closure: severity mapping note)
docs/modules/gates.md (DOCENUM001 closure: I001 added to _KNOWN_GATE_RULES member list)

Re-measured before starting: `uv run frob check --json --budget 500` (fresh
worktree, natives rebuilt) found 9 I001 findings across 8 files -- NOT the
23 the ticket body recorded from 2026-08-18 (batch 1, T-2788, and batch 2,
T-2800, both landed since and had already reduced the count). This is the
final batch: fixed all 9 with `ruff check --select I001 --fix` on exactly
those 8 files, then re-ran `uv run frob check --json --budget 500` and
confirmed 0 I001 findings remain repo-wide.

Both acceptance criteria closed:
[0] zero I001 findings -- verified via the same
    `frob check --json --budget 500` command, 0 remaining.
[1] severity promoted from warning to error -- `_is_ruff_error_code` in
    `src/frob/process/parsers/ruff.py` now treats I001 the same as E/F
    codes; both the JSON and text ruff parsers route through it. I
    explicitly verified zero I001 findings remained BEFORE writing this
    promotion, per the ticket's own instruction not to promote early.

Evidence:
tests/unit/test_parse.py::TestParseRuffText::test_severity_i001_is_error
tests/unit/test_parse.py::TestParseRuffJson::test_i001_is_error

Both are new tests added in this batch, asserting I001 renders as
"error" via parse_ruff_text and parse_ruff_json respectively.

Also ran the wider touched-file test set (tests/unit/test_parse.py -k
Ruff: 28/28 pass; tests/system/test_cli_parse.py, tests/unit/test_process.py,
tests/unit/test_rapid_sweep.py, tests/unit/test_ticket_runner_gate_findings.py,
tests/unit/test_parser_failure_diagnostics.py: 283/283 pass). Three
tests/system/test_system.py::*cycle* failures reproduced identically on
unmodified main -- pre-existing, unrelated to this change.

Filed: none (no out-of-scope work discovered).

Gates: `frob check --ticket T-2373` re-measured at 30 errors, all
pre-existing repo-wide findings (CYCLE001, COV001, DOC001/006/011, DRIFT001/002,
PERF004, REG002, SEC110, SYS003, TEST001, TICK003/004/006, claude-config-drift)
unrelated to this diff -- confirmed by diffing successive `frob check --ticket`
runs before/after this batch's own GATERULE001 (I001 registry) and AFFECT001/
DOCENUM001 (doc-closure) findings were fixed in-batch. No waivers needed.

### Changed
```
 tickets/T-2373/ticket.md | 93 ++++++++++++++++++++++++++++++++++++++++++++++--
 1 file changed, 91 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/test_parse.py::TestParseRuffText::test_severity_i001_is_error` (pytest node id, verified passing when recorded)
- `tests/unit/test_parse.py::TestParseRuffJson::test_i001_is_error` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 19 error(s), 1677 warning(s), 711 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, CYCLE001@src/frob/__init__.py, DOC001@docs/investigations/T-2790-check-stage-profile.md, DOC001@docs/investigations/T-2796-backlog-reproduction.md, DOC006@docs/audits/test005-zero-classification-t1418.md, DOC011@docs/investigations/T-2796-backlog-reproduction.md, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, PERF004@src/frob/tickets/_evidence.py, REG002@docs/design/registry/check-coverage.yaml, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SYS003@src/frob/check/__init__.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md
