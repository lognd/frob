## Done report

Changed:
  tests/unit/test_land_finish_idempotent.py::TestFinishOnlyIfAlreadyLanded::test_done_on_main_but_content_not_confirmed_runs_the_normal_land (frob:waive OPAQUE001 on line 243)

Investigated before waiving (not a reflexive clear): `loaded.danger_ok[tid]` at line 243 is a
plain dict `__getitem__` read into a local -- it is never called. OPAQUE001's
"container dynamic-key call" detector (`_SUBSCRIPT_CALL_RE`,
src/frob/vet/_capability_scan.py) is a byte-level regex, not an AST/statement-bound scan; its
trailing `\s*\(` lets the whitespace class span a newline, so this line's closing `]` plus the
NEXT (unrelated) statement's leading `(` -- `(wt / "src").mkdir(...)` -- reads as
`container[key](...)`, a genuine cross-statement false positive, not a real dynamic dispatch.

This is a detector defect, not a code defect at this site -- fixing the regex itself is out of
T-3392's declared scope (src/frob/vet/_capability_scan.py, a security-relevant scanner used
repo-wide for four languages, not this ticket's file). Filed T-3405 to fix the detector
(bind the match to one statement/logical line) instead of fixing it silently or expanding
scope. Waived here with the full explanation inline, per OPAQUE001's own documented discharge
path ("Fix by resolving the target statically, or frob:waive OPAQUE001 reason=... with a real
justification").

Evidence:
  frob check --only opaque (repo-wide): gate:OPAQUE 0 errors (was 1)
  tests/unit/test_land_finish_idempotent.py: 9/9 pass

Filed: T-3405 (OPAQUE001 _SUBSCRIPT_CALL_RE crosses statement boundaries, scope
  src/frob/vet/_capability_scan.py -- out of T-3392's scope)
Gates: frob check --only opaque -- gate:OPAQUE clean (repo-wide); ruff-check/ruff-format clean
  on the touched file.

### Changed
```
 tickets/T-3392/ticket.md | 5 ++++-
 1 file changed, 4 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_land_finish_idempotent.py::TestFinishOnlyIfAlreadyLanded::test_non_terminal_on_main_runs_the_normal_land` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_finish_idempotent.py::TestFinishOnlyIfAlreadyLanded::test_done_on_main_but_content_not_confirmed_runs_the_normal_land` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 18 error(s), 3931 warning(s), 899 waived
- error-findings: CYCLE001@src/frob/__init__.py, DEBT002@src/frob/app/check_runner.py, DEPR006@frob-deprecated-baseline.lock.json, DOC003@docs/commands/sys.md, DOC006@tickets/T-1382/ticket.md, DOC011@docs/modules/tickets.md, PRE001@tickets/T-3392, REL001@src/frob/__init__.py, REL001@src/frob/__main__.py, REL001@src/frob/app/check_runner.py, REL001@src/frob/app/ticket_runner/_land_cmd.py, REL001@src/frob/stats/_agentic.py, REL001@strata-core/src/graph/vmodel.rs, REL001@strata-core/src/parse/grammar_core.rs, REL001@tests/unit/test_conftest_suite_result_status.py, SELFAUDIT001@design, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
