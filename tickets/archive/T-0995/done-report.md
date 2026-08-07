## Done report

Dedup'd the two pre-existing DUP001 findings T-0988's fmt sweep surfaced.

test_evidence_integrity.py: TestD02ScopeBinding.test_transition_allows_when_covers_scope_true
and TestT0417ReverifyEvidenceOnClose.test_transition_allows_when_evidence_reverified_true were
byte-identical arrange/act/assert blocks differing only in which transition() override kwarg
they passed. Both live in the same file and exercise closely related evidence-transition safety
overrides, so this is a genuine single-owner copy: extracted a shared
`_assert_transition_to_done_allows(tmp_path, **transition_kwargs)` helper (tagged
`frob:ticket T-0995`) and had both tests call it, removing both stale DUP001 waivers.

test_tickets_scope_mutation.py::TestScopeCli.test_cli_requires_reason vs
test_ticket_file_flags.py::TestScopeReasonFile.test_neither_reason_nor_reason_file_errors_cleanly
were judged NOT a genuine single-owner copy: they live in two different files covering two
different named suites (general scope-CLI coverage vs T-0458's reason-file-exclusivity coverage),
and currently overlap only because both happen to exercise the "no reason provided" input.
Extracting a shared helper across files would blur which suite owns which check. Refreshed the
frob:waive DUP001 reason on the surviving site to document this judgment instead of extracting.

Ruff-format was applied to test_evidence_integrity.py after the helper extraction (the new
function definition needed reflow); no other files touched.

### Changed
```
 tests/test_evidence_integrity.py     | 49 +++++++++++++++++++-----------------
 tests/test_tickets_scope_mutation.py | 15 +++++++----
 2 files changed, 36 insertions(+), 28 deletions(-)
```

### Evidence
- `tests/test_evidence_integrity.py::TestD02ScopeBinding::test_transition_allows_when_covers_scope_true` (pytest node id, verified passing when recorded)
- `tests/test_evidence_integrity.py::TestT0417ReverifyEvidenceOnClose::test_transition_allows_when_evidence_reverified_true` (pytest node id, verified passing when recorded)
- `tests/test_tickets_scope_mutation.py::TestScopeCli::test_cli_requires_reason` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 14 error(s), 1765 warning(s), 358 waived
- error-findings: ARCH001@src/frob/graph/callgraph.py, ARCH001@src/frob/testing/_collect.py, COV001@src/frob/arch/_models.py, COV001@src/frob/gitlog/__init__.py, COV001@src/frob/process/parsers/common.py, COV001@src/frob/render/_color.py, COV001@src/frob/render/_elements.py, DEPR005@tests/system/test_cli_ticket_worktree_root.py, DEPR005@tests/test_evidence_integrity.py, DEPR005@tests/test_gates.py, DEPR005@tests/test_ticket_land.py, DEPR005@tests/test_vet.py, PERF003@src/frob/arch/_cpp_mayraise.py, PERF004@src/frob/arch/_cpp_mayraise.py
