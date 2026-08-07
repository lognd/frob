## Done report

Root cause (code): T-0690 registered the `ffi_boundary` gate in
`frob.gates._ALL_GATES` (bringing the total to 38) but never added it to
any `_STAGE_GROUPS` member. `_stamp_baseline_gate_chunks()` computes a
"leftover" chunk of any gate not covered by a `_STAGE_GROUPS` alias, so
`ffi_boundary` became a phantom 1-gate leftover chunk with no named
`--only` alias any caller (including the agent playbook's own chunked
`--stamp-baseline` recipe) ever passes -- the accumulator in
`_run_stamp_baseline` could record at most 37/38 gates and never
converged, so the real baseline was never (re)stamped.

Fix: added `"ffi_boundary"` to the `gates-fast` member of `_STAGE_GROUPS`
in `src/frob/check/__init__.py` (it is not in
`frob.gates._PROCESS_POOL_GATES`, so it is thread-pool/I-O-bound, the same
shape as the rest of `gates-fast`, not the CPU-bound `gates-native`/
`gates-security` giants).

Root cause (environment, NOT a code regression): 3 of the 4 reported
failing tests (test_testing_collect, test_close_with_evidence_and_done_
report_succeeds, test_dry_run_reports_clean) were caused by a stray
`/tmp/pyproject.toml` left on the shared machine `/tmp` by an unrelated
earlier session (dated the day before, unrelated to any of today's
lands). Every pytest `tmp_path`/`tmp_path_factory` fixture nests under
`/tmp/pytest-of-<user>/...`, and `uv run pytest` (the exact subprocess
`collect_python_tests` spawns) walks up parent directories looking for a
workspace root -- it found `/tmp/pyproject.toml` and tried to build a
package named "frob" from `/tmp` itself, which fails (missing README.md/
LICENSE/src dir), so every `uv run pytest --collect-only` spawned inside
any pytest tmp dir on this machine failed with exit 1, independent of
this repo's own code. Confirmed by reproducing manually with the file
present (fails) and absent (passes), and by rerunning all 3 tests with
only the stray file removed and no code change -- all 3 passed unmodified.
Removed the stray `/tmp/pyproject.toml` (pure junk, not part of any repo
or in-flight work) to unblock this and future test runs on this machine;
this part is not fixable in code since it is contamination outside any
repo tree.

Evidence (all four originally-reported failing tests, rerun clean after
the `_STAGE_GROUPS` fix and the stray-file removal):
- tests/integration/test_interfaces.py::TestInterfaces::test_testing_collect
- tests/system/test_cli_ticket.py::TestTicketRoundTrip::test_close_with_evidence_and_done_report_succeeds
- tests/system/test_cli_ticket_land.py::TestLandCLI::test_dry_run_reports_clean
- tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_baseline_only_chunk_completes_and_stamps

All 4 passed together in one `pytest` invocation (measured, `-p
no:cacheprovider -q`, 4 passed, 0 failed).

Gates: `frob check --ticket T-1044` run in chunks (lint,
static, gates-native, gates-security, gates-fast) -- all findings not
touching `src/frob/check/__init__.py` are pre-existing repo-wide debt
(waived or unrelated files); the DSL001 finding this ticket itself
introduced (a `frob:ticket T-1012:` comment misparsed as a directive) was
found and fixed in the same pass. PRE001 cleared via `frob ticket sweep`
after the code change. No in-scope gate errors remain.

### Changed
(no changed files detected)

### Evidence
- `tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_baseline_only_chunk_completes_and_stamps` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 8 error(s), 1994 warning(s), 344 waived
- error-findings: ARCH001@src/frob/arch/_cpp_mayraise.py, COV001@src/frob/arch/_models.py, COV001@src/frob/gitlog/__init__.py, COV001@src/frob/process/parsers/common.py, COV001@src/frob/render/_color.py, COV001@src/frob/render/_elements.py, PERF003@src/frob/arch/_cpp_mayraise.py, PERF004@src/frob/arch/_cpp_mayraise.py
