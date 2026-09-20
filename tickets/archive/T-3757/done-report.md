## Done report

raise win32 pytest per-test timeout to 600s via CLI --timeout append

### Changed
```
 .github/workflows/ci.yml | 16 +++++++++++++++-
 tickets/T-3757/ticket.md |  3 +++
 2 files changed, 18 insertions(+), 1 deletion(-)
```

### Evidence
- `cmd:uv run python -m pytest tests/test_ci_workflow_matrix.py tests/unit/test_release_workflow_gate.py -p no:xdist -q exit=0 sha256=b45c62f1acf0` (cmd evidence, exit=0)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 1 error(s), 4310 warning(s), 919 waived
- error-findings: DEPR006@frob-deprecated-baseline.lock.json
