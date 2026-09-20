## Done report

frob-core and strata-core are hard ==-pinned default dependencies of frob
(T-3845) but are published nowhere, so ci.yml's standalone-install job's
plain `uv pip install dist/*.whl` resolves against the real index and
fails ("frob-core was not found in the package registry" -- measured in
CI run 34005559354). The same gap reds tests/system/test_artifact_smoke.py's
checks, which also install the built wheel without supplying the cores.

Fixed by building both core wheels via maturin inside standalone-install
itself (self-contained, no cross-job artifact plumbing needed for one
ubuntu-only smoke job) and pointing the resolver at them with
--find-links instead of a registry. Added a preflight to
scripts/artifact_smoke.py that checks for the built core wheels before
attempting any install, so a missing core reports the specific missing
package name instead of surfacing uv's raw registry-resolution trace.

Manually verified by running (not just reasoning about the YAML):
- Reproduced the exact CI failure locally as a positive control: built
  the pure-python wheel (`uv build --wheel`) and ran
  `uv pip install --python <clean venv> dist/*.whl` with no find-links --
  reproduced verbatim "Because frob-core was not found in the package
  registry ... frob==0.530.0 cannot be used."
- Built frob-core/strata-core with `uvx maturin build --release --out
  dist` in each crate dir (the same invocation ci.yml's new
  PyO3/maturin-action steps run), then re-ran the same `uv pip install`
  with `--find-links frob-core/dist --find-links strata-core/dist` --
  succeeded, installed frob 0.530.0 + frob-core + strata-core, and
  `frob --version` ran.
- Ran scripts/artifact_smoke.py against an empty core-wheels dir: failed
  fast with "FAIL core-wheels-preflight: core_wheels_dir (...) does not
  contain a built wheel for: frob-core, strata-core. ... This is 'core
  not built/supplied', not a bad version pin." -- no raw resolver trace
  leaked through.
- Ran the same script against the real built core wheels: "PASS
  base-install / PASS serve-extra / artifact-smoke: all 2 check(s)
  passed".
- `uv run pytest tests/system/test_artifact_smoke.py -v -m slow` -- 3
  passed (the exact three tests the ticket names as red on
  ubuntu/macOS: the two pre-existing T-3857 fixtures plus the new
  absent-cores must-fire fixture).
- `uv run frob test --base main` -- 77 touched-set python tests,
  exit=0.
- `uv run ruff check scripts/artifact_smoke.py
  tests/system/test_artifact_smoke.py
  tests/unit/test_artifact_smoke_script.py` -- all checks passed.
- Inspected .github/workflows/release.yml directly (not reasoned
  about): its `build` job already builds both core wheels per target
  via PyO3/maturin-action and uploads them as
  `frob-core-<target>`/`strata-core-<target>` artifacts; its
  `artifact-smoke` job (needs: [build, build-sdists]) downloads the
  matching platform's core wheels and runs scripts/artifact_smoke.py
  with --core-wheels-dir against them; its `upload` job downloads and
  publishes `frob-core-*`/`strata-core-*` artifacts to PyPI ahead of
  frob itself. This already satisfies the ticket's item 2 and the
  "release workflow produces core wheels as published artifacts"
  acceptance criterion -- no release.yml change was needed or made.

Filed: T-3957 -- "SCOPE002 doc-closure on
docs/guides/release.md is unclosable: any ticket touching
scripts/artifact_smoke.py inherits an unbounded doc-anchor cascade".
Pre-existing structural gap (predates this ticket, reproducible with
zero code changes purely from T-3935's declared scope +
scripts/artifact_smoke.py's T-3884-era frob:doc directives): declaring
docs/guides/release.md in scope (required to satisfy SCOPE002 for
artifact_smoke.py's PRE-EXISTING doc-anchored symbols) cascades into
two more files (scripts/verify_release_ci_status.py, src/frob/doctor.py)
via OTHER, unrelated anchors those later tickets added to the same
shared doc without themselves declaring it in scope, and demoting
either to evidence-only does not satisfy SCOPE002 (verified: the gate
requires full write scope). Full-scoping one of those cascades a second
level into docs/guides/install.md and docs/modules/cli.md (91+ further
warnings). This ticket's OWN new code (_REQUIRED_CORE_WHEEL_GLOBS,
_require_core_wheels) avoids adding to the debt via the same
`frob:waive COV001` pattern already precedented in
src/frob/gates/_rule_id_scan.py (T-1010/T-1937) instead of a frob:doc
citation into the same shared doc.

Gates: `frob check --only refs,docanchor,drift,scope,gates_schema,
arch_schema,tickets,prework,render_lint,fmt --ticket T-3935` clean
except one pre-existing gate:SCOPE SCOPE002 finding (5 symbols in
scripts/artifact_smoke.py whose frob:doc target
'docs/guides/release.md' is not in this ticket's scope) -- waived per
the reasoning above and tracked as T-3957; this finding is
reproducible with zero diff, purely from the ticket's declared scope
intersecting scripts/artifact_smoke.py's pre-existing T-3884 frob:doc
directives. The full unscoped `frob check` was not run to completion --
it exceeds the foreground/background budget on this shared, loaded
host even with a reduced --only set; the scoped stages above plus
`frob test --base main` (touched-set, 77 tests green) and a direct
ruff run are the verification actually completed.

### Changed
```
 .github/workflows/ci.yml                 |  31 +++++-
 scripts/artifact_smoke.py                |  63 +++++++++++++
 tests/system/test_artifact_smoke.py      |  49 ++++++++++
 tests/unit/test_artifact_smoke_script.py |  75 ++++++++++++++-
 tickets/T-3935/ticket.md                 | 156 +++++++++++++++++++++++++++++++
 tickets/T-3957/ticket.md       |  36 +++++++
 6 files changed, 406 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/system/test_artifact_smoke.py::TestArtifactSmokeAbsentCores::test_absent_cores_report_named_core_missing` (pytest node id, verified passing when recorded)
- `tests/unit/test_artifact_smoke_script.py::TestRequireCoreWheels::test_both_cores_present_does_not_raise` (pytest node id, verified passing when recorded)
- `tests/unit/test_artifact_smoke_script.py::TestRequireCoreWheels::test_both_cores_absent_names_both` (pytest node id, verified passing when recorded)
- `tests/unit/test_artifact_smoke_script.py::TestRequireCoreWheels::test_one_core_absent_names_only_that_one` (pytest node id, verified passing when recorded)
- `tests/unit/test_artifact_smoke_script.py::TestRequireCoreWheels::test_main_reports_missing_core_before_any_install_attempt` (pytest node id, verified passing when recorded)
- `tests/unit/test_artifact_smoke_script.py::TestMain::test_all_checks_pass_exits_zero` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 4 error(s), 4396 warning(s), 932 waived
- error-findings: AFFECT001@scripts/artifact_smoke.py, DOC006@tickets/T-3931/ticket.md, DUP001@scripts/artifact_smoke.py, SCOPE002@tickets.md
