---
id: T-2110
title: '5 missing exports: judge each on merit (GlobalBinarySkew, global_binary_skew,
  commit_diff, recent_commits, frob_map)'
state: done
kind: bug
origin: agent
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/__init__.py
- src/frob/serve/_tools.py
- src/frob/serve/__init__.py
evidence_scope:
- tests/unit/test_exports.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/serve/__init__.py
  reason: 'T-2110 mid-fix discovery: frob_map''s export gap existed at two levels
    (_tools.py''s own __all__ AND serve/__init__.py''s re-export of it) -- fixing
    only the first still left the src/frob/serve package itself reporting the symbol
    missing'
  actor: logan
  at: '2026-08-10'
evidence:
- tests/unit/test_exports.py::TestFrobExportsPolicyResidue::test_all_nine_packages_report_zero_missing_symbols
designated_repro_test: tests/unit/test_exports.py::TestFrobExportsPolicyResidue::test_all_nine_packages_report_zero_missing_symbols
acceptance:
- text: Given frob-exports' 5 flagged symbols, when test_all_nine_packages_report_zero_missing_symbols
    runs, then it reports zero missing symbols and each symbol's export decision is
    justified individually (usage breadth, existing curation pattern, existing test
    surface), not blanket-added
  evidence:
  - tests/unit/test_exports.py::TestFrobExportsPolicyResidue::test_all_nine_packages_report_zero_missing_symbols
threat: null
component: null
anchor: false
anchor_reason: null
---
GROUP 2: `tests/unit/test_exports.py::TestFrobExportsPolicyResidue::
test_all_nine_packages_report_zero_missing_symbols` reports `frob-
exports` flagging 5 symbols as missing from their package's
`__init__.py`/module `__all__`:
`frob.doctor.global_binary_skew`, `frob.doctor.GlobalBinarySkew`,
`frob.gitio.commit_diff`, `frob.gitio.recent_commits`,
`serve._tools.frob_map`.

Judged each on its merits rather than blanket-adding all five.

## Export (2): `GlobalBinarySkew`, `global_binary_skew`

`frob/__init__.py`'s module docstring documents a deliberate curation
policy: `frob.doctor`'s diagnostics are "used across nearly every
sub-package, so they are surfaced here" (T-0362, T-0599) -- not
"everything public in doctor.py," a curated subset. `DoctorReport`
(already exported) has a field for every OTHER status/diagnostic type
it composes, and every one of those field types is already in
`__all__` (`NativeExtensionStatus`, `DerivedArtifactStatus`,
`MalformedTicketEdge`, `VenvShimDrift`, `LiveLandProcess`) except
`GlobalBinarySkew` (`global_binary: GlobalBinarySkew | None` field,
T-1719) -- a clean, unambiguous gap against the file's own established
pattern, not a judgment call. `global_binary_skew` (the function that
produces it) is the natural companion, matching every other exported
diagnostic's own producer function (`run_diagnosis`,
`scan_venv_shims`, etc.).

## Export, with reservations: `commit_diff`, `recent_commits` (frob.gitio)

Checked actual usage breadth first (`git grep`, not assumption): both
have exactly ONE production call site
(`src/frob/verify/_attribution.py`, imported directly `from frob.gitio
import ...`, never via the top-level `frob` package) -- narrower than
the curation rationale `frob/__init__.py`'s own docstring states
("used across nearly every sub-package") for its existing `gitio`
re-exports. Initially leaned toward leaving these un-exported as a
documented exception.

Reversed on inspecting `TestFrobExportsPolicyResidue`'s own docstring:
it commits this test to exactly two resolutions for any finding --
"a deliberate export ... or a demotion to private (leading underscore,
referrers fixed), never a blanket waiver" -- no third "leave it,
document why" option. Both symbols have their own DIRECT, committed
unit tests (`tests/test_gitio.py::TestCommitDiff`/
`TestRecentCommits`, T-2018) importing them as public `frob.gitio`
API, so demoting to private would break real, intentional test
surface, not just an internal implementation detail -- worse than
narrowly diluting the top-level curation. Given the test's binary
constraint and that the alternative resolution is actively harmful,
export both.

## Export (1): `serve._tools.frob_map`

`_tools.py` already curates its own `__all__` (13 `frob_*` MCP-tool-
style functions). `frob_map` is registered in `_socketd.py`'s real
tool-dispatch table (`"frob_map": _tools.frob_map`) exactly like every
already-exported sibling (`frob_affects`, `frob_check_delta`, etc.) --
same naming shape, same dispatch wiring, same "real tool a client can
call" status. Clean, unambiguous omission, not a judgment call.

## Plan

Add all 4 top-level symbols (`GlobalBinarySkew`, `global_binary_skew`,
`commit_diff`, `recent_commits`) to `frob/__init__.py`'s import +
`__all__`. Add `frob_map` to `src/frob/serve/_tools.py`'s `__all__`
(already imported/defined there, no import to add).