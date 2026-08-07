## Done report

Split src/frob/app/ticket_runner.py (3957 lines) into a
src/frob/app/ticket_runner/ package, per the T-1072/T-1076/T-1086
precedent: cohesive command families to private submodules
(_new, _query, _land_cmd, _lifecycle, _close_cmd, _verify, _mutate,
_archive), all re-exported unchanged from __init__.py via __all__ so
every `frob.app.ticket_runner.<name>` call site -- CLI dispatch, and
every test that monkeypatches these names, in any of the several
alias/string forms the test suite actually uses -- keeps working with
zero caller edits.

Two correctness hazards specific to this split, both verified by
running the pre-split suite and diffing failures:

1. Monkeypatch indirection. A name monkeypatched via
   `ticket_runner.<name>` (or a `runner_mod`/`ticket_runner_mod` import
   alias, or the string-dotted-path form) is only visible to a caller
   that looks the name up through the PACKAGE at call time. Any call
   site -- including a same-module call, since "same module" stopped
   meaning the same thing once the body moved to a submodule --
   that the test suite patches this way now does
   `from frob.app import ticket_runner as _ticket_runner; _ticket_runner.<name>(...)`
   instead of a bound import. Found the full set (9 names, not the 3
   an initial `monkeypatch.setattr(ticket_runner, ...)` grep suggested)
   by AST-walking every test file for every import-alias form plus the
   string-setattr form, not by grepping one literal spelling.

2. Logger identity. Several tests filter `caplog.records` by exact
   logger name `"frob.app.ticket_runner"` (test_app_style.py's
   `_info_text`, and caplog.at_level(logger=...) callers). Using
   `get_logger(__name__)` per submodule would silently change every
   moved command's logger name. Every submodule logs under the shared
   `"frob.app.ticket_runner"` name explicitly instead.

Also: DRIFT002 (doc/test frob:describes/frob:tests edges pointing at
the old monolithic file path) re-pointed at the new per-family
submodule paths; ticket scope widened to the new package glob plus the
doc/test files those edges live in; one DUP001 (diff-scoped clone gate
reading a pure file-move as new code, compared against a genuinely
different-domain same-shape helper in tickets/_land.py) waived with a
concrete reason; the monolith's file-level INV006 waiver carried into
every new submodule whose content inherited the exclusivity-vocabulary
prose that waiver covers (the T-1072/T-1086 precedent this ticket's own
plan calls out).

_root_release_manifest, _graph_snapshot stay defined in __init__.py
itself (not moved into the submodule that most often calls them)
specifically so the monkeypatch-indirection story above has one place
those two live; every other split fully relocated its family.

### Changed
```
 docs/design/registry/EXHAUSTIVENESS-GATE.md |    2 +-
 docs/modules/app.md                         |    2 +-
 docs/modules/tickets.md                     |   10 +-
 src/frob/app/ticket_runner.py               | 3957 ---------------------------
 src/frob/app/ticket_runner/__init__.py      |  404 +++
 src/frob/app/ticket_runner/_archive.py      |   45 +
 src/frob/app/ticket_runner/_close_cmd.py    |  675 +++++
 src/frob/app/ticket_runner/_land_cmd.py     |  692 +++++
 src/frob/app/ticket_runner/_lifecycle.py    |  539 ++++
 src/frob/app/ticket_runner/_mutate.py       |  428 +++
 src/frob/app/ticket_runner/_new.py          |  256 ++
 src/frob/app/ticket_runner/_query.py        |  510 ++++
 src/frob/app/ticket_runner/_verify.py       |  950 +++++++
 tests/system/test_cli_ticket_land.py        |    2 +-
 tests/system/test_spawn_budget.py           |    2 +-
 tests/test_ticket_runner_quiet.py           |    4 +-
 tickets.md                                  |   60 +-
 17 files changed, 4568 insertions(+), 3970 deletions(-)
```

### Evidence
- `tests/test_ticket_runner_quiet.py::TestDiagnosticLogCtx::test_default_clamps_frob_tree_but_pins_runner_output` (pytest node id, verified passing when recorded)
- `tests/test_ticket_runner_quiet.py::TestDiagnosticLogCtx::test_verbose_skips_the_clamp` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_land_release.py::TestWriteReleaseBump::test_rewrites_version_and_prepends_changelog_entry` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_land_release.py::TestApplyReleaseBumpForLand::test_bump_applies_writes_and_stamps` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_land_release.py::TestRootReleaseManifestReadsRootHead::test_reads_head_manifest_not_worktree_disk_copy` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_gate_findings.py::TestCheckGateFindingsFn::test_parses_multiple_findings_from_errors_section` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_gate_findings.py::TestSharedCheckSpawnFn::test_check_gates_summary_fn_and_check_gate_findings_fn_share_one_spawn` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: 2 error(s), 954 warning(s), 427 waived
- error-findings: PRE001@tickets/T-1089, TICK006@tickets.md
