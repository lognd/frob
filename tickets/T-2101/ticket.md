---
id: T-2101
title: SYS111 capability-ratchet BEFORE snapshot drops frob.toml, litmus fixtures
  leak into merged design and fail closed with DuplicateId
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
- src/frob/gates/_fix_engine_sync.py
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestFixEngineTierA::test_sys111_before_snapshot_excludes_litmus_like_the_live_tree
designated_repro_test: tests/test_gates.py::TestFixEngineTierA::test_sys111_before_snapshot_excludes_litmus_like_the_live_tree
acceptance:
- text: Given design/litmus/** fixture files declaring colliding node ids across files,
    when fix_sys111_capability_ratchet_sync computes its BEFORE snapshot via git archive
    of HEAD, then frob.toml's [graph].exclude travels with the archive so litmus is
    excluded and load_design_ids reports 0 errors, matching the live/current-tree
    load_design_ids call
  evidence:
  - tests/test_gates.py::TestFixEngineTierA::test_sys111_before_snapshot_excludes_litmus_like_the_live_tree
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
GROUP 3 investigation, requested by the coordinator: establish whether
the `ERROR: duplicate node id(s) in module design: ['api', 'audit',
'browser', 'browser_kid', 'dashboard', 'gateway', 'ledger', 'refund',
'replica', 'stripe', 'web', 'webhookq']` seen at real land time and
`tests/system/test_frob_self_model.py`'s 23-vs-25 `len(_model.nodes)`
drift are the SAME defect or two. They are TWO DIFFERENT, UNRELATED
defects.

## Defect A (real bug, this ticket's fix): the duplicate-id ERROR

Root-caused and reproduced directly (not from the symptom): a live
`uv run python` repro that runs `frob.gates._fix_engine_sync.
_capability_counts_at_head`'s own extraction step -- `git archive
--format=tar HEAD --output ... -- design`, extracted into a scratch
temp dir, then `load_design_ids(extract_dir, "design")` -- reproduces
the EXACT error text and exact id list byte for byte.

`_archive_design_dir_at_head` (SYS111 capability-ratchet Tier-A sync,
T-2001) archives ONLY the `design/` pathspec at `HEAD` into a scratch
dir to compute a BEFORE snapshot. `frob.toml` (which carries `[graph]
exclude = ["design/litmus/**", ...]`) is never carried into that
scratch dir. `frob.excludes.load_exclude_globs(root)` returns `()`
when `root/frob.toml` does not exist (verified directly in
`src/frob/excludes.py::load_exclude_globs`), so
`frob.strata._design_load._strata_files` walks and parses EVERY
`.strata` file under the scratch `design/`, including
`design/litmus/**` -- frob's own litmus fixture models (T-0130), never
meant to be treated as part of the maintained architecture surface.
Two litmus fixture pairs (`payments.strata`/`payments_hardened.strata`,
and similarly the audit pair) are BEFORE/AFTER variants of the SAME
scenario and deliberately reuse the same node ids across files by
design -- exactly the id list observed in the error
(`api`/`stripe`/`webhookq`/`refund`/... -- none of which exist in
frob's own `design/frob.strata`, confirmed: none of the 12 collided ids
overlap frob's own node id set, which is
`cli`/`graphlang`/`security`/`verify`/.../`frob_core_native`/
`tickets_ledger`). Merging those files into one synthetic `"design"`
module (`elaborate_merged`'s default `name="design"`) hits
`_validate_no_duplicates` and fails closed with `StrataError.
DuplicateId`, logged at ERROR by `_elaborate.py::_validate_no_
duplicates`.

Functionally this does NOT crash or corrupt anything: `_capability_
counts_at_head` treats `ids.errors` as non-empty and returns `{}` (its
own documented "nothing existed here at HEAD" fallback), so
`fix_sys111_capability_ratchet_sync` runs with an EMPTY before-snapshot
every single land, which silently defeats the whole point of T-2001's
handler (attributing ratchet growth to THIS land specifically vs. a
pre-existing breach) -- every land's capability growth reads as "this
land's own diff caused it" because there is never a real BEFORE
baseline to diff against. The loud, unwaived ERROR log line is also its
own cost: three separate agents (including this one) have now
independently flagged it as a signal worth investigating, at ERROR
severity, on every land, for a condition that is completely benign to
frob's own architecture and 100% attributable to litmus fixtures never
meant to participate in this model at all.

Confirmed via git ancestry / direct reproduction, not assumption: the
live repo's own `load_design_ids(Path("."), "design")` (frob.toml
present) elaborates cleanly with 0 errors and 25 real nodes -- litmus is
correctly excluded THERE. The defect is specific to the scratch-archive
path that drops `frob.toml` along the way.

Fix: also archive `frob.toml` alongside `design/` in `_archive_design_
dir_at_head`'s `git archive` pathspec, so the extracted scratch dir
carries the SAME `[graph].exclude` configuration `load_exclude_globs`
needs, and litmus fixtures are excluded from the BEFORE snapshot exactly
as they already are from the live/current one.

## Defect B (separate, NOT this ticket's fix -- filed as a follow-up):
`test_frob_self_model.py`'s hardcoded golden counts

`_model` in that test file parses ONLY `design/frob.strata` directly
(`parse_module`/`elaborate`, a single file, no merge, no litmus
involved at all) -- structurally unrelated to Defect A's merge-time
litmus leak. `len(_model.nodes) == 23` is simply stale: the live model
elaborates to 25 nodes today (measured directly), a routine, disclosed
addition (this same test file's own multi-paragraph running commentary
shows this exact "landed a node, forgot to bump the docstring counter"
pattern recurring at T-0707, T-0864, T-1329, T-1591, T-1735, and
presumably again since T-1735 -- an established, repeatedly-paid
maintenance cost, not a one-off).

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
