## Done report

Built `frob.serve._warm` (WarmState/repo_dirty_key/warm_state/invalidate): an
in-process, per-repo-root cache of the graph snapshot, stamped baseline, and
collected python test ids, keyed by a cheap `git rev-parse HEAD` + `git status
--porcelain` signature (excluding `.frob/` via pathspec, since build_graph/
collect_python_tests write it as a side effect of the very build this key
gates) plus a per-dirty-path `(mtime_ns, size)` tag (closing a real gap:
porcelain alone never reports an untracked file's own content change). Added
two MCP tools on top: `frob_check_delta` (new-since-baseline violations from a
full `run_gates` pass, using `delta_violations`/`is_baseline_stale`, plus a
`verify=True` mode that drops the warm cache and cross-checks a fully cold
re-run) and `frob_run_touched_tests` (select + run the touched-set tests for a
base ref, wrapping `select_tests`/`run_selected`). Packaging: `[serve]` was
already a proper pyproject extra; reconciled `make install-tool` to install it
via `--extra serve` instead of a second, independently-pinned `--with
"mcp>=..."`, and updated `_require_mcp`'s remedy message. Documented the daemon
lifecycle and staleness/correctness contract in docs/modules/serve.md,
including an explicit, honest scope note.

Scope cut (disclosed, not silently skipped): `frob.gates.run_gates` still
evaluates every selected gate in FULL on each `frob_check_delta` call -- there
is no per-obligation dependency-tracked partial re-evaluation inside
`run_gates` itself. The "only obligations whose inputs changed" framing in the
ticket's plan is achieved at the graph/baseline/test-collection layer (this
module) via `warm_state`'s dirty-key gate, not by threading a pre-built
snapshot into `run_gates`'s own `_load_inputs`/`_build_jobs` dispatch --
wiring that through would mean changing signatures a much larger set of gate
call sites depend on, a separately-ticketed project. Filed as a follow-up:
T-0602 (ex-draft, id lost at land) (provisional id, minted off-default-branch; the coordinator
assigns the real T-#### id at land). `frob_check_delta`'s `verify=True` mode is the correctness
guarantee for the part that IS cached (the graph/baseline/test-list), proven
via a cold-vs-warm violation-fingerprint diff plus a hypothesis property test
asserting the vacuous-pass invariant (a rebuild happens on every call
following a real edit, and only those).

Version bump (REL001, "public API changed (minor)... bump to >= 0.74.0") is
intentionally NOT done in this ticket -- CHANGELOG.md is not in T-0177's
declared scope, and this repo's own history (see recent `chore(release):
land workflow features ... at 0.N0.0` commits in `git log`) treats the
version bump + CHANGELOG note as a coordinator/land-time batch action across
several tickets, not a per-ticket implementer step. `frob check --ticket
T-0177` is clean except this one gate:REL error, which is expected under
that pattern.

### Changed
```
 tickets.md | 502 +++++++++++++++++++++++++++++++++++++++++++++++++++++--------
 1 file changed, 436 insertions(+), 66 deletions(-)
```

### Evidence
(no evidence recorded)
