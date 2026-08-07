## Done report

Added the DOC004 fenced-code bucket the ticket asked for. C/C++ has no
manifest namespace to key off (python has its package name, rust its
crate, ts its package.json name) so the new bucket resolves a quoted
`#include "..."` directly against this repo's own git-tracked files
instead: resolving to a real tracked file means it is this project's own
surface (UNBOUND if unanchored); resolving to nothing is treated as an
external/illustrative example and skipped, same posture the other three
buckets already take. Angle-bracket system includes are never touched.

Also fixed the LANG003 error this session had been carrying since before
this ticket started: frob.lang._support's c/cpp docblock facet was a
known_gap citing a bogus, non-existent ticket id (T-draft-78a0f919) --
`derive_language_registry` now reports c/cpp as IMPLEMENTED for the
docblock facet (merged into the same "c-cpp" bucket _capability_status
already uses), which is the real fix T-0566 was tracking (the LANG003
citation was the audit trail's own paper trail for this exact gap).

`frob check --ticket T-0566 --base <T-0322's close commit>` is fully
clean (0 errors across every gate, including gate:LANG at 0 errors for
the first time this session).

### Changed
```
 CHANGELOG.md                       |  15 ++
 docs/modules/testing.md            |  24 ++++
 pyproject.toml                     |   2 +-
 src/frob/__main__.py               |  43 +++++-
 src/frob/app/config.py             |   3 +
 src/frob/app/test_runner.py        |  31 ++++
 src/frob/app/ticket_runner.py      |  77 ++++------
 src/frob/gates/__init__.py         |  13 ++
 src/frob/gates/_docblocks.py       |  81 ++++++++++-
 src/frob/lang/_support.py          |  31 ++--
 src/frob/testing/__init__.py       |  10 ++
 src/frob/testing/_coverage_wait.py | 173 +++++++++++++++++++++++
 tests/test_app.py                  | 143 +++++++++++++++++++
 tests/test_docblocks_gate.py       |  88 ++++++++++++
 tests/test_lang_support.py         |  10 ++
 tests/test_prework_parity.py       |  19 +++
 tests/unit/test_main_entry.py      |  45 ++++++
 tickets.md                         | 280 +++++++++++++++++++++++++++++++++++--
 uv.lock                            |   2 +-
 19 files changed, 1010 insertions(+), 80 deletions(-)
```

### Evidence
- `tests/test_docblocks_gate.py::TestCCppNamespace::test_include_of_tracked_header_unanchored_warns` (pytest node id, verified passing when recorded)
- `tests/test_docblocks_gate.py::TestCCppNamespace::test_include_of_tracked_header_anchored_passes` (pytest node id, verified passing when recorded)
- `tests/test_docblocks_gate.py::TestCCppNamespace::test_include_resolving_to_no_tracked_file_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_docblocks_gate.py::TestCCppNamespace::test_angle_bracket_system_include_never_flagged` (pytest node id, verified passing when recorded)
- `tests/test_docblocks_gate.py::TestCCppNamespace::test_waive_suppresses_unbound_c_include` (pytest node id, verified passing when recorded)
- `tests/test_lang_support.py::TestDeriveLanguageRegistry::test_c_and_cpp_docblock_facet_is_implemented` (pytest node id, verified passing when recorded)
