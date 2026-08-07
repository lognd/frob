## Done report

Registered "deprecated" in `_ALL_GATES` and `_CANONICAL_GATE_ORDER`
(src/frob/gates/__init__.py) -- deprecated_gate's dispatch-table lambda
already existed but was unreachable since T-0576 because the gate name
was never added to the selectable set. Also added "deprecated" to the
"gates-fast" stage group in src/frob/check/__init__.py: this file was
structurally necessary (not originally in scope) because
test_available_stages_cover_every_gate_and_tool asserts every
_ALL_GATES member lands in some _STAGE_GROUPS alias -- added via
`frob ticket scope T-0797 --add src/frob/check/__init__.py --reason ...`
per the sanctioned scope-expansion mechanism, not silently.

Added two regression tests to TestDeprecatedGate in tests/test_gates.py:
test_deprecated_is_registered_in_all_gates (locks membership) and
test_deprecated_fires_through_real_gate_dispatch (end-to-end run_gates
with no --only filter, proving DEPR003 actually surfaces through real
dispatch, not just via a direct deprecated_gate() call).

Deviation from the ticket's predicted output: a real, unscoped
`frob check --only deprecated` on this repo now reports 4 DEPR002
errors, not the 4 DEPR003 in-window warnings the dispatch anticipated.
Cause: the T-0580 deprecation directives (map/outline/xref/docs-search
navigation commands) are bound via `ticket="T-0580"`, and T-0580 itself
is now closed/done -- DEPR002 fires because the bound ticket is no
longer open. This is correct new-gate behavior surfacing a real,
previously-invisible problem (catalogued-is-not-enforced), not a defect
in this ticket's registration. Filed T-0802 (rebind folded into this ticket at land; the interim draft was dropped as absorbed) (rebind the four
T-0580 frob:deprecated directives to a new open ticket) rather than
fixing it here -- out of this ticket's declared scope
(src/frob/app/{xref,outline,docs,map}_runner.py).

`uv run --frozen frob test` (full, unscoped, foreground) shows a large
set of pre-existing failures in unrelated areas (native/strata sys
audit, doctor, compliance registry, cli_check assorted) that reproduce
on this worktree's checked-out main independent of this change -- not
investigated further as out of scope for a 2-file (+1 scope-expansion)
gate-registration ticket. The touched-set verification below is what
this ticket's own change is judged against.

Fold (coordinator-directed, post-initial-report): merged main (brings
T-0802, the sunset-execution ticket, and reconciles the earlier-flagged
tests/unit/graph/test_cache.py main-advance). Scope-added the four
navigation runner files (map/outline/xref/docs_runner.py) with reason
"DEPR002 rebind: directives must cite an open ticket; T-0802 is the
sunset-execution ticket", rebound each frob:deprecated directive's
ticket= from the closed T-0580 to the open T-0802. Dropped
T-0802 (rebind folded into this ticket at land; the interim draft was dropped as absorbed) as absorbed-by T-0797 (its fix landed here instead of
as a separate ticket). `frob check --only deprecated` now shows 0
errors, 4 DEPR003 in-window warnings, matching the ticket's original
acceptance criterion exactly.

### Changed
```
 src/frob/check/__init__.py |  2 +
 src/frob/gates/__init__.py |  7 ++++
 tests/test_gates.py        | 36 +++++++++++++++++
 tickets.md                 | 96 ++++++++++++++++++++++++++++++++++++++++++++--
 4 files changed, 137 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestDeprecatedGate::test_deprecated_is_registered_in_all_gates` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDeprecatedGate::test_deprecated_fires_through_real_gate_dispatch` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_check.py::TestCheckStageGroups::test_available_stages_cover_every_gate_and_tool` (pytest node id, verified passing when recorded)
