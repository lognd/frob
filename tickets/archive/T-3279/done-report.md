## Done report

Changed: frob-ratchet.lock.json (top-level pin object)

Evidence: tests/unit/gates/test_lock_producer.py::TestProducerStatusVerdicts::test_must_stay_quiet_when_pinned covers the pin-suppresses-ABANDONED contract this fix relies on; frob check --only tickets confirms gate:WAIVE now 0 errors (WAIVE011 cleared)

Filed: none (DEPR006/frob-deprecated-baseline.lock.json left as-is -- no CLI re-stamp verb found and it is outside this session's known self-gate error set; T-3279's own scope also names it but re-stamping it needs tighten_deprecated_baseline, an internal-only function with no exposed command)

Gates: frob check --only tickets clean of WAIVE011

### Changed
```
 frob-ratchet.lock.json   |  4 ++++
 tickets/T-3279/ticket.md | 16 ++++++++++++++--
 2 files changed, 18 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/gates/test_lock_producer.py::TestProducerStatusVerdicts::test_must_stay_quiet_when_pinned` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 3 error(s), 4277 warning(s), 914 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, DEPR006@frob-deprecated-baseline.lock.json, TICK011@tickets.md
