## Done report

Extract the T-3326 unscoped-fix refusal (the function's only I/O call,
sys.exit) out of _apply_tier_a_and_reverify into a new helper,
_refuse_unscoped_fix_pass, which owns that whole concern (both the
one decision point and the I/O call). Per T-3311's consolidating-split
lesson, an extraction only helps when it takes a whole concern with
it rather than just some branches -- here the parent no longer has
any I/O call at all, so ARCH103's mixed-concern-function check (which
requires I/O + string-formatting + >=2 decision points together in
ONE body) no longer fires on it, regardless of how many decision
points remain in the parent.

Measured before: gate reported 7 decision points at check_runner.py
line 1577 (mixed-concern-function, ARCH103). Measured after (cache
cleared, no REPLAY): `_apply_tier_a_and_reverify` no longer appears
anywhere in `frob check --only arch --json` output.

`frob test --base main` touched-set: 17/17 passed. Full-repo
`frob check --ticket T-3394` exceeded the available time budget under
heavy fleet contention (11+ concurrent checks); verified instead via
targeted `--only arch` (fresh cache) and `--only release` (confirms
this ticket's ARCH103 debt directive is gone from REL001's findings).

### Changed
```
 src/frob/app/check_runner.py | 41 +++++++++++++++++++++++++++++------------
 tickets/T-3394/ticket.md     |  7 ++++++-
 tickets/T-3397/ticket.md     |  2 +-
 3 files changed, 36 insertions(+), 14 deletions(-)
```

### Evidence
- `tests/test_check_runner.py::TestApplyTierAAndReverify::test_unscoped_fix_refuses_without_fix_all` (pytest node id, verified passing when recorded)
- `tests/test_check_runner.py::TestApplyTierAAndReverify::test_fix_all_still_runs_repo_wide_when_explicitly_requested` (pytest node id, verified passing when recorded)
- `tests/test_check_runner.py::TestApplyTierAAndReverify::test_doc007_finding_fixed_and_reverified_clean` (pytest node id, verified passing when recorded)
- `tests/test_check_runner.py::TestApplyTierAAndReverify::test_ticket_scoped_fix_never_touches_files_outside_declared_scope` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 21 error(s), 3994 warning(s), 897 waived
- error-findings: AFFECT001@src/frob/app/check_runner.py, CYCLE001@src/frob/__init__.py, DEPR006@frob-deprecated-baseline.lock.json, DOC003@docs/commands/sys.md, DOC011@docs/modules/tickets.md, LEXCHECK001@src/frob/gates/_comment_placement.py, OPAQUE001@tests/unit/test_land_finish_idempotent.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, REL001@src/frob/__init__.py, REL001@src/frob/__main__.py, REL001@src/frob/app/ticket_runner/_land_cmd.py, REL001@src/frob/process/_reap.py, REL001@src/frob/stats/_agentic.py, REL001@strata-core/src/graph/vmodel.rs, REL001@strata-core/src/parse/grammar_core.rs, REL001@tests/unit/test_conftest_suite_result_status.py, SELFAUDIT001@design, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
