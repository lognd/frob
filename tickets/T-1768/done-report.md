## Done report

`frob release stamp --allow-unbumped` silently rebaselined `.frob-release.json`
with no `--reason` flag, no log line, and no audit record -- the third and
worst instance of the silent-override family T-1762 fixed for `ticket
archive --force` and `ticket land --finish --force`. Those two bypass a
guard for one invocation; this one permanently redefines what counts as
an API change from that moment forward, and the change is invisible in
the ledger, the logs, and the diff.

Mirrors T-1762's landed remedy exactly, reusing its primitive rather than
inventing a second shape:

- `frob.release.stamp` now takes `reason: str | None`. When
  `allow_unbumped=True` actually bypasses a real shortfall (the same
  `_bump_shortfall` computation the ordinary refusal already used), a
  non-blank reason is now REQUIRED -- `Err(ReleaseError.
  UnbumpedReasonMissing)` otherwise, nothing written. `allow_unbumped=True`
  with NO real shortfall (the version already covers the change) still
  needs no reason -- nothing was actually bypassed, matching `ticket
  archive --force`'s no-live-lease no-op posture.
- The bypass appends one `ForceOverrideEntry` line to `force-
  overrides.jsonl` via `frob.tickets._force_override.record_force_override`
  (`_record_unbumped_stamp_override`) -- the SAME audit-record shape
  `ScopeChangeEntry`/`AckAuditEntry`/`EvidenceChangeEntry` already use, not
  a fifth one -- naming the version move, the skipped bump class, and the
  count of symbol digests that changed (`_changed_symbol_count`), so the
  record says not just THAT the baseline moved but roughly how much
  surface it silently accepted.
- Logs at WARNING naming the old version, new version, skipped bump
  class, and the reason.
- `frob release stamp --allow-unbumped` takes matching `--reason TEXT` /
  `--reason-file PATH` CLI flags (`--reason-file` wins if both given,
  read verbatim -- T-0737's shell-injection-avoidance precedent),
  resolved in `frob.app.release_runner._resolve_release_allow_unbumped_
  reason`, reusing the shared `read_reason_file_verbatim` helper already
  used by `frob ack`/`ticket archive --force`.

Deliberately not done, per the ticket's own explicit instruction: no
name-pattern gate for override-shaped flags in general -- T-1762 already
examined and rejected that (semantic, not lexical, distinction; would
false-positive on all 18 `frob check --skip-*` flags).

Scope note: the ticket as filed declared `src/frob/_cli_parsers/
_reporting.py`, which does not contain the `--allow-unbumped` flag at
all -- the real CLI wiring lives in `src/frob/app/release_runner.py` and
`src/frob/_cli_parsers/_misc.py`. Narrowed scope to the real files before
starting (`frob ticket scope --remove/--add`), per the agent playbook's
scope-narrowing guidance.

### Changed
```
 docs/modules/release.md                |  45 ++++++++++++++
 src/frob/_cli_parsers/_misc.py         |  15 ++++-
 src/frob/app/_config_external.py       |   4 ++
 src/frob/app/config.py                 |   8 +++
 src/frob/app/release_runner.py         |  28 +++++++--
 src/frob/release/__init__.py           | 109 +++++++++++++++++++++++++++++++--
 tests/unit/test_release_stamp_guard.py |  99 +++++++++++++++++++++++++++++-
 tickets/T-1768/ticket.md               |  91 ++++++++++++++++++++++++++-
 8 files changed, 385 insertions(+), 14 deletions(-)
```

### Evidence
- `tests/unit/test_release_stamp_guard.py::TestAllowUnbumpedRequiresReason::test_refuses_with_no_reason_when_shortfall_is_real` (pytest node id, verified passing when recorded)
- `tests/unit/test_release_stamp_guard.py::TestAllowUnbumpedRequiresReason::test_succeeds_with_reason_and_writes_audit_record` (pytest node id, verified passing when recorded)
- `tests/unit/test_release_stamp_guard.py::TestAllowUnbumpedRequiresReason::test_no_reason_required_when_no_real_shortfall` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 0 error(s), 817 warning(s), 722 waived
- error-findings: none (measured, zero errors)
