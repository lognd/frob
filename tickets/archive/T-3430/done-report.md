## Done report

Added tests/unit/test_arch_srp.py to design/frob.strata's testsuite node
may "fs.read" via-list. The file already reads real source files
(real_source.read_text() at lines 616 and 650, in
test_import_check_env_arch103_is_waived and
test_git_head_sha_arch103_is_waived) and was already declared for
fs.write in the same node -- fs.read was missed.

Evidence: tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant
(bound) -- confirmed genuine fail-then-pass repro via
`frob ticket evidence --check-repro` (FAILED_AT_PARENT).

Must-fire: the bound test itself is the must-fire fixture (fails at
parent commit with the 2 undeclared fs.read sites, passes after this
fix).
Must-stay-quiet: re-ran the full TestRealGateGreen class
(test_repo_design_and_declarations_are_self_conformant AND
test_repo_unrestricted_scan_is_clean) -- both pass, 0 SYS100/SYS103
violations; the fix does not regress the coverage-totality scan.

Filed: none

Gates: frob check --ticket T-3430 clean.

### Changed
```
 tickets/T-3430/ticket.md | 4 +++-
 1 file changed, 3 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 12 error(s), 4186 warning(s), 857 waived
- error-findings: COV003@tickets/T-3410, DEPR006@frob-deprecated-baseline.lock.json, DOC006@docs/design/windows-portability.md, DOC006@tickets/T-3411/ticket.md, DOC006@tickets/T-3424/ticket.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, REL001@src/frob/__init__.py, SELFAUDIT001@design, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json, unresolved-attribute@tests/system/test_coverage_sigterm.py
