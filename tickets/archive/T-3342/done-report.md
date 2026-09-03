## Done report

Doc-content-only fix for the 6 gate:DOC findings that survived after
T-3344 independently fixed the shared frob:tests directive-syntax root
cause across the 11 other files this ticket originally touched.
DOC011 x3 (docs/guides/release.md): retargeted a citation of never-
finalized draft ticket T-draft-13d00ebe to T-3337, which already
tracks the identical release-publish bump-class bug. DOC001 x1
(docs/index.md): linked the orphaned docs/strata/graph.md into the
strata design-doc list. DOC005 x1 (docs/modules/cli.md): regenerated
the stale generated CLI command table via `frob docs --sync-commands`.
frob:no-behavior-change declared (T-2393) -- no executable code path
changed.
Two findings split to follow-up tickets due to live cross-worktree
lease collisions on the same files, not fixed here: DOC007 x2 in
src/frob/app/check_runner.py (T-3326's lease) -> T-draft-d44788a8;
DOC002 x1 in src/frob/tickets/_leases.py (T-3295's lease) ->
T-draft-b7982c97.
Verified via a completed gate:DOC-scoped `frob check` run against
these 3 files: 0 DOC-code errors remain. Full `frob check --ticket`/
`frob test --base main` could not complete under host contention
(load 20-64 on 12 cores, ~19 concurrent frob/pytest/ty processes from
other series) -- UNMEASURED, reported explicitly rather than implying
a pass.

### Changed
```
 docs/guides/release.md | 6 +++---
 docs/index.md          | 4 ++++
 docs/modules/cli.md    | 2 ++
 3 files changed, 9 insertions(+), 3 deletions(-)
```

### Evidence
- `cmd:bash /tmp/claude-1000/-home-logan-projects-frob/79c6402d-b401-4652-bea7-f81df1be9322/scratchpad/doc_evidence.sh exit=0 sha256=5300ee49bc51` (cmd evidence, exit=0)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 41 error(s), 3954 warning(s), 879 waived
- error-findings: ARCH103@src/frob/app/_version_guard.py, ARCH103@src/frob/app/check_runner.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/refactor/_verify.py, CLAUDE001@.claude/hooks/sync-claude-config.py, CYCLE001@src/frob/__init__.py, DEPR006@frob-deprecated-baseline.lock.json, DOC002@src/frob/tickets/_leases.py, DOC004@docs/commands/check.md, DOC007@src/frob/app/check_runner.py, DOC011@docs/modules/tickets.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT002@src/frob/app/check_runner.py, FLAGCOV001@frob.toml, LARGE001@src/frob/__main__.py, LARGE001@src/frob/process/_reap.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, LEXCHECK001@src/frob/gates/_comment_placement.py, OPAQUE001@tests/unit/test_land_finish_idempotent.py, PERF004@.claude/hooks/frob-suggest.py, PERF004@src/frob/lang/_support.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, REG002@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, REL001@strata-core/src/graph/vmodel.rs, REL001@strata-core/src/parse/grammar_core.rs, REL001@tests/unit/test_conftest_suite_result_status.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SEC110@tests/test_worktree_guard.py, SELFAUDIT001@design, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json, WIRE002@src/frob/gates/_tdd_order.py, WIRE002@tests/conftest.py
