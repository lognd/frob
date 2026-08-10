## Done report

Changed:
src/frob/app/ticket_runner/_land_cmd.py::_touched_py_files
src/frob/app/ticket_runner/_land_cmd.py::_ty_check_files
src/frob/app/ticket_runner/_land_cmd.py::_assert_touched_files_type_check_pre_land
src/frob/app/ticket_runner/_land_cmd.py::_land_core_prepare
src/frob/tickets/_land_verify.py::_reverify_done_report_claims_post_merge

Evidence: tests/test_ticket_work_and_land_finish.py::TestAssertTouchedFilesTypeCheckPreLand::test_a_type_error_in_a_touched_file_refuses_the_land, plus its sibling tests in the same class, plus tests/test_ticket_work_and_land_finish.py::TestReverifyDoneReportClaimsDisclosesUnknownGateState::test_no_captured_claims_section_logs_unknown_not_clean. Full module: 41/41 pass, no regressions.

Root cause (confirmed by direct reading, matching the ticket's own
measurement): `land()`'s post-merge `check_gates()` re-verification
(`_reverify_done_report_claims_post_merge`) only ever actually calls the
fresh `frob check` spawn when the ticket's Done report carries a
`### Captured claims` section -- `claims is None: return Ok(None)` skips
it entirely otherwise. An agent whose done-report used `--why-file` with
no capture, or whose capture ran under a scoped `--only` selection that
omitted `ty`, gets NO fresh gate re-check at land at all for that
family -- exactly how T-1894/T-1896 landed real `invalid-argument-type`
errors under the rapid profile, only caught afterward by the deferred
post-land sweep against an already-published commit.

Fix (both required-fix items, on merit):

1. `_assert_touched_files_type_check_pre_land` -- a new, small,
   UNCONDITIONAL guard (every profile, including rapid) wired into
   `_land_core_prepare` immediately after the existing T-1175 absorption
   step. Scoped to this ticket's own touched `.py` files (reusing
   `_land_touched_paths`, the same diff-derived touched-set T-1404
   already computes for the fmt pass) so it stays cheap -- one `ty
   check <touched files>` spawn, not a full-tree run. Any `ty` error in
   those files refuses the land (`sys.exit(1)`), naming the file(s).
   Split into three small functions (`_touched_py_files` filter,
   `_ty_check_files` spawn+parse, the thin decide-and-log wrapper) after
   an ARCH103 finding on the first single-function draft; both `ty` and
   `frob check --ticket T-1907 --only arch` are clean on the final
   shape (two ARCH103 waivers added on the spawn-building/decision
   functions, matching this module's own precedent for orchestration-
   shaped functions e.g. `_assert_design_loads_pre_land`).
2. `_reverify_done_report_claims_post_merge`'s `claims is None` early-out
   now logs a WARNING before returning `Ok(None)`, explicitly saying this
   ticket's gate-state re-verification was SKIPPED because nothing was
   ever recorded to compare against -- "treat as UNKNOWN, not clean" --
   rather than silently doing nothing. This is disclosure, not a
   refusal: land still proceeds (the (1) guard above is what actually
   closes the gap for the `ty` family specifically; this is the
   "unknown is not clean" signal the ticket's investigation names, made
   visible for every claims-less land regardless of which gate families
   it never ran).

Regression tests (required-fix item 3): `TestAssertTouchedFilesTypeCheckPreLand`
(3 tests -- a real `invalid-return-type` in a touched file refuses with
`SystemExit(1)`; a clean touched file does not refuse; an empty/None
touched set is a no-op) use a REAL `ty` subprocess, not a mocked parser,
so the test proves the actual cwd/extra-search-path/exit-code wiring
works end to end. `TestReverifyDoneReportClaimsDisclosesUnknownGateState`
covers the disclosure half directly.

Filed: none. This ticket's own fix covers required items (1) and (2);
item (3)'s regression test is the evidence above, not a separate ticket.

Rapid-profile impact (playbook requirement -- report before my land
makes existing in-flight work stricter): the new guard is UNCONDITIONAL
by design (that is the whole point -- rapid must not relax it), so any
worktree currently mid-flight under the rapid profile with a genuine
`ty` error in its own touched `.py` files will, for the first time,
be REFUSED at land instead of landing and being swept later. I did not
find a way to make this "soft" without reproducing the exact gap this
ticket exists to close. Scope is narrow (only the landing ticket's own
touched files, not a repo-wide type-debt gate) and the check is cheap
(a handful of files, not the whole tree), so the risk is a ticket that
already has a real type error in its own diff -- which is precisely the
class this ticket wants to stop landing.

Gates: `frob check --ticket T-1907 --only arch --only ty --only gates`
-- gate:ARCH 0 errors (after the two waivers above), gate:COV 0 errors,
gate:SCOPE 3 errors, all three pre-existing T-1903 artifacts
(rapid-debt.jsonl, tickets/T-1903/ticket.md, tickets/T-1903/done-report.md)
committed earlier in this SAME series worktree -- diff noise from this
scoped check comparing against the worktree's original stale base
rather than the real, already-landed main T-1903 will occupy once the
coordinator lands it first; not a T-1907 defect. gate:REG 1 error is
the same pre-existing SYS-IFACE-ORDER/SYS104 registry drift already
noted in T-1903's Done report, unrelated to this ticket. The 3 `ty`
diagnostics are the same pre-existing tests/unit/gates/test_sys_
interface_canonical_order.py argument-type mismatch already reported in
T-1903's own check; confirmed unrelated by `uv run ty check` scoped to
this ticket's exact three touched files (_land_cmd.py, _land_verify.py,
the test file), which reports "All checks passed!".

### Changed
```
 rapid-debt.jsonl                          |   2 +
 src/frob/app/ticket_runner/_land_cmd.py   | 207 +++++++++++++++++++++++++++---
 src/frob/tickets/_land_verify.py          |  23 ++++
 tests/test_ticket_work_and_land_finish.py | 146 +++++++++++++++++++++
 tickets/T-1903/done-report.md             |  64 +++++++++
 tickets/T-1903/ticket.md                  |  20 ++-
 tickets/T-1907/ticket.md                  |  28 +++-
 7 files changed, 473 insertions(+), 17 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 3 error(s), 895 warning(s), 697 waived
- error-findings: E501@/home/logan/projects/frob/.claude/worktrees/land-integrity-series/src/frob/app/ticket_runner/_land_cmd.py, REG002@docs/design/registry/check-coverage.yaml, invalid-argument-type@tests/unit/gates/test_sys_interface_canonical_order.py
