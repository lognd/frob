## Done report

BLOCKED path deviation from the ticket's original plan (disclosed, not
silent): T-1719 item 2's plan was "register CLAUDE001 in _KNOWN_GATE_RULES
and wire it into src/frob/gates/**'s pluggable job table". At dispatch
time both src/frob/gates/__init__.py and src/frob/gates/_waive.py were
held by T-1937's LIVE cross-worktree lease (Gate rule registry is not
authoritative), which blocked BOTH the pipeline-wiring path and the
rule-registry-registration path -- frob ticket scope --add refused both
files outright. Rather than force through with --allow-cross-ticket
(no coordinator clearance) or block the ticket, followed this exact
repo's own PRE-EXISTING precedent for the identical situation:
check_runner.py's `_deploy_drift_result`/`_deploy_conformance_result`
(DEPLOY001/002/003) already document verbatim "not wired into frob.gates's
pluggable job table (that module is out of this ticket's scope) -- instead
this runs as one more extra stage run() folds into CheckResult, the same
shape ruff/ty/arch/cycle/dup/bind/exports already use". Implemented
CLAUDE001 as `_claude_config_drift_result` in exactly that shape: an
opt-in extra `ToolResult` stage (`tool="claude-config-drift"`), folded
into `_append_deploy_stages` (renamed in spirit, not in code -- still one
function, now three stages) right after the two deploy stages, counted in
`_stage_total`. Same gate-shaped fail-frob-check semantics as a real
gate:* family, just not registered in _KNOWN_GATE_RULES (that registration
is now unblockable follow-up work once T-1937 lands -- filed nothing new,
since T-1937 itself already tracks fixing that exact registry's
authoritativeness gap, and this rule id is a natural addition to its own
scope once it lands).

Similarly docs/modules/gates.md was contested by concurrent in-progress
T-1881's live lease -- documented the new stage in check_runner.py's own
docstring plus docs/guides/claude-hooks.md instead (matches deploy-drift's
own self-documenting posture, since that stage also sits outside
frob.gates's own scope and gates.md never describes it either).

Acceptance shape required by the dispatch: `test_reports_drift_when_
managed_copy_absent` constructs a repo with NO ~/.claude/hooks/widget.py
materialized yet and asserts the stage FAILS (exit_code=1, a CLAUDE001
diagnostic) -- the required pre-fix failing state. `test_clean_when_
in_sync` then materializes the copy and asserts the SAME check reports
clean (exit_code=0, no diagnostics) -- no false positive on an in-sync
tree. `test_no_stage_when_repo_has_no_managed_config` covers the opt-in
None case (a repo that never had the hook script at all).

Self-verifying: this repo's own `frob check` (run from inside this
worktree, whose $HOME really is /home/logan) reports `claude-config-drift
Claude config in sync with ~/.claude/` -- T-1808's own sync already
materialized this repo's real managed files, so T-1809's new gate reads
clean against the real operator home directory it protects.

Changed:
src/frob/app/check_runner.py::_claude_config_drift_result
src/frob/app/check_runner.py::_append_deploy_stages (extended to fold the
  claude-config-drift stage too)
src/frob/app/check_runner.py::_stage_total (counts the opt-in claude stage)
docs/guides/claude-hooks.md (T-1809 section documenting the new stage)

Evidence: tests/test_check_runner.py -- TestClaudeConfigDriftStage::
  test_reports_drift_when_managed_copy_absent, TestClaudeConfigDriftStage::
  test_clean_when_in_sync, TestClaudeConfigDriftStage::
  test_no_stage_when_repo_has_no_managed_config (3 node ids, all pytest,
  `frob test --base main` green: 5/5)

Filed: none new. T-1937 (already open, unrelated to this dispatch) is the
  natural home for CLAUDE001's eventual _KNOWN_GATE_RULES registration
  once its own lease on gates/__init__.py + gates/_waive.py releases --
  reporting this coordination point per the dispatch's explicit
  instruction rather than filing a duplicate ticket. docs/modules/gates.md
  documentation of CLAUDE001 is the other piece deferred the same way,
  blocked on T-1881's live lease on that file.

Gates: frob check --ticket T-1809 clean on every gate this ticket's own
  touched set can affect (ruff-check/AFFECT/SCOPE/TEST/COV all 0 errors;
  the new claude-config-drift stage itself reports PASS). Remaining
  repo-wide FAILs (gate:DOC/gate:DRIFT on src/frob/tickets/_land.py's
  pre-existing doc-anchor drift, ruff-format 81 files, gate:TODO/gate:TICK
  pre-existing warnings) are the identical unscoped/pre-existing debt
  T-1808's own Done report already confirmed against main -- unchanged by
  this ticket's diff.

### Changed
```
 tickets/T-1809/ticket.md | 49 +++++++++++++++++++++++++++++++++++++++++++++---
 1 file changed, 46 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/test_check_runner.py::TestClaudeConfigDriftStage::test_reports_drift_when_managed_copy_absent` (pytest node id, verified passing when recorded)
- `tests/test_check_runner.py::TestClaudeConfigDriftStage::test_clean_when_in_sync` (pytest node id, verified passing when recorded)
- `tests/test_check_runner.py::TestClaudeConfigDriftStage::test_no_stage_when_repo_has_no_managed_config` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 2 error(s), 893 warning(s), 703 waived
- error-findings: DOC002@src/frob/tickets/_land.py, DRIFT002@src/frob/tickets/_land.py
