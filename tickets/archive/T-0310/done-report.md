## Done report

Changed:
- src/frob/strata/_selfconform.py::_fully_excluded_node_ids (new)
- src/frob/strata/_selfconform.py::_stale_design_violations (skip wired in)
- docs/strata/selfconform.md#sys101-fully-excluded-nodes (new anchor)
- tests/unit/strata/test_selfconform.py::TestStaleDesign::test_stale_design_skips_node_fully_within_graph_exclude (new)
- tests/unit/strata/test_selfconform.py::TestStaleDesign::test_stale_design_still_fires_when_node_has_non_excluded_file (new)
- tickets.md: T-0310's own `scope` field was malformed (a single
  comma-joined string in a one-item YAML list instead of five separate
  glob entries), which made SCOPE001 reject this ticket's own in-scope
  files. Corrected to a proper 5-entry list -- same file set the ticket
  already declared, no scope expansion.

Fix, precisely: `_fully_excluded_node_ids(model, root)` walks every real,
skip-dir-filtered file once, then for each node with a `code=` glob,
computes the raw fnmatch-match set (ignoring exclude) and checks: (a) at
least one file matches the glob at all, AND (b) every matched file is
excluded via the SAME `load_exclude_globs`/`is_excluded` pair
`_sorted_capability_files`/`_capability_binding` already use for
observation (T-0274). Only nodes satisfying both are added to the skip
set; `_stale_design_violations` skips SYS101 entirely for any node in
that set (before the declared/observed diff runs), and an INFO log line
names the node id and matched-file count so the skip is visible, not
silent. A node whose glob matches nothing at all (typo, empty dir) is
NOT skipped -- unaffected, pre-existing SYS101 behavior, per the ticket's
"do not weaken for a glob matching nothing" distinction. A node with even
one non-excluded observable file is NOT skipped -- SYS101 still fires
normally for a genuinely-unobserved declared capability on that node
(`test_stale_design_still_fires_when_node_has_non_excluded_file` proves
this directly).

Inverse graphite finding (bind_code over-attributing bundled-JS
capabilities to a server node via raw-FS walk) is CONFIRMED already
reconciled, not newly fixed here: `_sorted_capability_files` (feeds
`_capability_binding`, the binding SYS100/SYS101 both observe through)
already calls `load_exclude_globs`/`is_excluded` before including a file
(T-0274, unchanged by this ticket). `_fully_excluded_node_ids` calls the
identical two functions from `frob.excludes`. Observation and the SYS101
skip therefore structurally cannot diverge -- they are the same exclude
source, not two independently-maintained copies. No code change was
needed for the inverse direction; `docs/strata/selfconform.md
#sys101-fully-excluded-nodes` states this explicitly.

Litmus tests (both in `TestStaleDesign`, tests/unit/strata/
test_selfconform.py):
- `test_stale_design_skips_node_fully_within_graph_exclude` -- a node
  whose `code=` glob matches only a graph-excluded path produces NO
  SYS101 for its declared `may "net"`.
- `test_stale_design_still_fires_when_node_has_non_excluded_file` -- the
  same node shape but with one additional non-excluded file still
  produces SYS101 for the same undeclared-vs-observed gap -- proves the
  skip does not over-apply.

Evidence:
- tests/unit/strata/test_selfconform.py::TestStaleDesign::test_stale_design_skips_node_fully_within_graph_exclude
- tests/unit/strata/test_selfconform.py::TestStaleDesign::test_stale_design_still_fires_when_node_has_non_excluded_file
- tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant
  (full strata suite green against the real repo tree; no non-excluded
  node regressed to a new SYS101)

Filed: none (no out-of-scope discoveries beyond the ticket's own
malformed scope field, corrected above within declared scope since
tickets.md is already in scope).

Gates: `uv run pytest tests/unit/strata/test_selfconform.py -q` -- 34
passed. `uv run pytest tests/unit/strata -q` -- 622 passed (full strata
suite, no regression). `uv run ruff check` and `ruff check` (both PATH
and project-pinned) clean on `src/frob/strata/_selfconform.py` and
`tests/unit/strata/test_selfconform.py`. `uv run ruff format --check`
clean (both binaries). `uv run ty check src/frob/strata/_selfconform.py`
clean. `make coverage` -- full suite green, coverage stamp refreshed
(source_sha=a4d62752). `uv run frob check --ticket T-0310` -- 0 errors, 0
warnings, 204 pre-existing waived (unchanged waiver count). `git diff
main --diff-filter=D --stat` empty (deletion-filter clean).

Worktree: /home/logan/projects/frob/.claude/worktrees/agent-a02cb65092df565ac,
based on main tip f35cd4a (merge confirmed no-op, already current).
Not closed -- left for reviewer per the review-gated flow.
FROBLEMS (aprog-public, graphite, lograder): _selfconform file-discovery honors [graph].exclude (T-0274), which is correct, but a node whose code glob resolves ENTIRELY to excluded paths can never have any declared 'may' capability observed -> SYS101 'declared but never observed' fires permanently, unfixable by touching content (no non-excluded file exists to add a site to). Repos waived per-capability. Also graphite reported the INVERSE (bind_code over-attributing bundled-JS capabilities to a server node because it walked raw FS) -- the two must be reconciled into one coherent exclude-aware observation rule. Fix: SYS101 should skip (or explicitly annotate) a node whose entire code-glob set is excluded -- nothing can ever be observed there. Litmus: a node globbing only excluded paths yields no SYS101.
