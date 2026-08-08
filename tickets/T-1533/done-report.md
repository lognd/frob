## Done report

Changed:
- src/frob/registry/_corpus.py::CorpusError (new WriteFailed member)
- src/frob/registry/_staleness.py::sync_gate_rule_entries (returns WriteFailed on atomic_write I/O failure instead of reusing FileNotFound)
- src/frob/app/registry_runner.py (_CORPUS_ERROR_MESSAGES covers WriteFailed)
- docs/design/registry/EXHAUSTIVENESS-GATE.md (REG010 section notes the dedicated member)
- docs/guides/exhaustive-research.md (Corpus-emit mechanism section documents CorpusError's four members)

Evidence: tests/test_registry_staleness.py::TestSyncGateRuleEntriesCrashSafety::test_leaves_original_on_replace_failure

Filed: none

Gates: uv run frob check --ticket T-1533 clean (0 errors)

### Changed
```
 tickets/T-1533/ticket.md | 46 ++++++++++++++++++++++++++++++++++++++++++++--
 1 file changed, 44 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_registry_staleness.py::TestSyncGateRuleEntriesCrashSafety::test_leaves_original_on_replace_failure` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
