## Done report

Built the durable quarantine circuit-breaker primitive and the land-path
enforcement half, within declared scope.

`src/frob/verify/_quarantine.py` (new): `.frob/quarantine.json`-backed
durable state, mirroring `frob.verify._watermark`'s own persistence
shape (pydantic `frozen=True, extra="forbid"`, schema-versioned,
per-store advisory lock via `frob.tickets._land_queue.file_lock`).

- `raise_quarantine(root, *, batch_commit_shas, findings)`: persists a
  raised record, logs ERROR naming the batch and every finding, refuses
  on zero findings.
- `is_quarantined(root)`: `True` iff the current record's `cleared_at`
  is still `None`. Propagates a corrupt-store `Err` rather than
  degrading to `False` ("cannot verify is never verified").
- `clear_quarantine(root, *, dispositions, reason, actor)`: the ONLY
  clearing path -- requires every recorded finding to carry a
  disposition (`"filed"` with a real ticket id, or `"dismissed"` with a
  reason) or refuses with `FindingsNotDisposed`. There is no "record a
  green run" entrypoint anywhere in this module -- a green verification
  structurally cannot reach the clear path, which is the actual property
  the ticket asked for (verified directly:
  test_green_verification_alone_never_clears re-checks is_quarantined
  five times with no clear call and it stays True).

`src/frob/app/ticket_runner/_land_cmd.py`: added
`_quarantine_override_ceilings`, called from `_apply_backpressure` right
before its existing `ceilings_for_profile` result is handed to
`block_until_watermark_advances` (T-1692's own mechanism, reused rather
than duplicated) -- while quarantine is raised (or its store is
unreadable), ceilings are forced to `(max_depth=0, max_age_s=0.0)`, the
same shape `fortress` already gets, regardless of the land's actual
profile. This is "either run fully synchronous verification or block"
(the ticket's acceptance wording) implemented as a ceiling override on
an existing block/drain mechanism, not a second parallel gate.

`docs/modules/tickets.md` gained a new "Quarantine circuit breaker
(T-1693)" section covering all of the above plus the disclosed gap
below.

Disclosed gap, NOT done in this pass: nothing calls `raise_quarantine`
yet. The batch-verification driver that would call it on a red result
(`src/frob/app/ticket_runner/_rapid_sweep.py`, T-1690's own declared
scope) was leased by a concurrent in-progress ticket for this ticket's
entire working session -- confirmed via `frob ticket doable
--show-blocked` before starting, which (post-T-1743) correctly named
the real holding ticket and worktree. Filed T-1791 for the
wiring; the primitive and its land-path enforcement are both real and
tested independent of that wiring (raise/clear/is_quarantined all work
standalone, and the land-path override is tested by directly calling
raise_quarantine in the test, not through any driver).

Acceptance criteria status against the ticket's own wording:
- "a red batch raises quarantine" -- yes, `raise_quarantine` (tested,
  not yet wired to an actual driver call site -- see gap above).
- "a subsequent land does not defer" -- yes,
  `_quarantine_override_ceilings` forces synchronous ceilings (tested).
- "a later green verification does NOT clear it" -- yes, by
  construction (no such entrypoint exists; tested).
- "attributing and filing every finding does [clear it]" -- yes,
  `clear_quarantine` (tested).
- "the flag survives a worker restart" -- yes, disk-backed, re-loaded
  fresh on every `is_quarantined` call, no in-memory state (tested via
  test_survives_a_fresh_load_reflecting_a_restart).

Standing constraints from the ticket body: SYMBOLIC/NEVER LEXICAL --
this module makes no code-identity decisions itself (it persists and
gates on `Attribution`/`QuarantinedFinding` records the caller already
computed via T-1690's graph-reachability attribution); typani
`Result[T, E]` with named `ErrorSet` throughout, no bare `except`;
pydantic `frozen=True, extra="forbid"`, schema-versioned; every state
change logged (ERROR on raise, WARNING on clear); docs landed in the
same change; no waivers used anywhere in this module or its land-path
caller.

### Changed
```
 CHANGELOG.md                            |  10 -
 docs/modules/tickets.md                 |  78 +++++++
 src/frob/app/ticket_runner/_land_cmd.py |  42 ++++
 src/frob/verify/_quarantine.py          | 365 ++++++++++++++++++++++++++++++++
 tests/unit/test_land_cmd_quarantine.py  |  41 ++++
 tests/unit/verify/test_quarantine.py    | 169 +++++++++++++++
 tickets/T-1693/ticket.md                |  18 +-
 tickets/T-1791/ticket.md      |  22 ++
 8 files changed, 734 insertions(+), 11 deletions(-)
```

### Evidence
- `tests/unit/verify/test_quarantine.py::TestLoadQuarantine::test_missing_file_is_none` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_quarantine.py::TestLoadQuarantine::test_corrupt_file_errors` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_quarantine.py::TestIsQuarantined::test_false_when_never_raised` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_quarantine.py::TestIsQuarantined::test_true_while_raised` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_quarantine.py::TestIsQuarantined::test_false_after_clear` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_quarantine.py::TestRaiseQuarantine::test_raises_and_persists` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_quarantine.py::TestRaiseQuarantine::test_empty_findings_refused` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_quarantine.py::TestRaiseQuarantine::test_survives_a_fresh_load_reflecting_a_restart` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_quarantine.py::TestClearQuarantine::test_refuses_when_not_raised` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_quarantine.py::TestClearQuarantine::test_refuses_when_a_finding_is_undisposed` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_quarantine.py::TestClearQuarantine::test_clears_when_every_finding_disposed` (pytest node id, verified passing when recorded)
- `tests/unit/verify/test_quarantine.py::TestClearQuarantine::test_green_verification_alone_never_clears` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_cmd_quarantine.py::TestQuarantineOverrideCeilings::test_not_quarantined_is_unchanged` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_cmd_quarantine.py::TestQuarantineOverrideCeilings::test_quarantined_forces_synchronous` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_cmd_quarantine.py::TestQuarantineOverrideCeilings::test_corrupt_store_also_forces_synchronous` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 15 passed (from 15 evidence id(s))
- gates: 5 error(s), 925 warning(s), 721 waived
- error-findings: COV001@src/frob/verify/_quarantine.py, PRE001@tickets/T-1693, SELFAUDIT001@design, WIRE001@src/frob/verify/_quarantine.py, WIRE001@tests/unit/verify/test_quarantine.py
