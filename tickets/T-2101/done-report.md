## Done report

### Changed
src/frob/gates/_fix_engine_sync.py::_archive_design_dir_at_head
src/frob/gates/_fix_engine_sync.py::_frob_toml_tracked_at_head
tests/test_gates.py::TestFixEngineTierA.test_sys111_before_snapshot_excludes_litmus_like_the_live_tree

### Evidence
tests/test_gates.py::TestFixEngineTierA::test_sys111_before_snapshot_excludes_litmus_like_the_live_tree

Full TestFixEngineTierA re-verified: 20 passed.

### Investigation and verdict (coordinator's question: same defect as
### the 23-vs-25 self-model drift, or two?)

TWO SEPARATE DEFECTS, confirmed by direct reproduction of each in
isolation:

Defect A (this ticket): `_capability_counts_at_head`'s `git archive
HEAD -- design` (SYS111 capability-ratchet Tier-A sync, T-2001) never
carried `frob.toml` into its scratch extraction, so
`frob.excludes.load_exclude_globs` found no config there and returned
`()`. `design/litmus/**`'s fixture pairs (`payments.strata`/
`payments_hardened.strata`, `audit_hardened.strata`/`audit_vuln.strata`)
deliberately reuse the same node ids across files by design (T-0130
litmus fixtures, before/after variants of the same scenario) -- with no
exclude applied, both merge into one synthetic "design" module and hit
`_validate_no_duplicates`'s `DuplicateId` fail-closed path, logged at
ERROR (`duplicate node id(s) in module design: ['api', 'audit',
'browser', ...]` -- the exact live text three agents independently
flagged). Confirmed none of the 12 colliding ids overlap frob's own
real `design/frob.strata` node set at all. Confirmed the live/current
tree call (`load_design_ids(Path("."), "design")`, frob.toml present)
already excludes litmus correctly and elaborates cleanly (25 nodes, 0
errors) -- the defect was isolated to the scratch-archive path
specifically.

Functionally this did NOT crash anything (`_capability_counts_at_head`
treats `ids.errors` as "no BEFORE baseline" and returns `{}`), but it
silently defeated T-2001's own attribution feature every single land
(every capability-growth site reads as "this land caused it," since
there is never a real BEFORE count to diff against) and printed a scary
unwaived ERROR line on every land.

Defect B (filed separately as T-2102, NOT touched by this ticket):
`tests/system/test_frob_self_model.py`'s `_model` fixture parses ONLY
`design/frob.strata` directly (`parse_module`/`elaborate`, single file,
no merge, no litmus anywhere in that path) -- structurally unrelated to
Defect A. The 23-vs-25 node count is organic model growth (2 real nodes
added since the docstring was last hand-updated), not id corruption.
Left for T-2102 per the coordinator's explicit request to decide the
golden-vs-invariant question there, not conflate it with this fix.

### Fix
`_archive_design_dir_at_head` now also archives `frob.toml` alongside
`design/` when it is tracked at HEAD (new helper
`_frob_toml_tracked_at_head`, since `git archive` fails its WHOLE run
if any one pathspec matches nothing -- verified directly with a
throwaway git repo before relying on the fallback). Falls back to
`design/` alone when `frob.toml` is not tracked at HEAD (a bootstrap
commit, or a consumer repo with no `frob.toml`), preserving the
pre-fix behavior exactly for that case rather than losing the BEFORE
snapshot outright.

### Gates
`frob ticket evidence --check-repro` against the test-only commit
(`a1e3e98e470ce9c3584ccf2b0790ea20f9a968ab`, per playbook 7b's split-
commit technique -- the default parent resolution landed on an
unrelated already-squashed ticket commit and correctly refused
TEST_ABSENT_AT_PARENT, so `--base-ref` was passed explicitly): genuine
FAILED_AT_PARENT, confirmed before designating.

Filed: T-2102 (self-model golden-count drift, Defect B, sibling
investigation from the same coordinator request -- explicitly NOT this
ticket's scope).

### Changed
```
 src/frob/gates/_fix_engine_sync.py | 46 +++++++++++++++++++++++++++++++-------
 tests/test_gates.py                | 46 ++++++++++++++++++++++++++++++++++++++
 tickets/T-2101/ticket.md           |  9 +++++---
 3 files changed, 90 insertions(+), 11 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestFixEngineTierA::test_sys111_before_snapshot_excludes_litmus_like_the_live_tree` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: PRE001@tickets/T-2101
