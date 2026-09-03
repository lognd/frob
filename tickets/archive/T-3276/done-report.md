## Done report

Built the doctor.py side of the owner's directive within this ticket's
declared scope (src/frob/doctor.py):

- `ToolCategory` (REQUIRED / OPTIONAL / OPTIONAL_FOR_GATE) states the rule
  the owner gave: required-missing -> loud typed failure naming the tool
  and install command; optional-and-unused -> silent; optional-but-needed-
  for-a-gate -> that gate reports UNMEASURED, never CLEAN.
- `ExternalToolStatus` + `_EXTERNAL_TOOLS`: the stated inventory of every
  tool frob spawns or depends on for a gate to measure something --
  python/git/uv/ruff/ty (REQUIRED), pytest/pytest-xdist/pytest-cov
  (OPTIONAL_FOR_GATE -- this is the xdist/coverage category the owner
  called out specifically), cargo/npm/ctest (OPTIONAL, per-language).
- `scan_external_tools()`: probes binaries via shutil.which + a best-
  effort --version spawn, and Python plugins (pytest-xdist, pytest-cov --
  these are pytest PLUGINS loaded in-process, never separate binaries)
  via importlib.metadata.version. Never raises.
- `_external_tools_remediation()`: one line per missing REQUIRED tool,
  naming the tool and its install command; silent for OPTIONAL/
  OPTIONAL_FOR_GATE absences, per the category rule.
- Wired into DoctorReport/`_assemble_doctor_report`/`_log_doctor_
  diagnosis`/`run_diagnosis`: `frob doctor` now enumerates and reports
  every tool it can spawn with present/absent/version (build item 4), and
  a missing REQUIRED tool makes the overall report unhealthy with a named
  remediation line (build item 2's loud-typed-failure half, at the
  doctor-report layer).

VERIFIED all three fixtures against the real code (not simulated):
- MUST-FIRE: `test_missing_binary_reports_absent_with_install_hint` /
  `test_missing_package_reports_absent` / `test_missing_required_tool_
  names_it_and_the_install_command` -- a missing tool reports absent with
  its install hint, and a missing REQUIRED tool's remediation names both
  the tool and the install command.
- MUST-STAY-QUIET: `test_missing_optional_tool_is_silent` -- an absent
  OPTIONAL/OPTIONAL_FOR_GATE tool produces no remediation line.
- THIRD (gate distinguishes UNMEASURED from CLEAN): NOT built here --
  see "left out of scope" below; this is real remaining work, not
  disclosed-and-dropped.

XDIST SPECIFICALLY (build item 3): checked `warn_if_xdist_bound_missing`
(tickets/_worktree_guard.py) as directed -- confirmed it covers ONLY an
unset fleet bound (PYTEST_XDIST_AUTO_NUM_WORKERS missing from os.environ
under a detected fleet context), never the plugin's ABSENCE. Those are the
two different conditions the ticket named. `scan_external_tools` now
reports the plugin's absence via `frob doctor` (OPTIONAL_FOR_GATE,
pytest-xdist), but nothing yet preflight-checks it before an actual pytest
spawn adds `-n auto` -- filed as T-3316 rather than expanding this
ticket's scope into `_worktree_guard.py`.

LEFT OUT OF SCOPE (this ticket's own declared scope is doctor.py only; the
ask spans far more of the tree than that declaration covers) -- filed as
follow-ups rather than silently expanding scope or silently dropping them:

- T-3311: collapse the three divergent spawn conventions (sys.executable
  -m pytest / uv run pytest / bare pytest / bare python) into one
  resolution helper every call site uses, with a loud typed Result error
  -- this is build item 1 and most of item 2's actual enforcement point
  (the doctor-report unhealthy signal here is necessary but not
  sufficient: a command that never calls `frob doctor` first still hits
  the bare-spawn failure mode directly).
- T-3314: the scaffolded CI templates (ci.yml.j2 x3) silently skip `frob
  check` via a `::notice::` when `frob graph --help` fails, rather than
  failing the job -- reported per the ticket's own explicit instruction
  ("that pattern should be reported... as the same defect in the
  scaffolded CI"), not fixed here (out of this ticket's scope).
- T-3316: `warn_if_xdist_bound_missing` gap above.
- The THIRD fixture (a gate reporting UNMEASURED, distinguishable from
  CLEAN in exit code and output, when its optional tool is absent) is
  real remaining work at the individual-gate level (e.g. the TEST gate,
  `frob coverage`) -- doctor.py's own scope has no gate-running code to
  attach this to; it belongs with T-3311/T-3316's call-site work.

Filed: T-3311, T-3314, T-3316

### Changed
```
 tickets/T-3276/ticket.md | 16 +++++++++++++++-
 1 file changed, 15 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_doctor.py::TestScanExternalTools::test_present_binary_reports_version` (pytest node id, verified passing when recorded)
- `tests/unit/test_doctor.py::TestScanExternalTools::test_missing_binary_reports_absent_with_install_hint` (pytest node id, verified passing when recorded)
- `tests/unit/test_doctor.py::TestScanExternalTools::test_present_package_reports_version_via_importlib` (pytest node id, verified passing when recorded)
- `tests/unit/test_doctor.py::TestScanExternalTools::test_missing_package_reports_absent` (pytest node id, verified passing when recorded)
- `tests/unit/test_doctor.py::TestExternalToolsRemediation::test_missing_required_tool_names_it_and_the_install_command` (pytest node id, verified passing when recorded)
- `tests/unit/test_doctor.py::TestExternalToolsRemediation::test_missing_optional_tool_is_silent` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
