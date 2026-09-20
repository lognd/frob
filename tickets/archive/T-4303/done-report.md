## Done report

Fixed WIRE001's blind spot for the AppConfig-bypass direct-dispatch verbs
(bind/agent/worktree/sync-skills/whereis): every --help-only dest their own
_add_*_parser function registers is now exempt, resolved by AST span
(_appconfig_bypass_parser_line_ranges) against a named function set
(_WIRE001_APPCONFIG_BYPASS_PARSER_FUNCS in src/frob/gates/_wire.py) rather
than a raw dest-name list, so the exemption is scoped precisely to those
functions' own bodies and cannot silence an unrelated dest elsewhere in the
same file. Discharged whereis's own T-4299 waiver (src/frob/_cli_parsers/
_core.py) now that WIRE001 no longer needs it -- verified with `frob check
--only wire` against the real diff, not just the synthetic unit tests: zero
WIRE001 findings for whereis_json anywhere.

Did not add a "single boolean" exemption keyed on file path alone (e.g.
skip all of src/frob/_cli_parsers/_core.py) -- that would also silence a
genuinely new, real wiring gap landing in the same file next to a bypass
verb's own parser. The AST-scoped function-body check is the smallest fix
that stays precise; verified via a second test
(test_new_cli_dest_outside_appconfig_bypass_parser_func_still_flagged)
that an unrelated dest in the SAME file, outside any bypass-verb function,
still fires.

Evidence: tests/gates_suite/test_wire.py::TestWireGate::test_new_cli_dest_i\
nside_appconfig_bypass_parser_func_is_not_flagged is a real fail-then-pass
repro (FAILED_AT_PARENT confirmed via `frob ticket evidence --check-repro
--base-ref d1e71a274ff595ef270575c05c15dbc8f6f209a9`, the test-only commit
made before the fix commit). Plus
test_new_cli_dest_outside_appconfig_bypass_parser_func_still_flagged. Full
`pytest tests/gates_suite/test_wire.py tests/unit/test_main_entry.py`:
96 passed.

Gates: `frob check --ticket T-4303` (and unscoped `frob check`) both leave
gate:SCOPE failing on the same structural SCOPE002 defect T-4301 already
filed as T-4310 (SCOPE002 is unwaivable in this repo's per-ticket-directory
ledger); widened scope only to the three files actually touched
(src/frob/gates/_wire.py, src/frob/_cli_parsers/_core.py,
tests/gates_suite/test_wire.py -- the last two needed to discharge the
whereis waiver, which is what T-4303's own follow_up existed to do).
gate:WIRE itself is clean. The remaining unscoped FAILs (gate:ARCH on
src/frob/graph/cache.py, gate:TODO on src/frob/gates/_land_format.py) touch
none of this ticket's changed files -- confirmed pre-existing via `git diff
--name-only`.

### Changed
```
 src/frob/_cli_parsers/_core.py | 12 +++----
 src/frob/gates/_wire.py        | 74 +++++++++++++++++++++++++++++++++++++++++-
 tests/gates_suite/test_wire.py | 67 ++++++++++++++++++++++++++++++++++++++
 tickets/T-4303/ticket.md       | 17 ++++++++++
 4 files changed, 161 insertions(+), 9 deletions(-)
```

### Evidence
- `tests/gates_suite/test_wire.py::TestWireGate::test_new_cli_dest_inside_appconfig_bypass_parser_func_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/gates_suite/test_wire.py::TestWireGate::test_new_cli_dest_outside_appconfig_bypass_parser_func_still_flagged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 3 error(s), 4680 warning(s), 951 waived
- error-findings: ARCH103@src/frob/graph/cache.py, SCOPE002@tickets.md, TODO002@src/frob/gates/_land_format.py
