## Done report

`_evidence_collected` (`src/frob/gates/__init__.py`) now tries exact
node-level resolution FIRST (`matches_collected`, unchanged, still the
preferred/most precise granularity), and only when that fails and the
evidence id carries no `::` at all (`_is_path_level_evidence`) falls back
to a new `_path_level_evidence_collected`: resolves iff >=1 collected node
id lives under the bare path, either as that exact file
(`<path>::...` prefix) or inside that directory (`<path>/...` prefix).
Deliberately non-vacuous per the ticket's acceptance criteria: a path with
zero matching collected node ids (typo'd id, deleted/nonexistent
directory) still fails COV003 -- only a real, non-empty match resolves.

Node-level evidence is entirely unaffected (tried first, same code path as
before); this is purely an additional fallback, never a replacement.

Not in scope / not touched: the sibling malformed-id shape mentioned in
this ticket's own body (an id with `kind="unit"` embedded as a trailing
attribute rather than a bare path) is a different failure mode --
malformed-at-record-time schema validation, not a resolvable path -- and
belongs with T-0293's record-time normalization/rejection work
(`frob.tickets`, out of this ticket's declared scope which is
`src/frob/gates/__init__.py` + `src/frob/testing/**`, not `frob.tickets`).
Not filing a new ticket since T-0293 already exists and covers exactly
that shape.

Changed:
- src/frob/gates/__init__.py::_is_path_level_evidence (new)
- src/frob/gates/__init__.py::_path_level_evidence_collected (new)
- src/frob/gates/__init__.py::_evidence_collected (extended: node-level
  first, path-level fallback)
- docs/modules/gates.md (COV003 row + new T-0298 note documenting the
  file-/directory-level resolution rule and its non-vacuous guarantee)

Evidence:
- tests/test_gates.py::TestCoverageGate::test_cov003_passes_for_file_level_evidence
- tests/test_gates.py::TestCoverageGate::test_cov003_passes_for_directory_level_evidence
- tests/test_gates.py::TestCoverageGate::test_cov003_rejects_empty_directory_level_evidence
- tests/test_gates.py::TestCoverageGate::test_cov003_prefers_node_level_over_path_level

Filed: none.

Gates: `uv run pytest tests/test_gates.py -q` 138 passed. `uv run frob
check --ticket T-0298` (after re-sweep) shows only pre-existing,
out-of-scope items: TEST006 (no coverage stamp -- full-suite `make
coverage` deferred to the coordinator per the playbook) and ARCH001 on
`src/frob/dup/_template.py` (pre-existing, unrelated file). No new
violations attributable to this change.
