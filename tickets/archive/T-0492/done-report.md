## Done report

Root cause: `_apply_evidence` (src/frob/app/ticket_runner.py) passed the raw,
un-normalized `--evidence` CLI node ids straight into `_verify_ids_passing`,
which buckets ids via `matches_collected(n, collected)` -- but the collected
sets (`python_ids`/`rust_ids`) only ever hold pytest's native `::`-form node
ids. A dot-form id (`path::Class.method`, the canonical spelling this repo's
own docs teach) never matches either bucket, so its bucket is empty,
`run_selected` never actually runs it, and it silently ends up absent from
the returned `passing` frozenset -- rejected downstream as
`EvidenceNotPassing` even though the test genuinely passed.
`add_evidence`'s own normalization (`_validate_evidence_list`, T-0293)
already converts dot-form to `::` form before resolution/persistence, so the
two normalization paths had silently diverged.

Fix: normalize `node_ids` via `normalize_evidence_separator` (the same
function `validate_evidence` calls) BEFORE handing them to
`_verify_ids_passing`, and pass that SAME normalized list into `add_evidence`
too, so both paths see identical ids and can never diverge again.

Regression test: TestDotFormEvidenceNormalizesBeforePassingCheck deliberately
does NOT monkeypatch `_verify_ids_passing` (unlike this file's other tests)
so the real bucket-matching + run path is exercised with a dot-form id,
asserting it resolves and records identically to its `::` form.

### Changed
```
 src/frob/app/ticket_runner.py      | 25 ++++++++--
 src/frob/tickets/_store.py         | 98 ++++++++++++++++++++++++++++++--------
 tests/test_tickets.py              | 32 +++++++++++++
 tests/test_tickets_evidence_cli.py | 43 +++++++++++++++++
 tickets.md                         | 43 ++++++++++++++++-
 5 files changed, 216 insertions(+), 25 deletions(-)
```

### Evidence
- `tests/test_tickets_evidence_cli.py::TestDotFormEvidenceNormalizesBeforePassingCheck::test_dot_form_id_passes_exactly_like_its_colon_form` (pytest node id, verified passing when recorded)
