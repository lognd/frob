## Done report

T-3400: trimmed shared python Makefile.j2 and docs to match frob-is-the-interface direction; see scaffold.md/README.md.j2 diffs. Evidence: scaffold pytest suite (27 passed).

### Changed
```
 docs/commands/scaffold.md                         |  2 +-
 src/frob/scaffold/data/shared/python/Makefile.j2  | 53 ++++++++---------------
 src/frob/scaffold/data/shared/python/README.md.j2 | 17 +++++---
 tickets/T-3400/ticket.md                          |  5 ++-
 4 files changed, 33 insertions(+), 44 deletions(-)
```

### Evidence
- `cmd:pytest tests/unit/test_scaffold_project.py tests/unit/test_scaffold_managed.py tests/system/test_scaffold_dx.py -q exit=0 sha256=f6f0a5c777f7` (cmd evidence, exit=0)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 22 error(s), 3986 warning(s), 897 waived
- error-findings: CYCLE001@src/frob/__init__.py, DEPR006@frob-deprecated-baseline.lock.json, DOC003@docs/commands/sys.md, DOC006@tickets/T-1382/ticket.md, DOC011@docs/modules/tickets.md, LEXCHECK001@src/frob/gates/_comment_placement.py, OPAQUE001@tests/unit/test_land_finish_idempotent.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, REL001@src/frob/__init__.py, REL001@src/frob/__main__.py, REL001@src/frob/app/check_runner.py, REL001@src/frob/app/ticket_runner/_land_cmd.py, REL001@src/frob/process/_reap.py, REL001@src/frob/stats/_agentic.py, REL001@strata-core/src/graph/vmodel.rs, REL001@strata-core/src/parse/grammar_core.rs, REL001@tests/unit/test_conftest_suite_result_status.py, SELFAUDIT001@design, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
