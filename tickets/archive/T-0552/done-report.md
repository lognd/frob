## Done report

docs/audits/gates-accounting.md B3/E3: `_edge_has_execution_evidence` grants
full TEST001-004 execution credit to a ts/c/cpp `frob:tests` edge purely by
name/path convention (`_is_native_test_symref` + snapshot resolution) --
frob runs no vitest/ctest/etc collector, so an empty `void test_foo(){}`
was silently indistinguishable from a genuinely executed test.

Right-way fix direction per the audit was either (a) wire real TS/C/C++
collectors, or (b) mark the credit as an explicit degraded "unverified"
state instead of a silent pass. (a) requires new runner infrastructure in
`src/frob/testing/` -- out of this ticket's `src/frob/gates/` scope, and
building it well needs its own design pass, so not filed as a follow-up
(T-draft-2411b5b6 (never refiled), "Wire real TS/C/C++ test collectors (vitest/ctest) into
gate evidence", scope `src/frob/testing/`).

Implemented (b) within scope:
- Split the native-fallback check out of `_edge_has_execution_evidence`
  into `_edge_is_native_unverified` (same logic, just named and reusable).
- New gate TEST013 (WARN): fires once per TESTS edge whose ONLY credit is
  that structural fallback, naming the edge and stating plainly that it is
  "unverified, not proven test coverage."
- Deliberately did NOT withdraw the underlying TEST001-004 credit --
  `_valid_edges`/`_edge_has_execution_evidence` are unchanged in what they
  grant. Withdrawing credit outright, with no real collector to replace it,
  would flip every native-language public symbol across every sibling repo
  using this fallback to a TEST001 ERROR overnight for a structural change
  alone, not a real regression -- the same reasoning T-0545's TEST012 used
  for why that gate is WARN, not ERROR, on first landing.

Honest split (LARGE ticket): the actual collector wiring (the durable fix)
and the follow-up question of whether TEST013 should later promote to
ERROR once collectors exist are both left to T-draft-2411b5b6 (never refiled), noted in
that ticket's body.

### Changed
```
 CHANGELOG.md                |  19 +++++
 frob.lock                   |   2 +-
 pyproject.toml              |   2 +-
 src/frob/gates/__init__.py  |  91 +++++++++++++++++++++---
 src/frob/gates/_coverage.py | 125 ++++++++++++++++++++++++++++++++-
 tests/test_gates.py         | 125 ++++++++++++++++++++++++++++++++-
 tickets.md                  | 165 ++++++++++++++++++++++++++++++++++++++++++--
 uv.lock                     |   2 +-
 8 files changed, 510 insertions(+), 21 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestTest013NativeUnverified::test_fires_on_structural_only_edge` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTest013NativeUnverified::test_silent_on_executed_edge` (pytest node id, verified passing when recorded)
