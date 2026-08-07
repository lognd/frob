## Done report

Changed:
tests/test_capability_registry.py::TestPerOperationFireFixtures (new class)
tests/test_capability_registry.py::_fire_snippet (new helper)
tests/test_capability_registry.py::_LANG_EXT (new fixture data)
tests/test_capability_registry.py::_BENIGN_SOURCE (new fixture data)
tests/test_capability_registry.py::_PER_OPERATION_IDS (new fixture data)

Approach: three tests are parametrized DIRECTLY over `DANGEROUS_OPERATIONS`
itself (not a hand-maintained fixture tuple like the pre-existing
`_FIRE_FIXTURES`), so a new registry entry automatically gets its own
needle-based fire fixture with zero manual test authoring. `_fire_snippet`
generates a minimal source file from the entry's own `needles[0]` (or, for
the one no-needle entry -- python bare `compile()` -- a literal bare
builtin call matched via `_has_bare_compile_call`); it raises loudly for
any future no-needle entry it does not have a generation strategy for,
rather than silently skipping it. Per entry: (1) `scan_file_operations`
must name that EXACT entry object (identity via pydantic frozen-model
equality, not just a shared capability_kind), (2) `scan_file_capabilities`
must observe its `capability_kind`, (3) a negative fixture against
per-language benign source (`_BENIGN_SOURCE`) proves the entry does NOT
fire when none of its needles are present -- T-0145's "prove the negative
too" lesson applied per-entry instead of per-cell. This covers all 71
DANGEROUS_OPERATIONS entries (3 tests x 71 = 213 parametrized cases) as of
this ticket, and any future addition is auto-covered.

Evidence: 284 tests collected under tests/test_capability_registry.py, all
pass (`uv run pytest tests/test_capability_registry.py -q`). Bound via
`frob ticket evidence T-0182`:
- tests/test_capability_registry.py::TestPerOperationFireFixtures::test_entry_fires_scan_file_operations
- tests/test_capability_registry.py::TestPerOperationFireFixtures::test_entry_fires_scan_file_capabilities
- tests/test_capability_registry.py::TestPerOperationFireFixtures::test_entry_absent_from_benign_source

Filed: none (no out-of-scope defect found in src/frob/vet/** while writing
fixtures; every DANGEROUS_OPERATIONS entry's needle(s) fired cleanly
against a minimal snippet built from itself).

Gates: `uv run pytest tests/test_capability_registry.py -q` clean (284
passed). `uv run frob check` / `uv run frob test` results recorded
separately by the coordinator per the review-gated close policy on this
ticket.
