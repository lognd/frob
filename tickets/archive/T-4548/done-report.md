## Done report

T-3613's lease on src/frob/app/config.py is gone (landed at 42bbe4c2b), so
this ticket picked up the config.py residue T-4535 deferred.

SEC110 on the FROB_ROOT environment read in _pyproject_file_for_args:
added a frob:waive SEC110 directive right above the os.environ.get(
"FROB_ROOT") call, same reasoning as the existing FROB_AGENT/FROB_WORKTREE
waivers in src/frob/tickets/_worktree_guard.py -- FROB_ROOT is a
worktree-root path marker (T-4502), never a secret.

COV002 on the changed symbols: already satisfied. _pyproject_file_for_args
already carries frob:ticket T-4502 and four frob:tests edges to
tests/unit/test_app_config_pyproject_root_t_draft_1f1ae69b.py -- no new
directive needed once measured with --ticket/--base dev.

ARCH103 per its remedy text: does not fire on this file. frob check
--only arch --ticket T-4548 --base dev --files
src/frob/app/config.py --files src/frob/__main__.py reports "pass
frob-arch 19 warnings (36 waived), 537 suggestions" -- no ARCH103 hit on
either owned file.

Verified: frob check --only coverage --only drift --only affect_drift
--only clones --ticket T-4548 --base dev --files
src/frob/app/config.py --files src/frob/__main__.py reports 0 errors for
these files (the 5 errors in that run's full output are unrelated
T-4531/T-4515 residue on src/frob/excludes.py and
src/frob/lang/_project_detect.py that dev has not yet absorbed T-4531's
fix for -- not this ticket's files).

BUG002 waived per ticket body (gate/doc-metadata defect, not application
code a pytest repro can exercise).

ruff check/format: 0 errors on touched files (the one pre-existing
ruff-format warning is tests/test_tickets_triage_dates.py, untouched by
this ticket). claude-config-drift: pass.

Serial pytest (no xdist), all 4 collected, 0 failed:
  PYTHONPATH=<WT>/src python -m pytest -q -p no:cacheprovider -p no:xdist \
    tests/unit/test_app_config_pyproject_root_t_draft_1f1ae69b.py

2 pytest node ids bound as evidence for acceptance criterion [1]:
  tests/unit/test_app_config_pyproject_root_t_draft_1f1ae69b.py::TestPyprojectFileForArgs::test_explicit_ticket_path_wins_over_cwd
  tests/unit/test_app_config_pyproject_root_t_draft_1f1ae69b.py::TestPyprojectFileForArgs::test_frob_root_env_wins_over_cwd_when_no_explicit_path

### Changed
```
 src/frob/app/config.py | 1 +
 1 file changed, 1 insertion(+)
```

### Evidence
- `tests/unit/test_app_config_pyproject_root_t_draft_1f1ae69b.py::TestPyprojectFileForArgs::test_explicit_ticket_path_wins_over_cwd` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_config_pyproject_root_t_draft_1f1ae69b.py::TestPyprojectFileForArgs::test_frob_root_env_wins_over_cwd_when_no_explicit_path` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 21 error(s), 4943 warning(s), 977 waived
- error-findings: ARCH103@src/frob/app/config.py, ARCH103@src/frob/doctor.py, CROSSTICKET001@design/frob.strata, CROSSTICKET001@docs/commands/check.md, CROSSTICKET001@docs/design/registry/capability-via-ratchet.lock.json, CROSSTICKET001@docs/modules/app.md, CROSSTICKET001@docs/modules/lang.md, CROSSTICKET001@docs/modules/tickets-landing.md, CROSSTICKET001@src/frob/_cli_parsers/_check.py, CROSSTICKET001@src/frob/_cli_parsers/_ticket/_progress.py, CROSSTICKET001@src/frob/app/_config_external.py, CROSSTICKET001@src/frob/app/check_runner.py, CROSSTICKET001@src/frob/app/ticket_runner/_land_cmd.py, CROSSTICKET001@src/frob/app/ticket_runner/_verify.py, CROSSTICKET001@src/frob/dup/_legacy_cs.py, CROSSTICKET001@src/frob/gates/__init__.py, MILE001@tickets.md, PERF004@src/frob/doctor.py, REF002@src/frob/vet/_capability_registry/_dotnet_bcl.py, WIRE002@src/frob/dup/_legacy_cs.py, invalid-argument-type@tests/unit/test_ticket_runner_land_cmd_flags.py
