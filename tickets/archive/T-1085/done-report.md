## Done report

Re-measured `frob check --only arch --json` first, filtered to
abstraction-opportunity + `src/frob/app/`: confirmed the same 5 groups the
ticket names. Read every member body per the ticket's own instruction to
check the two duplicate-name groups (`debt_runner.py`'s
`_load_snapshot`/`_load_snapshot`/`_snapshot`, `deploy_runner.py`'s
`_design_dir`/`_design_dir`/...) for a literal same-file duplicate first.

`debt_runner.py`'s group was the genuine extraction: `_load_snapshot(root:
Path)` -- try `frob.graph.load_graph` against a cached `.frob/cache.db`
snapshot, `frob.graph.build_graph` fresh on a miss, `sys.exit(1)` on a hard
build error -- was duplicated BYTE-IDENTICAL (bar the log-message prefix
string) in `debt_runner.py`, `deprecated_runner.py`, AND
`release_runner.py` (`_snapshot`, same shape) -- a genuine third instance
the arch check's own 3-member group didn't even fully list (it grouped by
bare signature `(Path)`, which only shows the members whose signature
literally has no return annotation; `release_runner.py`'s copy has the
same shape under its own `# noqa: ANN202`). `_CACHE_REL = Path(".frob") /
"cache.db"` was ALSO duplicated verbatim across all three.

Extracted both into a new `frob.app._snapshot` module:
`CACHE_REL` (public) and `load_or_build_snapshot(root, *, log_context)`
(public, `log_context` parametrizes the one real difference the three
copies had -- their log message's caller identity: "debt"/"deprecated"/
"release"). Kept the ORIGINAL lazy `from frob.graph import build_graph,
load_graph` INSIDE the function (not hoisted to module level) specifically
because existing tests `monkeypatch.setattr(frob.graph, "build_graph",
...)` and rely on the next call picking up the patched attribute --
verified this the hard way (a first draft hoisted the import and broke
`TestReleaseRunner::test_snapshot_build_graph_err_exits_1`; reverted to
the lazy-import shape and re-ran to confirm green).

`deploy_runner.py`'s duplicate-name group (`_design_dir`/`_design_dir`)
turned out NOT to be a literal same-file duplicate either (confirmed via
`grep -rn "^def _design_dir"` -- one copy each in `deploy_runner.py` and
`sys_runner.py`, genuinely different files/callers) -- left untouched,
out of this ticket's narrowed scope (see below), not silently dropped.

`check_runner.py`'s two `ToolResult`-builder groups and `perf_runner.py`'s
`_heat`/`_collect` group were NOT touched -- deliberately left for a
follow-up pass rather than expanding this ticket's scope further while
`src/frob/app/**` is contended this wave (T-1106's daemon land, the
tickets agent's `ticket_runner.py` work): `check_runner.py` alone is
~640 lines with two separate groups that deserve their own focused read,
and touching it risks a collision with concurrent in-flight work in the
same package.

Scope narrowed from the ticket's original broad `src/frob/app/` to the
exact files touched (`_snapshot.py`, `debt_runner.py`,
`deprecated_runner.py`, `release_runner.py`, plus their real test files
and `docs/modules/app.md`) via `frob ticket scope --remove`/`--add`,
per the dispatch note's contention mitigation -- confirmed via
`git status --porcelain` that only these 4 source files (3 modified, 1
new) plus docs/tickets changed.

Newly-surfaced debt fixed in the same land: AFFECT001 fired on
`deprecated_runner.py::run` (its `docs/modules/gates.md#deprecated-gate-
t-0576` doc anchor, genuinely out of this ticket's own declared scope) --
waived with an honest reason (pure internal refactor, no behavior/output/
gate-semantics change) rather than expanding scope for a doc anchor that
needs no real content change. Two INV006 self-hits from my own new
prose (`_snapshot.py`'s docstring, then the waiver reason text itself)
fixed by rewording to drop the `\bonly\b`/exclusivity match, not by
waiving -- the gate's own first-listed remedy.

Gates (manual `--only` loop, `--ticket T-1085`): gates-fast/gates-native/
static all 0 new errors after the above fixes; the one remaining
gates-fast error (`src/frob/gates/_tracked_files.py::tracked_files`
COV001) is pre-existing, outside this ticket's scope, confirmed present
before this ticket touched anything. `lint`'s 5 ruff-check errors are all
`src/frob/vet/_supplychain.py` (a different agent's recent land,
confirmed via `git log -- <path>`), not this ticket's files -- `ruff
check`/`ruff format --check` on the 4 touched files individually both
pass clean.

Tests: `tests/test_debt_runner.py`, `tests/test_deprecated_runner.py`,
`tests/unit/test_app_runners_batch5.py::TestReleaseRunner`,
`tests/unit/test_app_runners_batch5.py::TestReleaseSyncRunner` -- 21
passed (measured), including the release-runner monkeypatch test that
caught the lazy-import regression above.

### Changed
```
 tickets.md | 3 +--
 1 file changed, 1 insertion(+), 2 deletions(-)
```

### Evidence
- `tests/test_debt_runner.py::TestDebtRunner::test_json_mode_lists_debt_entries` (pytest node id, verified passing when recorded)
- `tests/test_deprecated_runner.py::TestDeprecatedRunner::test_json_mode_lists_deprecated_entries` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch5.py::TestReleaseRunner::test_snapshot_build_graph_err_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch5.py::TestReleaseRunner::test_stamp_success_writes_manifest` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 6 error(s), 578 warning(s), 427 waived
- error-findings: COV001@src/frob/gates/_tracked_files.py, E501@/home/logan/projects/frob/.claude/worktrees/w17-arch/src/frob/vet/_supplychain.py:154, E501@/home/logan/projects/frob/.claude/worktrees/w17-arch/src/frob/vet/_supplychain.py:168, E501@/home/logan/projects/frob/.claude/worktrees/w17-arch/src/frob/vet/_supplychain.py:209, E501@/home/logan/projects/frob/.claude/worktrees/w17-arch/src/frob/vet/_supplychain.py:267, E501@/home/logan/projects/frob/.claude/worktrees/w17-arch/src/frob/vet/_supplychain.py:295
