## Done report

BUG 1 (F-026) re-measured against current main: already fixed by T-2668's _GATE_SUMMARY_COUNTS_ONLY_RE split (.search(), no anchor). Added a regression test (test_replay_annotated_summary_still_parses) proving a REPLAY-annotated gate-summary line still parses as measured, confirming this stays fixed. BUG 2 (F-043/F-048): reproduced directly against the real CLI (frob ticket scope --add + sweep, both untracked-only after the scope commit, then two frob check --ticket <id> calls) -- the second and later checks replayed the PRE-sweep PRE001 verdict. Root cause: _gate_cache.py::_replay_fingerprint folded root_content_key (tracked-file content) + .frob/baseline + build fingerprint, but never the per-ticket .frob/prework/<id>.json sweep record or the gitignored .frob/coverage-stamp TEST006 reads -- both untracked derived state a legitimate sweep/coverage stamp writes without moving the fingerprint. Folded both in (read-if-present, hash, fold -- same shape .frob/baseline already uses). Designated repro (test_sweep_write_invalidates_a_ticket_scoped_replay) verified FAILED_AT_PARENT (pre-fix commit) and passes at HEAD. F-031: PRE001's own remediation text named 'frob ticket start <id>', which always refuses on an in-progress ticket (the only state prework_gate ever fires against, per its own state guard) -- fixed both branches to name 'frob ticket sweep <id>' instead, and updated the two existing test_gates.py assertions that pinned the old text. Scope widened from src/frob/app/ticket_runner/_verify.py to also include src/frob/gates/_gate_cache.py (BUG 2's actual fix location) and src/frob/gates/__init__.py (F-031's PRE001 message location) -- both cited with reasons via frob ticket scope --add, since the ticket's own investigation showed the fix could not land inside _verify.py alone.

### Changed
```
 src/frob/gates/__init__.py                     | 16 +++--
 src/frob/gates/_gate_cache.py                  | 69 ++++++++++++++-----
 tests/test_gate_cache.py                       | 93 ++++++++++++++++++++++++++
 tests/test_gates.py                            | 12 +++-
 tests/unit/test_ticket_runner_gate_findings.py | 35 ++++++++++
 tickets/T-3301/ticket.md                       | 35 +++++++++-
 6 files changed, 236 insertions(+), 24 deletions(-)
```

### Evidence
- `tests/test_gate_cache.py::TestRunReplay::test_sweep_write_invalidates_a_ticket_scoped_replay` (pytest node id, verified passing when recorded)
- `tests/test_gate_cache.py::TestRunReplay::test_unrelated_lookup_survives_unchanged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestScopePrework::test_pre001_missing_sweep` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestScopePrework::test_pre001_stale_sweep` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_gate_findings.py::TestCheckGatesSummaryFn::test_replay_annotated_summary_still_parses` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 12 error(s), 4354 warning(s), 859 waived
- error-findings: COV001@src/frob/tickets/_scope.py, COV003@tickets/T-3410, DEPR006@frob-deprecated-baseline.lock.json, DOC006@tickets/T-3411/ticket.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/tickets/_scope.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PRE001@tickets/T-3301, REL001@src/frob/__init__.py, SELFAUDIT001@design, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
