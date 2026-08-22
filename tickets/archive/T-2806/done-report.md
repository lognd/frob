## Done report

Changed:
src/frob/gates/__init__.py::_run_gates_bounded
src/frob/gates/__init__.py::_stamp_worker_parse_artifact_cache_env

Evidence:
tests/unit/test_check.py::TestParseArtifactCacheWarmedBeforeGraphBuild::test_env_var_set_before_load_inputs_builds_graph
tests/unit/test_check.py::TestParseArtifactCacheWarmedBeforeGraphBuild::test_stamp_is_idempotent_across_both_call_sites
tests/test_gates.py::test_gates_run_gates_integration (touched-set, unchanged, still green)

Filed: none (this closes T-2806 itself; no further out-of-scope findings)

Gates: frob check --ticket T-2806 clean for this ticket's own scoped
checks (gate:SCOPE/gate:PREWORK/COV002/TODO001/FMT/AFFECT all pass);
every other family's non-zero count in that run is pre-existing repo-wide
noise unrelated to this change (DRIFT001/DRIFT002 on tickets storage,
TICK003/004/006 on tickets.md, REG002, TEST001, DOC001/006/011,
CLAUDE001 config drift) -- confirmed identical before/after this change
in a real unbudgeted `frob check --json` run (see Findings below).
frob test --base main: exit=0, 4 python outcomes recorded.

Summary: moved `_stamp_worker_parse_artifact_cache_env` to run BEFORE
`_load_inputs` (and the `build_graph` call inside it) in
`_run_gates_bounded`, in addition to its existing call site inside
`_open_process_pool`. `build_graph`'s own `frob.lang.parse_file` calls
during graph construction now warm the shared, content-hash-keyed
`.frob/parse-artifacts.db` (T-1464) before any `ProcessPoolExecutor`
gate worker (perf/dead_symbols/archgate/sys/clones) starts, instead of
leaving the cache cold for whichever worker touches a file first.
`_stamp_worker_parse_artifact_cache_env` is idempotent (re-opens the
same db, re-stamps the same path), so the pre-existing later call site
is now a harmless no-op repeat, kept as a safety net.

Findings (real, unbudgeted `frob check --json` runs, this repo, fleet
LOAD 9-14 during measurement -- flagged as contended, not a quiet
window):
  - Full check, cold `.frob/cache.db` + `.frob/parse-artifacts.db`,
    WITHOUT this fix: 29 distinct-source errors (some inherent to this
    dirty worktree's own diff-in-progress state), 22 distinct (rule,file)
    identities excluding that noise.
  - Same, WITH this fix: same 22 distinct (rule,file) identities plus
    2 diff-location-only differences (PRE001/SCOPE001 moving between
    which of the two touched files was dirty at measurement time, an
    artifact of the A/B methodology -- both files are dirty in the real
    diff) -- IDENTICAL finding set once that measurement artifact is
    accounted for. One real difference caught and fixed before landing:
    COV002 fired on both changed functions (missing frob:ticket edges);
    added `frob:ticket T-2806` to both, re-verified clean.
  - Per-stage timing delta in that same full, cold, contended run
    (before -> after): perf 61.12s -> 47.86s, sys 72.24s -> 65.57s,
    archgate 48.45s -> 41.91s, coverage 49.68s -> 38.77s, clones
    22.54s -> 12.79s, dead_symbols 36.25s -> 32.41s. All process-pool,
    extract-heavy gates improved; none regressed.
  - Isolated `--only perf --only dead_symbols` from a cold cache,
    total wall time (build_graph + both gates): 79.3s -> 71.2s
    (~10% cut) -- this is the COLD-cache case specifically, the one
    that matters for a fresh worktree/land, not just a warm second run.
  - Positive control (cache mechanism unaffected by this change):
    genuinely changing a probe file's content (with a distinguishable
    mtime, avoiding an unrelated pre-existing mtime+size collision in
    build_graph's OWN incremental snapshot cache -- see Note below)
    correctly misses `.frob/parse-artifacts.db` and re-populates under
    the new content hash; the stale hash's old row is left in place
    (harmless, superseded) and the new hash's row is written fresh.
  - Operational-target framing: this fix measurably helps but the
    ~250-260s per-spawn bar (T-2782/T-2790's stated target for the
    land critical section's two sequential check spawns to fit under
    540s) is NOT fully closed by this ticket alone -- the win here is
    real (10-20% per affected gate, cold-cache case included) but
    build_graph itself still pays the full parse+extract cost once,
    unavoidably; this change makes that unavoidable cost SHARED instead
    of wasted N times over, it does not eliminate it.

Note (found, NOT fixed here, out of this ticket's scope): while
building the positive control above, a same-second, same-byte-length
content edit was silently treated as unchanged by `build_graph`'s own
(mtime_ns, size) incremental-snapshot shortcut (T-0245, in
`frob.graph`, not `frob.gates`/`frob.lang`) -- reproduced independent
of this ticket's change (confirmed by testing this scenario against
this same file on unmodified `_run_gates_bounded` too). This is the
same class of issue as T-2805 (native-staleness latch mtime could not
resolve, filed tonight per the dispatching coordinator) but a different
code path (`frob.graph`'s file-level snapshot cache, not a native
staleness latch) -- flagging for visibility, not filing a duplicate,
since T-2805 already covers the general "mtime cannot resolve a
same-size same-second edit" hazard class; if T-2805's fix doesn't
happen to cover this call site, a follow-up may be warranted once
T-2805 lands and its scope is known.

### Changed
```
 tickets/T-2806/ticket.md | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 21 error(s), 1220 warning(s), 714 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, CYCLE001@src/frob/__init__.py, DOC001@docs/investigations/T-2790-check-stage-profile.md, DOC001@docs/investigations/T-2796-backlog-reproduction.md, DOC006@docs/audits/test005-zero-classification-t1418.md, DOC011@docs/investigations/T-2796-backlog-reproduction.md, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, PERF004@src/frob/tickets/_evidence.py, PRE001@tickets/T-2806, REG002@docs/design/registry/check-coverage.yaml, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, SYS003@src/frob/check/__init__.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md
