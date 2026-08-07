## Done report

Root cause: `_audit.py::_gap_rule_in_scope` (the exhaustiveness pass's own
`apply_waivers` in-scope predicate) did not exclude SYS205 from the rule ids
it judges staleness for, even though SYS205 already owns its own separate
`apply_waivers` call inside `check_mode_conformance`
(`_mode_conformance.py`). Since the exhaustiveness pass's `gaps` list never
contains a SYS205 finding (SYS205 findings live entirely in
`check_mode_conformance`'s own report), every declared `waive "SYS205:..."`
clause was unconditionally judged stale here regardless of whether the real
SYS205 evaluator matched and waived it -- the exact same cross-family
collision T-0724 (SYS200-203) and T-0640 (REL200/REL201) already hit and
fixed for their own rule families.

Fix: added `SYS_MODE_NONCONFORMANCE` ("SYS205") to the exclusion tuple in
`_gap_rule_in_scope`, imported from `_mode_conformance.py`, mirroring the
existing `_HOST_RULE_IDS`/`RESOURCE_CONTENTION_RULES`/`RELIABILITY_RULES`
pattern exactly.

Verified against this repo's own `design/frob.strata`: `frob sys audit`
now reports "mode-conformance PROVED (5 waived) -- zero UNWAIVED SYS205
gaps" with no SYSWAIVE002 stale-waiver finding for any of the five
tickets_ledger SYS205 waivers (previously all five were misreported
stale).

Gates run (chunked, --ticket T-1157):
- gates-fast: clean (0 errors) after scope-add + frob:ticket edge + sweep
  refresh.
- gates-native: 5 pre-existing ARCH001 errors (check_runner.py
  _try_check_delta_via_daemon, _close_cmd.py _fail, doctor.py
  run_diagnosis, _setters.py ticket_flow) -- these are the exact four
  findings already filed as T-1162 ("wave-18 fallout long-function
  extractions"), none in files this ticket touches or scopes.
- gates-security: clean (0 errors).
- lint/static: ruff-check/ruff-format/ty failures are all in files this
  ticket never touched (_store.py, _supplychain.py, various tests/*); my
  own two files (`src/frob/strata/_audit.py`,
  `tests/unit/strata/test_audit.py`) pass `ruff check` and
  `ruff format --check` individually.

`git diff main --diff-filter=D --stat` is empty.

### Changed
```
 tickets.md | 3 +--
 1 file changed, 1 insertion(+), 2 deletions(-)
```

### Evidence
- `tests/unit/strata/test_audit.py::TestExhaustiveness::test_sys205_waiver_is_not_reported_stale_by_exhaustiveness_pass` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
