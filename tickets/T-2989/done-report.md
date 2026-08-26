## Done report

Rename performed via `frob refactor move-module frob.yaml_io frob.yamlio` (the new T-2990 verb), not by hand -- exact command run:

    uv run frob refactor move-module frob.yaml_io frob.yamlio

The tool: git-mv'd src/frob/yaml_io.py -> src/frob/yamlio.py (rename detected, blame/history preserved), rewrote 8 Python import-form references (frob:tests-bound module_scan_python tests cover these forms) and 52 non-Python citations (frob.toml-shaped dotted strings, design/frob.strata code= globs, ticket path citations across 8 archived tickets and the T-2990 ticket itself, docs prose), applied and WIP-committed in one transaction.

The tool's own Verify phase crashed mid-run: `frob check --delta`'s subprocess timed out after 100s and `guarded_subprocess_run` (src/frob/process/_guard.py) does not catch `subprocess.TimeoutExpired`, so the exception propagated uncaught through the CLI instead of surfacing as an `Err`/failed VerifyOutcome. This is a pre-existing bug shared by every `guarded_subprocess_run` caller, outside T-2989's/T-2990's declared scope (src/frob/process/_guard.py) -- filed as a new ticket rather than fixed here or silently worked around; see Filed below. The WIP commit itself (the actual rename + rewrites) was already made before the crash and was independently verified correct by hand below.

Residue handled deliberately, per the ticket's own instruction:
- `_coverage_tracer_active` traveled with the module (module-private, moved automatically by move-module's git-mv, not left behind).
- yaml_io.py holds nothing -- it no longer exists (git-mv'd away entirely).
- No re-export shim left -- 40 in-repo references (grown from the ticket's originally-measured 21 since T-2990 landed with its own docs/tests, all touched by move-module too), no external consumers.
- `__all__` in yamlio.py already reads `["fast_yaml_loader"]` -- no module-name entry to update.
- move-module's own text scan deliberately never touches `.py` docstrings (T-2990's must-NOT-fire guard: a docstring's own prose is not touched by the module-move verb's automated reach) -- 4 genuine docstring/comment citations of the old dotted path plus one doc-anchor slug survived the automated pass and were hand-fixed as declared residue (`src/frob/tickets/_store.py` x2 docstrings, `src/frob/derived_state.py` x1 comment, `docs/modules/tickets-data-storage.md` x1 code-fence comment, `src/frob/yamlio.py` x1 `frob:doc` anchor slug that referenced the OLD heading text's auto-generated id -- the heading prose itself WAS rewritten by the tool since it spelled the dotted path literally).

VERIFY, per the ticket's own instructions:
- `git grep -c "yaml_io"` over src/, tests/, docs/: 0 (confirmed after both the tool's automated pass and the hand-fixed residue above).
- `frob check --only docanchor`: zero findings on tickets-data-storage.md/yamlio.py (the anchor slug fix above resolves cleanly).
- `frob check --only coverage --only arch --only dup --ticket T-2989`: zero findings on any touched file.
- Runtime import exercised through a real call path (not just text rewrite): `from frob.yamlio import fast_yaml_loader; fast_yaml_loader()` returns `yaml.CSafeLoader` and `yaml.load("a: 1\nb: 2\n", Loader=loader)` parses correctly.
- `tests/unit/test_ticket_store.py` (100 tests) and `tests/unit/perf/test_hotpath_smells.py` (16 tests) both pass unchanged.

Filed: T-3015 (renumbers at land) for `guarded_subprocess_run`'s uncaught `subprocess.TimeoutExpired` on any timeout-bounded call (src/frob/process/_guard.py) -- discovered when `frob refactor move-module`'s own Verify phase crashed the whole CLI process instead of returning a failed VerifyOutcome, mid-transaction, with the WIP commit already made. Every caller passing `timeout=` (verify_check_delta/verify_pytest_collect in frob.refactor, and every other `frob.check` tool runner) is exposed to the identical crash-instead-of-Err failure mode. Out of both T-2989's and T-2990's declared scope (src/frob/process/_guard.py).

Gates: ruff-check/ruff-format clean on every touched file (pre-existing repo-wide `ruff format` drift on src/frob/tickets/_store.py predates this ticket, confirmed via the same file already appearing in the pre-ticket drift list). `git diff main --diff-filter=D` shows only the expected renamed-away yaml_io.py (git rename detection, not a plain delete).

### Changed
```
 design/frob.strata                       |  6 +--
 docs/commands/refactor.md                |  8 ++--
 docs/modules/tickets-data-storage.md     | 14 +++---
 src/frob/__init__.py                     |  2 +-
 src/frob/derived_state.py                |  2 +-
 src/frob/gates/_fmt_directives.py        |  2 +-
 src/frob/gates/decisions.py              |  2 +-
 src/frob/gates/invariants.py             |  2 +-
 src/frob/refactor/_module_prose.py       |  4 +-
 src/frob/refactor/_module_scan_python.py | 10 ++---
 src/frob/registry/_models.py             |  2 +-
 src/frob/tickets/_store.py               |  8 ++--
 src/frob/vet/_lockfile.py                |  2 +-
 src/frob/{yaml_io.py => yamlio.py}       |  2 +-
 tests/test_refactor.py                   | 18 ++++----
 tests/unit/perf/test_hotpath_smells.py   |  4 +-
 tickets/T-2989/ticket.md                 |  7 +++
 tickets/T-2990/done-report.md            |  2 +-
 tickets/T-2990/ticket.md                 | 16 +++----
 tickets/T-3015/ticket.md       | 74 ++++++++++++++++++++++++++++++++
 tickets/archive/T-1204/done-report.md    |  6 +--
 tickets/archive/T-1485/done-report.md    |  2 +-
 tickets/archive/T-1644/ticket.md         | 10 ++---
 tickets/archive/T-1647/ticket.md         |  4 +-
 tickets/archive/T-1780/ticket.md         |  6 +--
 tickets/archive/T-1892/ticket.md         |  4 +-
 tickets/archive/T-2380/done-report.md    |  2 +-
 tickets/archive/T-2403/ticket.md         |  4 +-
 28 files changed, 153 insertions(+), 72 deletions(-)
```

### Evidence
- `tests/unit/test_ticket_store.py::TestYamlLoader::test_prefers_csafeloader_when_libyaml_present` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_store.py::TestYamlLoader::test_falls_back_to_safeloader_without_libyaml` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_store.py::TestYamlLoader::test_detects_coverage_tracer_by_module_name` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_store.py::TestYamlLoader::test_no_active_tracer_is_not_coverage` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_store.py::TestYamlLoader::test_falls_back_to_safeloader_under_active_coverage_tracer` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_hotpath_smells.py::TestPerf010YamlCLoader::test_does_not_fire_on_helper_loader_indirection` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 47 error(s), 1153 warning(s), 858 waived
- error-findings: ARCH103@src/frob/tickets/_new_renumber.py, COV001@scripts/branch_stranded_work_analysis.py, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-2989/ticket.md, DOC006@tickets/T-2993/ticket.md, DOC006@tickets/T-2996/ticket.md, DOC006@tickets/T-3015/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DUP001@tests/unit/perf/test_hotpath_smells.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/stats/_agentic.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-2989, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SELFAUDIT001@design, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_ghio.py, TEST001@scripts/branch_stranded_work_analysis.py, TICK004@tickets.md, TICK011@tickets.md
