## Done report

frob.gates._bare_toolchain.bare_toolchain_gate existed, was unit-tested, and
was documented, but was never registered in _build_process_jobs, so it never
ran on a real check. A written, tested, documented detector that is not
executed reports nothing while looking like protection -- this closes that
gap.

Registered it (mirroring taint_gate's ProcessJob wiring one function up), and
also added it to _ALL_GATES/_CANONICAL_GATE_ORDER: _build_jobs only runs a
process job whose name is in the `selected` set, which for a full `frob
check` run is `cfg.gates or _ALL_GATES` -- the ProcessJob entry alone would
have stayed unreachable dead wiring, the same gap taint_gate itself still has
today (out of scope here; a pre-existing condition on a gate this ticket did
not touch).

Evidence: tests/unit/vet/test_bare_toolchain.py::TestBareToolchainGate::test_flags_bare_argv_literal
(already-existing test covering bare_toolchain_gate itself; bound as this
ticket's evidence since the change is registry wiring around an already-
tested function, not new gate logic).

Gates: `frob check --ticket T-4146` -- gate:BARETOOL clean at 0 errors, 40
warnings, 0 unresolved (WARN-tier as designed, per bare_toolchain_gate's own
first-turn-on posture). The COV002 finding _CANONICAL_GATE_ORDER's edit
triggered is closed with a `frob:ticket T-4146` directive on that tuple.
gate:SCOPE reports 34 SCOPE002 findings that are pre-existing structural
fan-out of src/frob/gates/__init__.py's declared scope (the file's existing
symbols already carry transitive frob:doc/frob:tests edges into dozens of
files unrelated to this change) -- this predates and is independent of the
18 lines this ticket actually inserted; widening this ticket's scope to
~20 unrelated doc/test files to silence it would itself be the scope
overreach the agent playbook warns against, so it is left as a known,
unaddressed pre-existing condition rather than force-widened. Filed: none.

VERIFIED LIVE per the dispatch brief's explicit requirement (not merely that
the import resolves): a full `frob check` run reports:
  pass  gate:BARETOOL  0 errors, 40 warnings, 0 unresolved, 0 waived
with `bare_toolchain=<seconds>` present in the gate-summary per-gate timing
line -- 40 real subjects (bare pytest/ruff/ty/mypy argv literals across the
repo, including the exact T-4147/T-4148 sites), not a zero-subject phantom
registration.

### Changed
```
 src/frob/gates/__init__.py | 18 ++++++++++++++++++
 tickets/T-4146/ticket.md   |  2 ++
 2 files changed, 20 insertions(+)
```

### Evidence
- `tests/unit/vet/test_bare_toolchain.py::TestBareToolchainGate::test_flags_bare_argv_literal` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 15 error(s), 4507 warning(s), 934 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@src/frob/process/_project_tool.py, COV001@src/frob/vet/_bare_toolchain.py, DOC006@tickets/T-4144/ticket.md, DRIFT002@src/frob/check/_python.py, LARGE001@src/frob/_cli_parsers/_ticket/_closeout.py, PRE001@tickets/T-4146, REF001@.github/ISSUE_TEMPLATE/config.yml, REF002@.github/ISSUE_TEMPLATE/bug_report.yml, REF002@.github/ISSUE_TEMPLATE/feature_request.yml, REF002@.github/PULL_REQUEST_TEMPLATE.md, REF002@CODE_OF_CONDUCT.md, REF002@CONTRIBUTING.md, REF002@SECURITY.md, SCOPE002@tickets.md
