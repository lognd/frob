## Done report

Implemented per the ticket's own instruction to "pick per implementation
reality, do not assume" -- investigated first and the literal premise
("--ticket filters findings to the ticket's declared scope") does not
hold for most gate families. Verified directly (frob check --only test,
with and without --ticket, --json diff): gate:TEST and gate:COV's COV001
report the EXACT SAME repo-wide counts in both cases (482/22 identical).
Only gate:SCOPE/gate:PREWORK and the diff-driven checks folded into
gate:COV (COV002/TODO001) and gate:FMT/gate:AFFECT are actually scoped to
the ticket's touched set. The real mechanism behind the T-1293 incident
is therefore the OPPOSITE of the ticket's literal wording: a repo-wide
"0 findings" was misread as ticket-scoped-and-clean, not a genuinely
filtered number hiding real findings. The second cited instance (T-1337,
--only opaque --ticket T-1337 never surfacing new INV006 errors) is a
distinct, simpler mechanism: `--only <subset>` runs ONLY the named gate
families, so anything outside it is invisible by construction, unrelated
to --ticket at all.

Fix implemented in src/frob/check/_python.py:
- New `_scope_disclosure_note(*, ticket, gates, ran)` (pure function):
  returns a disclosure string whenever `--only` narrowed the gate
  selection below the full `_ALL_GATES` set (naming every family NOT
  run this invocation -- addresses the T-1337 instance) and/or whenever
  `--ticket` is set (clarifying which families ARE actually diff/ticket-
  scoped vs which are repo-wide -- addresses the T-1293 instance,
  correctly, per what --ticket actually does).
- `_gates_success_result` now threads `ticket`/`gates` through and
  appends a `gate:scope-note` `ToolResult` (warn-severity, never
  blocking) whenever the note is non-None, right before the existing
  `gate-summary` line.
- Manually verified against the real T-1337 shape: `frob check --only
  opaque --ticket T-1351` now prints "NOTE: --only ran 2/38 gate
  famil(ies); NOT run this invocation (status unknown, not clean): ...
  invariant, ..." plus the --ticket clarification note, exactly the
  disclosure that would have caught T-1337 before it landed.

docs/guides/agent-playbook.md: new section 6c documents the measurement
protocol (proposal 4) -- cites both T-1293 and T-1337 as the concrete
incidents, states plainly that --ticket does NOT filter most gate
families (with the specific list of what it does scope), and folds in
the TEST005-specific guidance (a locally-scoped `pytest --cov` run
structurally cannot produce a trustworthy TEST005 count for files it
never measured, per `_test005_symbols`'s own skip-when-unmeasured
design) -- this connects directly to T-1335's coverage-pipeline work
from the same dispatch.

Not implemented (disclosed, not silently dropped): proposal 2 (naming
the measurement command inside TEST005's own finding text) and proposal
3 (a coverage-derived gate refusing to report at all on a stale/absent
stamp) -- both are real, separately-scoped improvements to
src/frob/gates/_coverage.py, which T-1335's own residue ticket (its
Done report's "T-1335 residue" ticket, scoped to that exact file) is the
right home for; folding them into this ticket's src/frob/check/**-only
scope would have meant editing a file outside it.

Also fixed in this dispatch, as its own small ticket (T-1362, landed
separately): a `ty` no-matching-overload regression T-1335's own new
test (tests/unit/test_makefile_coverage.py) introduced, found while
verifying this ticket's lint stage.

Verification: `uv run pytest tests/unit/test_check.py -p no:cacheprovider
-q` (full file, all pass) and `tests/system/test_cli_check.py` (full
file, all pass, confirming no ToolResult-shape assumption elsewhere in
the test suite broke from the new `gate:scope-note` stage). `frob check
--ticket T-1351 --only coverage --only scope --only invariant --only
tickets` shows only pre-existing, unrelated errors (2x INV006 in
src/frob/app/** -- explicitly leased/excluded from this dispatch's scope
-- and 1x TICK003 ledger-archive threshold), confirmed by diffing against
the identical error set observed before this ticket's changes.

Land-mechanics note for this Done report's own honesty: this ticket's
code (src/frob/check/_python.py, tests/unit/test_check.py, docs/guides/
agent-playbook.md) was swept onto main incidentally by T-1362's own land
(the wip-commit step picks up ALL uncommitted worktree changes, not just
the ticket being landed) before this ticket's own scope/evidence/Done-
report cycle ran -- confirmed via `git log`/file diff on main matching
this worktree exactly. This Done report and the scope/evidence CLI calls
above were re-applied against main's current ledger state after that
fact, so `frob ticket land T-1351` below is a ledger-only land (the code
diff versus main is empty; only tickets.md's own state transition needs
to land).

### Changed
```
 tickets.md | 27 +++++++++++++++++++++++++--
 1 file changed, 25 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/test_check.py::TestScopeDisclosure::test_only_names_the_gate_families_it_did_not_run` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestScopeDisclosure::test_ticket_flag_notes_which_families_are_actually_diff_scoped` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestScopeDisclosure::test_full_unfiltered_run_adds_no_disclosure` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 2 error(s), 920 warning(s), 688 waived
- error-findings: PII012@tests/unit/test_doctor_runner_t1276.py, TICK003@tickets.md
