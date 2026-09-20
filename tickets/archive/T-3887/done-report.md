## Done report

PARTIAL: this lands the shared mechanism (frob.process._project_tool)
and its regrowth guard (BARETOOL001), the piece of T-3887 that is one
root cause with T-4125. It does NOT close the rest of T-3887's ask.

DONE here: project_tool_argv/resolve_project_tool route every Python
toolchain spawn this session touched (frob.check._python's ruff/ty call
sites, frob.app.pyfmt_runner's four ruff call sites, frob.app.
ticket_runner._land_cmd's touched-set ty/ruff pre-land checks) through
the project's own uv-managed environment instead of a bare PATH lookup
-- closing the exact defect class T-3887's F-017 (bare pytest spawn in
frob's own environment) and F-012 (parser import from frob's own
interpreter) describe, demonstrated concretely against `ty`/`ruff`
rather than `pytest` specifically.

frob.gates._bare_toolchain.bare_toolchain_gate (BARETOOL001) is the
regrowth guard T-3887's "wants a gate of its own" line asked for --
implemented, unit-tested (10 tests, both the finder and the gate
wiring), but NOT YET registered in frob.gates' job registry
(src/frob/gates/__init__.py:_build_process_jobs) because that file is
under T-4124's live lease for this entire session. Filed T-4146 to wire
the one-line registration once that lease frees.

NOT DONE, filed as follow-ups rather than silently dropped:
- F-012's actual FLAGCOV001 parser-import site (imports the target
  project's parser from frob's own interpreter) is untouched -- routing
  an import (not a subprocess spawn) through the project's own
  interpreter needs a different mechanism than project_tool_argv
  (which only covers spawns). Filed T-4147.
- F-017/F-018: frob.testing._coverage_refresh's own pytest spawn and
  its pytest-xdist presence assumption were not audited or routed in
  this session -- frob.process._pytest_spawn already exists per this
  module's docstring reference and may already cover part of this;
  needs its own enumeration pass. Filed T-4148.
- The "no [[test.runner]] declared" policy decision (refuse vs. loud
  fallback) is undecided. Filed T-4149.
- Off-repo verification (a non-frob project fixture proving the parser/
  pytest spawn now resolve correctly outside this repo) was not built.
  Folded into T-4147/T-4148's own acceptance.

Every consumer-reported instance of "bare toolchain name resolves the
wrong environment" that this session actually touched (ty, ruff) is
fixed and gated against regrowth; the pytest/parser-import instances
named in T-3887's own body are real, separate, and now tracked as their
own tickets rather than left implicit in a closed T-3887.

### Changed
```
 docs/modules/process.md                 |  55 ++++++++++
 src/frob/app/pyfmt_runner.py            |  15 ++-
 src/frob/app/ticket_runner/_land_cmd.py |  77 +++++++++++---
 src/frob/check/_python.py               |  46 ++++----
 src/frob/gates/_bare_toolchain.py       | 104 ++++++++++++++++++
 src/frob/process/_project_tool.py       | 180 ++++++++++++++++++++++++++++++++
 src/frob/vet/_bare_toolchain.py         | 111 ++++++++++++++++++++
 tests/unit/test_check.py                |  55 +++++-----
 tests/unit/test_project_tool.py         | 123 ++++++++++++++++++++++
 tests/unit/vet/test_bare_toolchain.py   | 109 +++++++++++++++++++
 tickets/T-3887/ticket.md                | 118 ++++++++++++++++++++-
 tickets/T-4125/done-report.md           |  72 +++++++++++++
 tickets/T-4125/ticket.md                |  38 ++++++-
 tickets/T-4146/ticket.md                |  29 +++++
 tickets/T-4147/ticket.md                |  27 +++++
 tickets/T-4148/ticket.md                |  27 +++++
 tickets/T-4149/ticket.md                |  27 +++++
 17 files changed, 1145 insertions(+), 68 deletions(-)
```

### Evidence
- `tests/unit/test_project_tool.py::TestResolveProjectTool::test_ok_resolves_path_and_version` (pytest node id, verified passing when recorded)
- `tests/unit/vet/test_bare_toolchain.py::TestBareToolchainFindings::test_clean_on_project_tool_argv_spelling` (pytest node id, verified passing when recorded)
- `tests/unit/vet/test_bare_toolchain.py::TestBareToolchainGate::test_clean_on_project_tool_argv_spelling` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 27 error(s), 4470 warning(s), 934 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@src/frob/gates/_bare_toolchain.py, COV001@src/frob/process/_project_tool.py, COV001@src/frob/vet/_bare_toolchain.py, COV003@tests/unit/test_check.py, CROSSTICKET001@src/frob/app/ticket_runner/_land_cmd.py, DOC002@src/frob/gates/_bare_toolchain.py, DOC002@src/frob/vet/_bare_toolchain.py, DRIFT002@src/frob/check/_python.py, DUP001@src/frob/app/ticket_runner/_land_cmd.py, FMT001@src/frob/gates/_bare_toolchain.py, FMT001@src/frob/process/_project_tool.py, FMT001@src/frob/vet/_bare_toolchain.py, LARGE001@src/frob/_cli_parsers/_ticket/_closeout.py, PRE001@tickets/T-3887, REF001@.github/ISSUE_TEMPLATE/config.yml, REF002@.github/ISSUE_TEMPLATE/bug_report.yml, REF002@.github/ISSUE_TEMPLATE/feature_request.yml, REF002@.github/PULL_REQUEST_TEMPLATE.md, REF002@CODE_OF_CONDUCT.md, REF002@CONTRIBUTING.md, REF002@SECURITY.md, SCOPE002@tickets.md, SELFAUDIT001@src/frob/vet/_bare_toolchain.py, SELFAUDIT001@tests/unit/test_project_tool.py, SELFAUDIT001@tests/unit/vet/test_bare_toolchain.py, WIRE001@src/frob/gates/_bare_toolchain.py
