## Done report

Implemented per-test stability tracking and quarantine-with-ticket in a new
module `src/frob/testing/_stability.py`:

- Storage: `.frob/test-stability.json`, keyed by pytest node id, each entry
  a `StabilityEntry` (frozen pydantic model) holding a bounded (last 20
  runs, `HISTORY_WINDOW`) "P"/"F" history plus `quarantine_ticket` /
  `quarantined_at`. Same per-worktree-derived-state posture as the
  existing pytest-collection cache and coverage stamp.
- Flake detection rule (`is_flaky`): a test's bounded history contains
  BOTH a pass and a fail. All-pass and all-fail are explicitly NOT flaky
  (an all-fail test is a real regression, not a flake); fewer than 2
  recorded runs is never flaky.
- Quarantine semantics: `quarantine(root, node_id, ticket_id=...)` always
  ties to a real ticket -- a resolvable, still-open one if given
  explicitly (Err TicketUnresolvable otherwise), or an auto-filed bug
  ticket via the public `frob.tickets.new_ticket` API when omitted (never
  touching `src/frob/tickets/**` internals, per the ticket's scope note).
  `lift_quarantine` clears quarantine explicitly (never automatic on going
  stable). `quarantine_alarms` flags quarantines whose ticket has closed
  (DONE/DROPPED) or gone unresolvable while the test is still flaky --
  the expiry alarm. `evaluate_gate` is the pure function that folds
  quarantine into a pass/fail verdict: a failing run is promoted back to
  passing only if every failing node id is quarantined.
- Per-test capture: `capture_python_outcomes` runs given node ids directly
  via `uv run pytest --junit-xml` (bypassing configured `[[test.runner]]`
  templates, which have no report-path placeholder) and parses per-test
  pass/fail from the junit report; `track_python_stability` combines
  capture + record in one call. KNOWN LIMITATION (documented in
  docs/modules/testing.md): junit's classname/name naming does not match
  this codebase's `path::Class::method` symref convention, so outcomes are
  zipped onto the original node ids by pytest's own argv-preserving run
  order rather than re-derived from junit naming.
- Wired `frob test`'s CLI (`src/frob/app/test_runner.py`) to call this
  automatically is explicitly OUT of this ticket's scope (declared scope
  is `src/frob/testing/**`, `docs/modules/testing.md`, `tests/unit/testing/**`
  only) and is called out as a follow-up in the docs.

Docs: added a "Flake quarantine (T-0575)" section to
docs/modules/testing.md with full API surface, storage shape, flake rule,
quarantine enter/exit/expiry semantics, and the known junit-mapping
limitation.

Filed as a follow-up (out of scope): a real pre-existing circular-import
fragility between frob.testing and frob.gates (import frob.testing as the
first frob-touching import in a process raises ImportError -- reproducible
via `uv run python -c "import frob.testing"`). Does not affect the full
suite (already masked by import order), but breaks running the new test
file standalone; worked around locally in tests/unit/testing/test_stability.py
via an explicit `import frob.gates` before `from frob.testing import ...`,
documented inline. Ticket id noted below.

Not done in this pass, left for a follow-up: wiring frob.testing._stability
into frob test's actual CLI run path (src/frob/app/test_runner.py) so
quarantine/flake tracking happens automatically on every `frob test`
invocation -- out of this ticket's declared scope.

REL001 (public API changed, version bump) is left unresolved per this
repo's coordinator-landing convention (memory: "coordinator landing
workflow" -- REL001 bump happens at land time against the merged result,
not per-ticket in a worktree).

### Changed
```
 tickets.md | 309 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++--
 1 file changed, 302 insertions(+), 7 deletions(-)
```

### Evidence
- `tests/unit/testing/test_stability.py::TestRecord::test_persists` (pytest node id, verified passing when recorded)
- `tests/unit/testing/test_stability.py::TestRecord::test_window_bounded` (pytest node id, verified passing when recorded)
- `tests/unit/testing/test_stability.py::TestRecord::test_carries_quarantine` (pytest node id, verified passing when recorded)
- `tests/unit/testing/test_stability.py::TestIsFlaky::test_all_pass_ok` (pytest node id, verified passing when recorded)
- `tests/unit/testing/test_stability.py::TestIsFlaky::test_all_fail_ok` (pytest node id, verified passing when recorded)
- `tests/unit/testing/test_stability.py::TestIsFlaky::test_mixed_is_flaky` (pytest node id, verified passing when recorded)
- `tests/unit/testing/test_stability.py::TestIsFlaky::test_single_run_ok` (pytest node id, verified passing when recorded)
- `tests/unit/testing/test_stability.py::TestIsFlaky::test_filters_map` (pytest node id, verified passing when recorded)
- `tests/unit/testing/test_stability.py::TestQuarantine::test_explicit_ticket` (pytest node id, verified passing when recorded)
- `tests/unit/testing/test_stability.py::TestQuarantine::test_rejects_bad` (pytest node id, verified passing when recorded)
- `tests/unit/testing/test_stability.py::TestQuarantine::test_auto_files` (pytest node id, verified passing when recorded)
- `tests/unit/testing/test_stability.py::TestQuarantine::test_lift_clears` (pytest node id, verified passing when recorded)
- `tests/unit/testing/test_stability.py::TestQuarantine::test_lift_unknown_errs` (pytest node id, verified passing when recorded)
- `tests/unit/testing/test_stability.py::TestAlarms::test_closed_still_flaky` (pytest node id, verified passing when recorded)
- `tests/unit/testing/test_stability.py::TestAlarms::test_no_alarm_open` (pytest node id, verified passing when recorded)
- `tests/unit/testing/test_stability.py::TestAlarms::test_no_alarm_stable` (pytest node id, verified passing when recorded)
- `tests/unit/testing/test_stability.py::TestGate::test_already_ok_stays_ok` (pytest node id, verified passing when recorded)
- `tests/unit/testing/test_stability.py::TestGate::test_all_quarantined_ok` (pytest node id, verified passing when recorded)
- `tests/unit/testing/test_stability.py::TestGate::test_one_bad_stays_failed` (pytest node id, verified passing when recorded)
- `tests/unit/testing/test_stability.py::TestCapture::test_empty_ok` (pytest node id, verified passing when recorded)
- `tests/unit/testing/test_stability.py::TestCapture::test_spawn_err` (pytest node id, verified passing when recorded)
- `tests/unit/testing/test_stability.py::TestCapture::test_parses_junit` (pytest node id, verified passing when recorded)
- `tests/unit/testing/test_stability.py::TestTrack::test_captures_then_records` (pytest node id, verified passing when recorded)
