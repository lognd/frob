## Done report

Wired frob.release.dev_version_bump_enabled/dev_version_major_ack (T-4184) into a
real CLI consumer: `frob release status [path]`, a new direct-dispatch verb
(add_release_status_parser/run_release_status_command in src/frob/release/_cli.py,
wired via _dispatch_release_status in src/frob/__main__.py, mirroring `frob release
publish`'s own direct-dispatch shape). It reports the authoritative version, the
per-land dev-version-bump toggle/ack, and the release gate's own bump verdict (the
same diff_class/required_version/satisfies computation `frob release check` runs),
exiting 1 when the gate would refuse. Verified against current main: version reads
0.530.1.dev1, the toggle reads off (major ack: none), and the gate reports "since
0.530.1.dev1: major change -> need >= 0.531.0: BUMP REQUIRED" -- matching the
ticket's own measured premises.

Evidence: tests/test_release.py::TestRunReleaseStatusCommand::test_reports_bump_re\
quired_when_gate_refuses is a real fail-then-pass repro (FAILED_AT_PARENT confirmed
via `frob ticket evidence --check-repro --base-ref
1fdf1d8eb23179bc7f61874cd92c60fc0c19577f`, the test-only commit made before the
implementation commit). Plus TestRunReleaseStatusCommand::test_reports_ok_and_dev_b\
ump_toggle_state and TestAddReleaseStatusParser::test_registers_release_status.
Full `pytest tests/test_release.py tests/unit/test_main_entry.py`: 114 passed.

Filed: T-4310 (bug) -- discovered while widening scope: SCOPE002 is promoted to
error in frob.toml but is structurally unwaivable in this repo's per-ticket-
directory ledger (no real tickets.md exists for a frob:waive directive to bind to;
measured zero SCOPE002 WAIVE edges anywhere in the graph, including on tickets that
carry a documented-but-dead waiver block in their own ticket.md -- T-4298/T-1010/
T-4286/T-4013). Confirmed this predates T-4301's own work: the identical
tests/test_release.py requirement reproduces against the ORIGINAL declared scope
(src/frob/release/_cli.py alone), since its pre-existing run_release_publish_command
binding already points there.

Gates: `frob check --ticket T-4301` (and unscoped `frob check`) leave gate:SCOPE
failing on 8 SCOPE002 findings -- the direct, unavoidable consequence of the T-4310
defect above. Widened scope only to the two files this ticket actually touches
(src/frob/release/_cli.py, tests/test_release.py); declined to widen further into
src/frob/gates/__init__.py's own unrelated closure (docs/modules/gates.md, perf.md)
as disproportionate, same posture T-1010's own SCOPE002/COV001 waiver took for the
identical fan-out. COV001 on the two new public functions is waived in-code with the
same reasoning. Every OTHER gate family is clean for this diff (ruff-check, ty,
frob-cycle, frob-dup, gate:COV, gate:LANDPARITY, gate:DRIFT, gate:WAIVE, gate:TEST,
gate:REF all pass); the remaining unscoped FAILs (ruff-format on 2 unrelated files,
gate:ARCH on src/frob/graph/cache.py, gate:SELFAUDIT design:1, gate:TODO on
src/frob/gates/_land_format.py, gate:WIRE on tests/test_ci_workflow_timeout.py)
touch none of this ticket's 3 changed files -- confirmed pre-existing via `git diff
--name-only`.

### Changed
```
 src/frob/__main__.py     |  32 ++++++++++
 src/frob/release/_cli.py | 150 ++++++++++++++++++++++++++++++++++++++++++++---
 tests/test_release.py    |  96 ++++++++++++++++++++++++++++++
 tickets/T-4301/ticket.md | 137 ++++++++++++++++++++++++++++++++++++++++++-
 tickets/T-4310/ticket.md |  30 ++++++++++
 5 files changed, 434 insertions(+), 11 deletions(-)
```

### Evidence
- `tests/test_release.py::TestRunReleaseStatusCommand::test_reports_bump_required_when_gate_refuses` (pytest node id, verified passing when recorded)
- `tests/test_release.py::TestRunReleaseStatusCommand::test_reports_ok_and_dev_bump_toggle_state` (pytest node id, verified passing when recorded)
- `tests/test_release.py::TestAddReleaseStatusParser::test_registers_release_status` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 5 error(s), 4655 warning(s), 952 waived
- error-findings: ARCH103@src/frob/graph/cache.py, SCOPE002@tickets.md, SELFAUDIT001@design, TODO002@src/frob/gates/_land_format.py, WIRE002@tests/test_ci_workflow_timeout.py
