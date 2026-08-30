## Done report

test_seccomp's golden diff was a pure addition of syscalls (chmod, mkdir, pwrite64, rename, truncate, unlink, clone, execve, execveat, fork, vfork), no removals or reordering elsewhere. git log on design/frob.strata/src/frob/strata/_export.py shows 4 recent legitimate lands (T-3409, T-3416, T-3429, T-3430) that added SYS100 exec/fs.write/fs.read/env.read capability declarations for the testsuite, process/_reap split, and stats/_agentic split -- each widening the syscall set export_seccomp renders. The exporter and model are both correct; the golden fixture (tests/golden/frob_export_seccomp.json) was simply never regenerated after those lands. Regenerated it directly from a fresh export_seccomp(elaborate(parse_module(design/frob.strata))) call (confirmed byte-identical to two successive in-process renders, matching the test's own determinism assertion) and verified the diff against the old golden contains only the syscall additions attributable to those 4 capability-declaration commits, nothing else.

### Changed
```
 tests/golden/frob_export_seccomp.json | 11 +++++++++++
 tickets/T-3446/ticket.md              |  4 +++-
 2 files changed, 14 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/strata/test_export_golden.py::TestExportGolden::test_seccomp` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 11 error(s), 3969 warning(s), 855 waived
- error-findings: COV001@src/frob/tickets/_scope.py, COV003@tickets/T-3410, DEPR006@frob-deprecated-baseline.lock.json, DOC006@tickets/T-3411/ticket.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/tickets/_scope.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, REL001@src/frob/__init__.py, SELFAUDIT001@design, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
