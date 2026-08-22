## Done report

T-2290: reconciled `frob verify status`'s `unverified depth` figure against
the real `git rev-list --count <watermark>..HEAD` commit gap, and added a
soft (non-blocking) warning for the `rapid` profile once real verification
debt crosses a threshold.

Implemented (c): `frob.verify._watermark.commits_since_watermark` computes
the real commit gap via git; `frob verify status` now prints both
"unverified depth (queued land-intents): N" (renamed to name what it
measures -- a queue-entry count) and "commits since watermark: M"
alongside it, so the two numbers can never again be conflated.

Implemented (b): `frob.verify._backpressure.rapid_soft_warning` computes
against the real commit gap (falling back to queue depth only when git is
unavailable) and returns a message once depth/age crosses a threshold,
configurable via frob.toml [profile] rapid_soft_warn_depth/
rapid_soft_warn_age_s. Wired into `_apply_backpressure` (land path, WARNING
log only, never blocks -- verified live at land time: this exact land
printed "WARNING: ticket land: rapid profile verification debt is stale:
496 commits since watermark...") and into `frob verify status`'s own
output.

NOT implemented: (a), an actual drain mechanism. Per the dispatch brief's
explicit scope instruction, this needs a design decision (idle-time sweep
vs explicit command vs coordinator-invoked catch-up) that guessing wrong
would cost more than leaving open. Filed as a follow-up so the loud warning
this ticket adds has something to point an operator at beyond "run frob
verify now by hand".

Verified against this repo's own real stale watermark (not synthetic):
before this fix, `frob verify status` in the shared root read "unverified
depth: 102" while the real gap (`git rev-list --count
f0ab85d0..HEAD`) was 490 commits (measured directly). After the fix, the
same watermark reads "unverified depth (queued land-intents): 102" /
"commits since watermark: 490" side by side, plus a WARNING line.

### Changed
```
 src/frob/app/ticket_runner/_land_cmd.py  |  15 ++++-
 src/frob/app/verify_runner.py            |  32 +++++++++-
 src/frob/verify/__init__.py              |   4 ++
 src/frob/verify/_backpressure.py         | 100 +++++++++++++++++++++++++++++++
 src/frob/verify/_watermark.py            |  59 ++++++++++++++++++
 tests/unit/test_land_cmd_backpressure.py |  33 ++++++++++
 tests/unit/verify/test_backpressure.py   |  47 +++++++++++++++
 tests/unit/verify/test_verify_runner.py  |  27 +++++++++
 tests/unit/verify/test_watermark.py      |  75 +++++++++++++++++++++++
 tickets/T-2290/ticket.md                 |  52 ++++++++++++++--
 10 files changed, 437 insertions(+), 7 deletions(-)
```

### Evidence
- `tests/unit/verify/test_watermark.py::TestCommitsSinceWatermark::test_counts_raw_git_commits_not_queue_entries` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_watermark.py::TestCommitsSinceWatermark::test_zero_at_the_watermark_itself` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_watermark.py::TestCommitsSinceWatermark::test_none_when_watermark_commit_unresolvable` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_backpressure.py::TestRapidSoftWarning::test_no_watermark_yet_is_none` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_backpressure.py::TestRapidSoftWarning::test_below_threshold_is_none` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_backpressure.py::TestRapidSoftWarning::test_stale_watermark_trips_the_soft_warning` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_backpressure.py::TestRapidSoftWarning::test_toml_override` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_verify_runner.py::TestBuildStatus::test_commits_since_watermark_reflects_real_git_gap_not_queue_depth` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_cmd_backpressure.py::TestApplyBackpressure::test_rapid_profile_calls_soft_warning_never_blocks` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 9 passed (from 9 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, AFFECT001@src/frob/app/verify_runner.py, AFFECT001@src/frob/verify/_backpressure.py, AFFECT001@src/frob/verify/_watermark.py, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/release/_cli.py, COV001@src/frob/tickets/_land_git_ops.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV005@src/frob/verify/_backpressure.py, DOC001@docs/commands/release.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT002@scripts/fleet_status.py, E402@/home/logan/projects/frob/.claude/worktrees/t-2290/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2290/scripts/fleet_status.py, F841@/home/logan/projects/frob/.claude/worktrees/t-2290/tests/test_ticket_land.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PERF004@src/frob/app/ticket_runner/_new.py, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md
