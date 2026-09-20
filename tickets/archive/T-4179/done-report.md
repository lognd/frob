## Done report

Fixed all three compounding defects from F-380.

(1) dry-run mutation: _absorb_pre_land_fixes (_land_cmd.py) now takes
dry_run and threads it through its three sub-steps -- fmt/ruff-format run
in check_only/preview mode, the Tier-A batch (no preview mode of its own,
out of this ticket's scope in _fix_engine.py) is skipped and logged
instead of applied. Proven with a tree-hash-identical-before/after test
(test_ticket_land_dry_run.py).

(2) token split: _fmt_directives._canonical_lines's fallback (no
breakable space within the wrap budget) used to cut at the budget
boundary verbatim, which could land inside a token. It now searches
FORWARD for the token's own end and accepts an over-limit physical line
instead, restoring the T-0991 boundary-space special case as its own
branch so the T-0984/T-0991 regressions still hold. A dedicated
TestNodeIdNeverSplitT4179 fixture reproduces the exact reported shape (a
long frob:tests node id immediately followed by kind="unit").

(3) refusal attribution: _check_uncommitted_waive_deletions now runs each
finding through _attribute_own_fmt_rewrap, which suffixes a finding with
"[frob fmt's own rewrap, not an operator edit]" when
_uncommitted_change_is_own_fmt_rewrap proves the uncommitted diff is
exactly canonicalize_text(HEAD content) -- i.e. the tool's own rewrap, not
a hand edit. Note: with (2) fixed, a legitimate rewrap can no longer
corrupt a waiver past this check's own parser, so the original end-to-end
refusal shape cannot recur; this attribution is now defense-in-depth for
any other rewrap-shaped tool edit, tested directly.

Guard-vs-rewrite ordering (item 4): already correct --
_assert_design_loads_pre_land is called both pre- and post-Tier-A (T-1903
fixed exactly this ordering after the T-1900 incident); no inversion
found.

Scope widened (coordinator-approved widening flow) to include
src/frob/gates/_fmt_directives.py (defect 2's actual implementation) and
tests/test_gates_fmt_directives.py (its existing tests encoded the old
always-under-limit invariant the fix deliberately relaxes for unbreakable
tokens).

Environment note: frob check via the bare .venv/bin/frob binary hit a
CLI-surface-skew collection failure (imports frob.tickets._land from the
PRIMARY checkout, not this worktree, so a brand-new worktree-only symbol
ImportErrors) -- uv run frob (worktree-native) does not have this
problem and was used for evidence binding. --check-repro against
merge-base fails with the documented T-2025 pre-land limitation (new
test not present at any ref without its fix already applied in the same
commit) -- not a real regression.

### Changed
```
 src/frob/app/ticket_runner/_land_cmd.py | 116 +++++++++++--
 src/frob/gates/_fmt_directives.py       |  86 +++++----
 src/frob/tickets/_land.py               |  65 ++++++-
 tests/test_gates_fmt_directives.py      |  88 ++++++++--
 tests/test_ticket_land_dry_run.py       | 297 ++++++++++++++++++++++++++++++++
 tickets/T-4179/ticket.md                |  25 +++
 6 files changed, 605 insertions(+), 72 deletions(-)
```

### Evidence
- `tests/test_gates_fmt_directives.py::TestNodeIdNeverSplitT4179::test_pytest_node_id_directive_value_is_never_split` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land_dry_run.py::TestAbsorbPreLandFixesDryRunIsReadOnly::test_dry_run_leaves_the_worktree_tree_hash_unchanged` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land_dry_run.py::TestAbsorbPreLandFixesDryRunIsReadOnly::test_dry_run_leaves_the_noncanonical_file_byte_identical` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land_dry_run.py::TestAbsorbPreLandFixesDryRunIsReadOnly::test_running_dry_run_twice_is_still_a_noop_both_times` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land_dry_run.py::TestAbsorbPreLandFixesDryRunIsReadOnly::test_real_run_still_rewrites_the_noncanonical_file` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land_dry_run.py::TestOutOfScopeRefusalAttributesOwnFmtRewrap::test_own_fmt_rewrap_is_recognized` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land_dry_run.py::TestOutOfScopeRefusalAttributesOwnFmtRewrap::test_a_genuine_hand_deletion_is_not_misattributed` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land_dry_run.py::TestOutOfScopeRefusalAttributesOwnFmtRewrap::test_a_rewrap_that_stays_parseable_does_not_refuse_at_all` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land_dry_run.py::TestOutOfScopeRefusalAttributesOwnFmtRewrap::test_attribute_helper_suffixes_only_own_rewrap_findings` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land_dry_run.py::TestOutOfScopeRefusalAttributesOwnFmtRewrap::test_attribute_helper_suffixes_an_own_rewrap_finding` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 10 passed (from 10 evidence id(s))
- gates: 10 error(s), 4899 warning(s), 978 waived
- error-findings: ARCH001@src/frob/gates/_fmt_directives.py, COV003@tests/test_gates_fmt_directives.py, DRIFT001@src/frob/doctor.py, LANDFMT001@Would reformat: [1msrc/frob/app/ticket_runner/_land_cmd.py[0m, LANDFMT001@Would reformat: [1mtests/test_ticket_land_dry_run.py[0m, LANDPARITY002@src/frob/gates/_fmt_directives.py, PRE001@tickets/T-4179, REF002@docs/design/macos-portability.md, SELFAUDIT001@tests/test_ticket_land_dry_run.py, WIRE001@tests/test_ticket_land_dry_run.py
