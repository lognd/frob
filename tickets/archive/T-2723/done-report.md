## Done report

Re-verified the reported premise directly in code before designing anything:
`_membership_key`, `_touched_key`, `extra_key` (per-gate cache), and
`root_content_key`/`_replay_fingerprint` (root-scanning + whole-run replay
caches) were all pure functions of tracked tree content -- none folded in
any signal identifying the frob build/gate code that produced the cached
result. Confirmed this is the exact mechanism the measured incident hit:
`_replay_fingerprint` backs the T-2585 whole-run replay cache, which is
what actually served the stale 4-LANG004 result in the consumer repo.

Fix: `_gate_build_fingerprint()` (new, `@lru_cache`d for process lifetime)
folds the installed `frob` distribution's `importlib.metadata.version`
together with a content hash of every `.py` file under the running
`frob.gates` package. `extra_key()` now always folds this in alongside its
caller-supplied values, which covers both the per-gate cache
(`evaluate_cacheable_gate`) and the T-1445 root-scanning cache
(`load_root_gate_cache`/`store_root_gate_cache`, both route their `extra`
through `extra_key`) with one change. `_replay_fingerprint` does not route
through `extra_key` at all, so it folds the same build fingerprint in
directly -- this is the cache the measured incident actually hit.

Both version AND a code-content hash are folded together (not either
alone): version alone misses a dev/editable checkout that patches gate
logic without a version bump (this repo's own REL001 stamp is scoped to
public API surface, not every gate fix); the content hash alone degrades
gracefully when the package cannot be located (folds a distinguishing
marker string in instead of raising) so the two signals corroborate
without either being a hard dependency of the other.

Positive controls, all three required directions, all passing:
- upgrade with an UNCHANGED tree: `test_upgrade_forces_real_replay_on_unchanged_tree`
  stores a replay under one fingerprint, swaps to a different one via
  monkeypatch (standing in for a real upgrade), and asserts the stored
  replay MISSES -- forcing a real re-run rather than reprinting the old
  build's verdict. This is the ticket's own designated BUG002 repro:
  committed the test alone first (d3cf36601, against pre-fix code) and
  confirmed a real failure (AttributeError: no `_gate_build_fingerprint`
  attribute existed yet -- `--designate-repro` verified FAILED_AT_PARENT
  against that exact commit), then applied the fix as a second commit and
  reconfirmed the same test passes.
- SAME build, unchanged tree, twice: `test_same_build_same_tree_still_replays_twice`
  and `test_extra_key_stable_for_same_build` -- the cache must stay
  load-bearing, not degrade into invalidating every run.
- tree change under a FIXED build: `test_tree_change_still_invalidates_under_same_build`
  -- the build fingerprint is additive to tree-content keys, never a
  replacement; a tracked-file edit still forces a miss exactly as before.

Also added direct unit coverage for `extra_key`/`_replay_fingerprint`
sensitivity to the fingerprint changing
(`test_extra_key_changes_when_build_fingerprint_changes`,
`test_replay_fingerprint_changes_when_build_fingerprint_changes`) and a
smoke test on the real (unpatched) `_gate_build_fingerprint` itself
(`test_real_fingerprint_is_stable_and_never_raises`).

Re-verified the four consumer measurements the coordinator flagged as
possibly warm-cache artifacts (DOC006, DOC008, DOC010, SYS004) against
/home/logan/projects/aprog-public with `--no-cache`, read-only, no writes
to that repo -- reported in my final message to the coordinator, not in
this ticket's own scope.

`frob check --ticket T-2723` reports zero errors attributable to
`src/frob/gates/_gate_cache.py`, `tests/test_gate_cache.py`, or
`docs/modules/serve.md` (one AFFECT001 on `extra_key`'s changed doc-closure
target was hit and fixed by extending the T-0602 section of
`docs/modules/serve.md` with a T-2723 paragraph naming the new mechanism
and the incident it closes).

### Changed
```
 docs/modules/serve.md         |  32 ++++++++
 src/frob/gates/_gate_cache.py | 116 ++++++++++++++++++++++----
 tests/test_gate_cache.py      | 183 ++++++++++++++++++++++++++++++++++++++++++
 tickets/T-2723/ticket.md      |  12 ++-
 4 files changed, 327 insertions(+), 16 deletions(-)
```

### Evidence
- `tests/test_gate_cache.py::TestGateBuildFingerprint::test_upgrade_forces_real_replay_on_unchanged_tree` (pytest node id, verified passing when recorded)
- `tests/test_gate_cache.py::TestGateBuildFingerprint::test_same_build_same_tree_still_replays_twice` (pytest node id, verified passing when recorded)
- `tests/test_gate_cache.py::TestGateBuildFingerprint::test_tree_change_still_invalidates_under_same_build` (pytest node id, verified passing when recorded)
- `tests/test_gate_cache.py::TestGateBuildFingerprint::test_extra_key_changes_when_build_fingerprint_changes` (pytest node id, verified passing when recorded)
- `tests/test_gate_cache.py::TestGateBuildFingerprint::test_extra_key_stable_for_same_build` (pytest node id, verified passing when recorded)
- `tests/test_gate_cache.py::TestGateBuildFingerprint::test_replay_fingerprint_changes_when_build_fingerprint_changes` (pytest node id, verified passing when recorded)
- `tests/test_gate_cache.py::TestGateBuildFingerprint::test_real_fingerprint_is_stable_and_never_raises` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: 44 error(s), 1893 warning(s), 679 waived
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC002@src/frob/gates/_milestone.py, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, E501@/home/logan/projects/frob/.claude/worktrees/t2723-t2721/src/frob/_cli_parsers/_ticket/_closeout.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII010@src/frob/deploy/_audit.py, PII012@src/frob/doctor.py, PII012@src/frob/serve/_socketd.py, PII012@tests/system/test_cli_doctor.py, PII012@tests/test_capability_registry.py, PII012@tests/test_doctor.py, PII012@tests/test_hook_diagnosis_nudge.py, PII012@tests/test_prework_parity.py, PII012@tests/test_vet.py, PII012@tests/unit/test_doctor_runner_t1276.py, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
