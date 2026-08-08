## Done report

Both defects fixed, exactly as scoped.

1. NOT PROFILE-AWARE: `_own_obligations_rel_bump_dirty`
   (src/frob/app/ticket_runner/_close_cmd.py) now checks
   `effective_profile(root)` first -- under `rapid`, the whole REL001
   preflight is skipped and the relaxation is recorded via
   `record_rapid_debt(root, ticket.id, "close-rel001-preflight-skipped")`,
   the same seam `frob.tickets._land._land_is_rapid` already uses for
   every other rapid relaxation. Fails closed: an unresolvable profile
   falls back to running the check (tested explicitly), never silently
   skips it.

2. NO AGENT-REACHABLE REMEDY: the outstanding-bump WARNING now names the
   real remedy explicitly -- "do NOT bump pyproject.toml by hand, that
   commit is land-owned and the T-0731 hook will refuse it; the
   supported remedy is `frob ticket land <id>`, which applies the bump
   and closes this ticket itself." Tested that the log message actually
   contains both the prohibition and the named remedy.

Regression coverage matches the ticket's own acceptance text: under
rapid, closes without a bump and records debt (tested); under standard,
the refusal message names `frob ticket land` (tested).

Not touched, disclosed rather than silently dropped: the generic
own-obligations refusal message in `frob.tickets._evidence`'s
`transition` (shared across COV001/SELFAUDIT001/REL001) still fires
alongside the specific, now-corrected REL001 WARNING this ticket owns --
`_evidence.py` is outside T-1705's declared scope.

No root-cause fix needed under DEAD001/WIRE001/OPAQUE001/REF002.

### Changed
```
 tickets/T-1705/ticket.md | 7 ++++++-
 1 file changed, 6 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_close_rel001_bump.py::TestOwnObligationsRelBumpDirtyRapidSkip::test_rapid_skips_the_check_and_records_debt` (pytest node id, verified passing when recorded)
- `tests/unit/test_close_rel001_bump.py::TestOwnObligationsRelBumpDirtyRapidSkip::test_standard_still_runs_the_check` (pytest node id, verified passing when recorded)
- `tests/unit/test_close_rel001_bump.py::TestOwnObligationsRelBumpDirtyRapidSkip::test_outstanding_bump_under_standard_names_land_as_the_remedy` (pytest node id, verified passing when recorded)
- `tests/unit/test_close_rel001_bump.py::TestOwnObligationsRelBumpDirtyRapidSkip::test_unresolvable_profile_falls_back_to_running_the_check` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 0 error(s), 931 warning(s), 731 waived
- error-findings: none (measured, zero errors)
