## Done report

T-1201 delivers `frob refactor split`: chunked move of N symbols out of a
source module into a new sibling module, generating a re-export shim in
the source module so external `from source import symbol` call sites
need no edit, built directly on T-1197's build_plan/apply_plan pipeline
(with T-1199/T-1200/T-1267's carriers already wired into it).

New src/frob/refactor/_split.py: chunk_symbols (order-preserving grouping),
build_reexport_shim_op (T-1072/T-1077-style `from DEST import (...)  #
noqa: F401` block), _plan_chunk/_run_chunk (merge each chunk's per-symbol
build_plan output into one apply/verify/commit-or-rollback transaction),
run_split (the whole pipeline: chunk, then run each chunk in order,
stopping after the first failed chunk without touching earlier committed
chunks), ChunkReport/SplitReport (disclosed report models).

_dedupe_equivalent_import_ops handles the one real cross-symbol hazard a
chunk introduces that a single move never hits: two symbols moved out of
the SAME source module in the same chunk each independently plan a full
rewrite of the shared `from source import a, b` line; since both
rewrites resolve to the same name set (just reordered), they are
collapsed to one op instead of tripping apply_plan's overlapping-rewrite
refusal (a real, different-content conflict is still left alone, so
apply_plan's own refusal still fires for a genuine collision).

Extracted src/frob/refactor/_gitops.py (current_sha/git/working_tree_clean)
out of _transaction.py so _split.py's own per-chunk transactions reuse
the identical git primitives instead of a second copy (CLAUDE.md's
no-duplication rule); _transaction.py now imports from _gitops instead
of defining its own private copies -- no behavior change to run_refactor.

CLI: `frob refactor split SOURCE_MODULE --symbols a,b,c --into
DEST_MODULE [--alias-conflict ...] [--chunk-size N]` wired into
src/frob/refactor/_cli.py's add_refactor_parser/run_refactor_command
(same ready-to-wire-but-not-yet-connected-to-frob.__main__ status as
move/rename, per T-1197's own CLI wiring status note).

Changed:
- src/frob/refactor/_split.py (new)
- src/frob/refactor/_gitops.py (new)
- src/frob/refactor/_transaction.py (git/working_tree_clean/current_sha
  extracted to _gitops, no other change)
- src/frob/refactor/_cli.py (split subcommand + _run_split_command)
- src/frob/refactor/__init__.py (re-exports)
- docs/commands/refactor.md (Split verb section + new anchors)
- tests/test_refactor.py (TestSplitChunking, TestSplitReexport,
  TestRunSplit, TestCli.test_add_refactor_parser_registers_split)

Evidence:
- tests/test_refactor.py::TestRunSplit::test_split_moves_symbols_and_leaves_reexport_shim (accepts 0)
- tests/test_refactor.py::TestRunSplit::test_split_chunk_failure_does_not_touch_later_chunks (accepts 1)
- tests/test_refactor.py::TestCli::test_run_refactor_command_dispatches_split_end_to_end (bound, mutation-kills _cli.py)
- tests/test_refactor.py::TestCli::test_run_refactor_command_split_refusal_exit_code (bound, mutation-kills _cli.py)
- tests/test_refactor.py::TestSplitChunking::test_chunk_symbols_preserves_order_and_size (supporting)
- tests/test_refactor.py::TestSplitChunking::test_chunk_symbols_clamps_nonpositive_size_to_one (supporting)
- tests/test_refactor.py::TestSplitReexport::test_shim_op_imports_every_moved_name (supporting)
- tests/test_refactor.py::TestRunSplit::test_dirty_working_tree_refuses (supporting)
- tests/test_refactor.py::TestCli::test_add_refactor_parser_registers_split (supporting)
- Full tests/test_refactor.py: 63 tests, all pass
  (uv run pytest tests/test_refactor.py -q)

Filed: none

Gates: uv run frob check --only lint/gates-fast --ticket T-1201 --
gate:AFFECT, gate:DOC, gate:FMT (own files), gate:TEST all clean for
this ticket's own files. Remaining gate:COV/PRE/REG/SCOPE errors in the
full-repo run are pre-existing findings unrelated to this diff (other
in-flight tickets' own files: src/frob/gates/_fix_engine_tier_c.py,
tests/test_gates.py TestFixEngineTierB/TierC, docs/design/registry/
check-coverage.yaml's REG005/007 denominator drift, uv.lock/pyproject.toml/
.frob-release.json/CHANGELOG.md land-owned-file staleness) -- confirmed by
diffing this ticket's own touched-file set, none of which appear in this
list. ruff/ty findings pre-existing in src/frob/refactor/_directives.py,
_prose.py, and tests/test_refactor.py:860/868 (T-1199/T-1200's own files,
untouched by this diff) are likewise not from this change.

`frob ticket close T-1201` blocks ONLY on REL001's version-bump half
(needs 0.322.0) -- land-owned per agent-playbook.md sec 4b, resolved by
`frob ticket land`, not by this worktree. TEST016's mutation-evidence
gate on src/frob/refactor/_cli.py (the split dispatch branch and its new
argparse wiring) is now clean: added
TestCli::test_run_refactor_command_dispatches_split_end_to_end and
TestCli::test_run_refactor_command_split_refusal_exit_code, which
exercise `run_refactor_command`'s split-dispatch branch and
`_run_split_command` end to end through a real fixture repo (added
`--skip-pytest-collect`/`--skip-check-delta` split CLI flags, mirroring
move/rename's own, so this is possible without a full pytest/frob-check
subprocess in the test).

Disclosed cuts / honest scope notes:
- A repo-wide `git merge main` was attempted mid-ticket to refresh the
  SCOPE/PRE gate baseline (main had advanced with T-1263's land) but hit
  a CHANGELOG.md merge conflict; per agent-playbook.md sec 4b, CHANGELOG.md
  is land-owned and a worktree commit touching it is mechanically refused
  -- the merge was aborted (`git merge --abort`) rather than working
  around the guard. This ticket's own diff and tests are unaffected;
  the coordinator's land will pick up the real current main state.
- _dedupe_equivalent_import_ops resolves same-span import-rewrite
  conflicts only when the resulting name sets are IDENTICAL
  (order-insensitive) -- a genuinely different conflicting rewrite at the
  same span is left alone and still correctly refused by apply_plan's own
  OverlappingRewrites check, per design.

### Changed

### Changed
```
 design/frob.strata                |  11 +
 docs/commands/refactor.md         |  81 ++++++
 src/frob/refactor/__init__.py     |  12 +
 src/frob/refactor/_cli.py         | 125 ++++++++-
 src/frob/refactor/_gitops.py      |  60 +++++
 src/frob/refactor/_split.py       | 514 ++++++++++++++++++++++++++++++++++++++
 src/frob/refactor/_transaction.py |  56 +----
 tests/test_refactor.py            | 314 ++++++++++++++++++++++-
 tickets.md                        | 151 ++++++++++-
 9 files changed, 1267 insertions(+), 57 deletions(-)
```

### Evidence
- `tests/test_refactor.py::TestRunSplit::test_split_moves_symbols_and_leaves_reexport_shim` (pytest node id, verified passing when recorded)
- `tests/test_refactor.py::TestRunSplit::test_split_chunk_failure_does_not_touch_later_chunks` (pytest node id, verified passing when recorded)
- `tests/test_refactor.py::TestCli::test_run_refactor_command_dispatches_split_end_to_end` (pytest node id, verified passing when recorded)
- `tests/test_refactor.py::TestCli::test_run_refactor_command_split_refusal_exit_code` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
