## Done report

Root-cause verdict: scanner false positive, not a real capability use.
src/frob/arch/_logging_checks.py:67,70,71,73 are lines inside the
`_BOUNDARY_CALLEE_MARKERS` tuple, a bare-text needle table
`_is_boundary_call` compares a parsed `NormalizedCall.callee` STRING
against (`subprocess.`, `requests.`, `httpx.`, `socket.`, ...). The module
itself only imports `frob.arch._models`/`_normalized` and does no I/O --
it is written once against `NormalizedModule`, a parsed-fact model.
SELFAUDIT001's underlying SYS100 self-conformance scan
(`frob.strata._effects._line_effects`, reusing `frob.vet._capability`'s
`_PATTERNS` needle tables) has no code-vs-data distinction: it flags any
file whose text CONTAINS these substrings, regardless of whether the
substring is a live call or a classifier-table literal. This is the exact
same self-match class T-0729 already fixed for
`frob.arch._srp.py`'s `_IO_MODULE_PREFIXES` (also excluded via
`is_self_pattern_path`/`_SELF_PATTERN_SUFFIXES`), and the same class
T-0882 fixed for SYS100's bare-call boundary via
`_needle_hits_as_bare_call` -- here the needle never appears as a bare
call at all, it appears as tuple element data, so the fix is the same
`_SELF_PATTERN_SUFFIXES` exclusion mechanism T-0729 established, not a
change to `_needle_hits_as_bare_call` itself.

Fix: added `("frob", "arch", "_logging_checks.py")` to
`frob.vet._capability._SELF_PATTERN_SUFFIXES`, mirroring the `_srp.py`
entry verbatim in shape and rationale. Declaring `may net`/`may exec`/
`may fetch_url` on the `graphlang` design node was rejected as the wrong
fix per the ticket's own guidance -- the file does not actually have
those capabilities, so declaring them would be dishonest self-modeling
that also masks a REAL future exec/net use in this file from ever being
caught by SELFAUDIT001 again.

Regression tests added in `tests/test_vet.py::TestFingerprintScan`:
- `test_self_pattern_exclusion_covers_logging_checks_needle_tuples`:
  `is_self_pattern_path(_logging_checks.py, repo_root)` is True.
- `test_line_effects_reports_no_capability_on_logging_checks_module`:
  end-to-end, `frob.strata._effects._line_effects(_logging_checks.py) == []`
  (zero net/fs/exec effects observed), the actual SYS100/SELFAUDIT001
  scan path.

Evidence:
- `pytest tests/test_vet.py::TestFingerprintScan` (includes both new
  tests, 24 passed)
- `pytest tests/test_vet.py` (full file, 189 passed)
- `uv run frob check --ticket T-0910`: gate-summary 0 errors (SYS/
  SELFAUDIT001 clean; COV/PRE/SCOPE clean after `frob:ticket` directives +
  scope add + re-sweep)
- `uv run frob test --base main`: pre-existing unrelated failures only
  (native-detection/worktree-parallelism/registry-reconciliation tests
  outside this ticket's touched set: test_doctor.py,
  test_frob_self_model.py, test_registry_reconciliation_*.py,
  test_export_golden.py, test_cli_check.py::TestGitlessTargetGateSeverity,
  etc. -- none in src/frob/vet/_capability.py or tests/test_vet.py, none
  exercising `_SELF_PATTERN_SUFFIXES`/`_logging_checks.py`); rust suite
  passes 0.15s.

Filed: none -- fix stayed within the scanner correction the ticket's own
dispatch instructions directed (widened scope to
`src/frob/vet/_capability.py` and `tests/test_vet.py` via
`frob ticket scope --add`, both recorded in `scope_changes` above).

Gates: `frob check --ticket T-0910` clean, 0 errors.

### Changed
(no changed files detected)

### Evidence
- `tests/test_vet.py::TestFingerprintScan::test_self_pattern_exclusion_covers_logging_checks_needle_tuples` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestFingerprintScan::test_line_effects_reports_no_capability_on_logging_checks_module` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 0 error(s), 2300 warning(s), 219 waived
- error-findings: none (measured, zero errors)
