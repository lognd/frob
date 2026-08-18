## Done report

Changed:
- src/frob/gates/_waive_audit_watermark.py::WaiveAuditWatermark (added `catchup_covered` field)
- src/frob/app/ticket_runner/_waive_audit.py::AuditVerdict (added PARTIAL_PROGRESS_BANKED)
- src/frob/app/ticket_runner/_waive_audit.py::_waiver_identity (new private helper)
- src/frob/app/ticket_runner/_waive_audit.py::run_scan (catch-up branches now skip catchup_covered identities)
- src/frob/app/ticket_runner/_waive_audit.py::complete_pass (new `partial` kwarg; banks a batch instead of refusing outright when partial=True)
- src/frob/app/ticket_runner/_waive_audit.py::_complete_refusal_reason (extracted from complete_pass, ARCH001)
- src/frob/app/ticket_runner/_waive_audit.py::_next_catchup_fields (extracted from complete_pass, ARCH001)
- src/frob/app/ticket_runner/_waive_audit.py::run / _run_scan_subcommand / _run_complete_subcommand (split for ARCH001; verdict now driven by watermark.catchup_remaining, not just cop_outs)
- src/frob/_cli_parsers/_ticket/_closeout.py::_add_ticket_waive_audit_parser (new `--partial` flag on `complete`)
- src/frob/app/config.py::AppConfig (new `waive_audit_partial` field)
- src/frob/app/_config_external.py::_BOOL_FLAGS (registered `waive_audit_partial` so the flag actually reaches AppConfig)
- docs/modules/app.md#waive-audit-t-2467 (documents catchup_covered, PARTIAL_PROGRESS_BANKED, and --partial)
- tests/unit/test_waive_audit_runner.py::TestPartialCatchup (4 new tests)

Evidence: tests/unit/test_waive_audit_runner.py::TestPartialCatchup.test_partial_without_flag_still_refuses, test_partial_banks_batch_and_advances_watermark, test_next_scan_skips_already_banked_waivers, test_banking_the_final_batch_clears_catchup_state (all pass, `frob test --base main` selected 20 touched tests, exitstatus=0)

Filed: none (this ticket itself was filed as a follow-up from T-1614's own live pass)

Gates: `frob check --ticket T-2485` -- all findings tied to files this ticket touched are resolved (E501/ARCH001/WIRE001/FLAGCOV001 fixed; the one remaining pre-existing E501 at _waive_audit.py:420 predates this ticket, same line as before, only shifted by unrelated additions above it -- not introduced by this change). PRE001 staleness cleared via `frob ticket sweep T-2485`. Repo-wide gate-summary FAILs (ruff-format, ty, dup, etc.) are pre-existing and unscoped to this ticket per the `gate:scope-note` in `frob check --ticket` output.

Root cause and context: this fixes the mechanism T-1614's own first live pass against this repo's real corpus (100 scanned, 857 not covered) surfaced as broken. `complete_pass` used to refuse UNCONDITIONALLY whenever a bounded catch-up pass had `not_covered_count > 0`, and nothing ever wrote a watermark with nonzero `catchup_remaining` -- so the only way to ever advance the watermark was reviewing the entire 857-waiver backlog in one sitting, exactly what `_CATCHUP_BOUND=100` was built to avoid. `complete --partial` now banks exactly the reviewed batch (advancing `catchup_remaining`/`catchup_covered`) while the CLI's own displayed verdict is driven off `watermark.catchup_remaining`, not just `cop_outs`, so a banked-but-incomplete pass can never render identically to `CLEAN` (T-2391 fail-loudly doctrine, per the coordinator's explicit design constraint). Verified end-to-end by using the fixed tool to resume and complete T-1614's own audit pass in the same session.

### Changed
```
 tickets/T-2485/ticket.md | 51 +++++++++++++++++++++++++++++++++++++++++++++++-
 1 file changed, 50 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_waive_audit_runner.py::TestPartialCatchup::test_partial_without_flag_still_refuses` (pytest node id, verified passing when recorded)
- `tests/unit/test_waive_audit_runner.py::TestPartialCatchup::test_partial_banks_batch_and_advances_watermark` (pytest node id, verified passing when recorded)
- `tests/unit/test_waive_audit_runner.py::TestPartialCatchup::test_next_scan_skips_already_banked_waivers` (pytest node id, verified passing when recorded)
- `tests/unit/test_waive_audit_runner.py::TestPartialCatchup::test_banking_the_final_batch_clears_catchup_state` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
