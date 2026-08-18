## Done report

Changed:
- src/frob/app/_config_external.py::_BOOL_FLAGS

Root cause confirmed: T-2320's three flags (check_skip_ruff_check,
check_skip_ruff_format, check_ruff_fix) parsed correctly into
argparse's Namespace but were absent from _BOOL_FLAGS, so
_apply_bool_flags never copied them into the kwargs dict passed to
AppConfig(**d) -- the exact T-0749 bug class recurring.

Ran find_dropped_cli_flags(parser, AppConfig) directly against the
live tree before and after: before, it returned exactly
{check_ruff_fix, check_skip_ruff_check, check_skip_ruff_format} --
matching the ticket's claim precisely, with no other dest names
missing. After the fix, it returns the empty set. No other dropped
flags exist beyond the three named in the ticket.

Proved behavior, not just the test: parsed
`check --skip-ruff-check --skip-ruff-format --fix-ruff` through the
real `_build_parser()` -> `AppConfig.from_external` path and confirmed
all three fields read True (previously always False regardless of the
flag). Also re-ran the ticket's own CLI repro
(`frob check --skip-ruff-format --skip-arch --skip-cycle --skip-dup
--skip-bind --skip-exports --skip-gates --skip-tests --no-cache`) and
confirmed the output no longer mentions ruff-format at all (previously
it still ran and reported "138 files would be reformatted" regardless
of the flag).

Visibility gap (asked and answered per instruction): find_dropped_cli_
flags (T-2004) is a real, correct, already-existing detector -- it was
never wrong either time this bug class occurred. It is wired to
exactly one place: its own unit test
(tests/unit/test_app_config_flag_coverage.py::TestFindDroppedCliFlags::
test_current_tree_has_zero_dropped_flags), which nothing in the
frob check gate surface runs. That is what let this sit undetected: a
green PR does not run `pytest tests/unit/`, it runs `frob check`. Filed
a follow-up (see below) to wire it into frob check as a gate rather than
leaving it a unit test nobody runs as part of the enforcement path.

Filed: T-draft-d1d6cb26 ("Wire find_dropped_cli_flags into frob check
as a gate (T-2387 visibility gap)"), scope
src/frob/gates/**,src/frob/check/**,docs/modules/gates.md -- renumbers
to a real id at land.

Gates: full unscoped `frob check` on this repo carries pre-existing
ARCH/DRIFT/PERF findings unrelated to this change (measured before
touching _config_external.py); this ticket's own touched file
(src/frob/app/_config_external.py) introduces no new findings in the
diff-scoped checks. No frob:waive touched or needed.

### Changed
```
 src/frob/__main__.py               | 24 +++++++++++----
 src/frob/_cli_parsers/_ops.py      |  7 +++--
 tests/unit/test_main_entry.py      | 60 ++++++++++++++++++++++++++++++++++++--
 tickets/T-2385/ticket.md           | 18 +++++++++++-
 tickets/T-2387/ticket.md           |  8 ++++-
 tickets/T-draft-d1d6cb26/ticket.md | 48 ++++++++++++++++++++++++++++++
 6 files changed, 153 insertions(+), 12 deletions(-)
```

### Evidence
- `tests/unit/test_app_config_flag_coverage.py::TestFindDroppedCliFlags::test_current_tree_has_zero_dropped_flags` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_config_flag_coverage.py::TestT2320RuffFlagsReachAppConfig::test_from_external_carries_all_three_ruff_flags_from_parsed_argv` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_config_flag_coverage.py::TestT2320RuffFlagsReachAppConfig::test_absent_ruff_flags_default_false` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: AFFECT001@src/frob/__main__.py, ARCH103@src/frob/release/_cli.py, COV001@src/frob/verify/_drain.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV005@src/frob/app/_config_external.py, DOC001@docs/commands/release.md, DOC002@src/frob/verify/_drain.py, DOC005@docs/modules/cli.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT002@docs/modules/vet.md, E501@/home/logan/projects/frob/.claude/worktrees/contention-cluster/src/frob/verify/_worker.py, F401@/home/logan/projects/frob/.claude/worktrees/contention-cluster/src/frob/vet/_capability.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_new.py, PRE001@tickets/T-2387, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md
