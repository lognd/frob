## Done report

Batch 16 of the T-2359 ruff-format-only reformat epic. Fresh `uv run
ruff format --check .` (2026-08-21) measured 13 files pending -- UP from
the 10 the coordinator's brief assumed, since new content landed after
batch 15 (T-2807, T-2817, T-2818, T-2800 all touched files in this
family). Verified rather than assumed the count in both directions, per
instruction.

Excluded tests/unit/test_coordinator_scripts.py from this batch:
`fleet_status.py`'s own LEASES section shows it live-claimed by T-2818
(in-progress, scope=['scripts/fleet_status.py',
'tests/unit/test_coordinator_scripts.py']). The other 12 files had no
live lease (checked every in-progress/planned/queued ticket's own
`scope:` block against the file list, cross-checked against
`fleet_status.py`'s LEASES output showing only 5 leases total, 3 live:
T-1686 root-resident/unrelated, T-2359 itself, T-2369, T-2370
(scope=[], its one child T-2810 already done, no live child claims
anything), T-2818). `src/frob/tickets/_land.py` has queued-only
(non-live) scope claims from T-2691/T-2361/T-2202 -- no worktree/lease
exists for any of them, so proceeding is safe (matches the T-2373
empty-scope-but-in-progress caution the coordinator raised: T-2373
itself is DONE now, not in-progress, so that caution does not apply
here).

Reformatted exactly these 12 files with `uv run ruff format <files>`,
nothing else touched. Diff is whitespace/line-wrap only (verified via
`git diff` per file -- e.g. `_land.py`'s only change collapses a
3-line `min(...)` call onto one line).

Test verification: this session's ambient environment makes two of the
12 files' suites (`tests/test_ticket_work_and_land_finish.py`,
`tests/test_tickets_priority.py`) fail intermittently regardless of file
content -- confirmed by A/B: reverted each file to its ORIGINAL
(unformatted) content in place, re-ran the identical failing tests under
the identical shell environment, and got the same failure class (worktree-
guard/FROB_WORKTREE leakage into a test's own tmp_path fixture, and
FROB_AGENT causing an unrelated `frob check` full-run refusal inside a
subprocess the test spawns) -- then restored the formatted content.
This is pre-existing session/environment noise, not a regression from
this format-only change. All 12 files pass 100% clean (551 total tests
across the 10 non-flaky files: 497 + 36 + 13 + 5, plus the 2
investigated files individually green once FROB_WORKTREE/FROB_AGENT
were unset and xdist worker-count pressure was reduced) when run without
that ambient leakage.

Filed: none new. T-2359 (parent epic) NOT closed by this batch --
tests/unit/test_coordinator_scripts.py plus whatever else lands in the
interim still needs a further batch; recommend the coordinator re-measure
after this lands before deciding whether the epic can close.

Gates: format-only diff, no logic changes, no fixture-corpus files
touched (acceptance criteria per T-2359's own filed intent, still
formally UNBOUND at the epic level pending the final batch).

### Changed
```
 tickets/T-2821/ticket.md | 6 +++++-
 1 file changed, 5 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_tickets_organization.py::TestFieldRoundTrip::test_serialize_parse_round_trip` (pytest node id, verified passing when recorded)
- `tests/unit/test_capability_native.py::TestScanPythonCapabilitiesParity::test_unparseable_source_returns_empty_not_a_crash` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_backpressure.py::TestCeilingsForProfile::test_fortress_is_zero_depth_zero_age` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 23 error(s), 1586 warning(s), 716 waived
- error-findings: AFFECT001@src/frob/tickets/_land.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, CYCLE001@src/frob/__init__.py, DOC001@docs/investigations/T-2790-check-stage-profile.md, DOC001@docs/investigations/T-2796-backlog-reproduction.md, DOC006@docs/audits/test005-zero-classification-t1418.md, DOC011@docs/investigations/T-2796-backlog-reproduction.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, PERF004@src/frob/tickets/_evidence.py, PRE001@tickets/T-2821, REG002@docs/design/registry/check-coverage.yaml, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, SYS003@src/frob/check/__init__.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md
