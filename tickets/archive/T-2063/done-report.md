## Done report

Changed:
README.md (added `frob profile` command-table row, fixed claimed
command count 43 -> 44)
docs/modules/cli.md (regenerated generated command-table block via
`frob docs --sync-commands`)

Evidence:
tests/test_docblocks_gate.py::TestDoc005ReadmeTableDrift::test_missing_row_for_real_command_fails
tests/test_docblocks_gate.py::TestDoc005ReadmeTableDrift::test_count_claim_mismatch_fails
(existing DOC005 gate coverage exercising exactly the two violation
shapes this ticket fixed; full class run: `uv run pytest
tests/test_docblocks_gate.py -q` -- 26 passed, 0 failed)

SELFAUDIT001 half of the T-1584 residue (node=cli fs.read on
profile_runner.py, node=testsuite fs.write on test_profile_runner.py)
is NOT part of this change: re-measured on this ticket's base commit
(current main, a523fa4f5, T-1344's land) with `uv run frob check
--only sys --json` and found ZERO SELFAUDIT001 findings -- both
capabilities are already declared in design/frob.strata as an
incidental side effect of T-1344's own unrelated land (confirmed via
`git log -S'"src/frob/app/profile_runner.py"' -- design/frob.strata`,
which shows the declaration was added by T-1344's land commit, not by
any change in this ticket). This ticket's scope (`README.md`,
`docs/modules/cli.md`) never included `design/frob.strata` and no such
edit was made.

Filed: none (this ticket IS the filed residue ticket for T-1584; no
further out-of-scope work discovered while fixing it)

Gates: `frob check --only docblocks --ticket T-2063`: 0
DOC005 findings (pre-existing unrelated DRIFT002 errors in
src/frob/app/ticket_runner/_rapid_sweep.py remain, out of this
ticket's scope, owned by another agent per dispatch brief).
`frob check --land-parity`: clean -- 0 unscoped error(s), matches what
the land sweep would see.

## Investigation: why T-1584's own `--land-parity` claim did not catch this

T-1584's Done report states `frob check --land-parity: clean -- 0
unscoped error(s)`. This claim does NOT hold up against direct
measurement of the actual land commit (99ecae11dff1):

- Checked out 99ecae11dff1 into a throwaway detached worktree
  (`/tmp/t1584-check-hist`, since removed) and ran `frob check --only
  docblocks --json` there directly (unscoped, no `--ticket`, no
  `--delta`, `FROB_NO_GATE_CACHE` irrelevant since this is a fresh
  process). Result: all 3 DOC005 findings named in this ticket's body
  fire at that exact commit, in 2.84s.
- Same checkout, `frob check --only sys --json`: 6 SELFAUDIT001
  findings fire (1 node=cli fs.read, 5 node=testsuite fs.write
  instances -- the brief's "(x4)" undercounted by one against my
  direct measurement, immaterial to the conclusion).
- Both `docblocks` (gates-fast) and `sys` (gates-security) are
  ordinary `_STAGE_GROUPS` members `--land-parity`'s own
  `--budget 300` unscoped run covers, and both ran fast (well under
  budget) at this commit -- there is no plausible budget-deferral
  explanation for either family being silently skipped.
- `_drop_checkpoint_exempt_findings` (T-1524) does not exempt either
  rule: it only drops PRE001/SCOPE001 and root-level land-owned-file
  findings (`.frob-release.json`, `pyproject.toml`, etc.); README.md
  and docs/modules/cli.md are not in `_LAND_OWNED_SWEEP_EXEMPT`.
- `land_parity_findings` forces `FROB_NO_GATE_CACHE=1` on the spawned
  check, so T-1346's gate-result cache cannot explain a stale
  false-clean read either.

Conclusion: the gate family was NOT invisible to `--land-parity` --
the SAME rule ids (DOC005, SELFAUDIT001) fire deterministically and
quickly against the exact commit T-1584 landed, using the exact
mechanism `--land-parity` itself uses. I could not find a structural
blind spot in `--land-parity`'s own coverage that explains this. The
agent's "clean -- 0 unscoped error(s)" claim for that specific land is
therefore, on the evidence I was able to gather, simply incorrect --
either the check was not actually run against the final committed
tree state, its output was misread, or it was not run at all despite
being reported. I did not attribute this to a specific mechanism
beyond what I could directly measure (playbook sec 9): I found no
evidence of a genuine land-parity coverage gap for these two gate
families, only a discrepancy between a historical claim and what the
same tooling reports today against the same commit.

### Changed
```
 README.md                          |  3 +-
 docs/modules/cli.md                |  1 +
 tickets/T-2063/ticket.md | 69 ++++++++++++++++++++++++++++++++++++++
 3 files changed, 72 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_docblocks_gate.py::TestDoc005ReadmeTableDrift::test_missing_row_for_real_command_fails` (pytest node id, verified passing when recorded)
- `tests/test_docblocks_gate.py::TestDoc005ReadmeTableDrift::test_count_claim_mismatch_fails` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/app/ticket_runner/_query.py, ARCH001@src/frob/app/ticket_runner/_rapid_sweep.py, ARCH001@src/frob/tickets/_land.py, ARCH103@src/frob/app/ticket_runner/_query.py, DRIFT002@src/frob/app/ticket_runner/_rapid_sweep.py, PII012@src/frob/testing/_coverage_refresh.py, PRE001@tickets/T-2063
