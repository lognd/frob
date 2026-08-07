## Done report

Changed:
- src/frob/strata/_sysdoc.py::_assumed_cwes (new)
- src/frob/strata/_sysdoc.py::_row (now takes `assumed: frozenset[str]`, prints
  `ASSUMED (<rung>)` instead of `PROVED (<rung>)` when the entry's discharging
  claim(s) include an `assumed` claim)
- src/frob/strata/_sysdoc.py::render_audit_matrix (computes `assumed =
  _assumed_cwes(model)` and threads it into `_row`)
- tests/unit/strata/test_sysdoc.py::TestRenderAuditMatrix (new regression test
  `test_assumed_discharge_renders_distinct_from_proved`)

Root cause: `check_discharge_completeness` (`_threat.py`) only returns
FAILING violations -- it discards, for a successfully-discharged obligation,
whether the discharging `Claim` was closure-proved or a human-owned
`assumed` TCB entry. `_row` in `_sysdoc.py` therefore printed `PROVED
(<rung>)` for BOTH cases whenever `discharge_violations` was empty for that
CWE. The claim-level model (`_claims.py::evaluate_claims`) already
distinguishes `Verdict.PROVED`/`EVIDENCED` from `Verdict.ASSUMED` -- the
renderer was the one place dropping the distinction, exactly as the ticket
diagnosed. Fix: `_assumed_cwes(model)` scans `model.claims` for the
`weakness:<cwe-id>:<node-id>` discharge-claim naming convention
(`_threat.py::_discharge_claim_id`) and collects every CWE id with at least
one `assumed=True` discharging claim, without importing any of `_threat.py`'s
private catalog internals (matches this module's existing T-0085 import
boundary). `_row` now checks `entry.id in assumed` before falling back to
`PROVED`.

Not touched: `frob.app.sys_runner`'s waiver-channel summary output
(`"PROVED (N waived)"` / `"sys audit: PROVED"`) -- that is T-0174's separate
surface per the dispatch instructions; only the `frob sys doc` per-CWE
matrix rows (`render_audit_matrix`/`_row`) changed. `audit_claim` /
`ClaimAuditResult` (the DOC003 doc-marker gate) were also left untouched --
that surface reports proved/not-proved as a single boolean over the whole
view's violation set, which is a separate distinction from a single row's
status label and out of this ticket's diagnosed bug (matrix rows only).

Evidence:
- `uv run pytest tests/unit/strata/test_sysdoc.py -q` -> `13 passed`
  (verified: all 13 tests in the file collected and passed, including the
  new regression test and the pre-existing `test_discharged_obligation_
  renders_proved` proving the PROVED path still renders unchanged).
- `uv run frob test --base main` -> `run_selected: python exit=0
  duration=2.70s`, `[PASS] python exit=0 2.70s` over the 7 touched-set
  `test_sysdoc.py::TestRenderAuditMatrix` node ids selected from the diff.
- `uv run frob check --ticket T-0224` -> `pass gates 3 violation(s), 27
  waived`; the 3 unwaived violations (`TEST006` missing coverage stamp,
  `PERF004` in `src/frob/tickets/_land.py:75`, `PERF003` in
  `src/frob/vet/_obfuscation.py:77`) are all pre-existing and outside this
  ticket's scope/diff (confirmed via `git status --short` -- neither file
  is touched by this change).
- `git diff main --diff-filter=D --stat` -> empty (deletion-filter land
  rule, section 9 of the playbook: no unintended deletions).

Filed: none (no out-of-scope work discovered).

Gates: `frob check --ticket T-0224` clean of new violations; no new waivers
added.
