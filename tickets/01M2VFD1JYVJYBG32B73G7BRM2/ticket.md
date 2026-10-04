+++
id = "01M2VFD1JYVJYBG32B73G7BRM2"
title = "Regenerate docs/commands from the final CLI surface (18 files for 51 verbs today) and report the drift in the owner-owned ~/.claude/refs/frob.md"
type = "docs"
category = "done"
outcome = "done"
priority = "high"
points = 2
reporter = "human"
created = "2026-09-19T00:00:00Z"
updated = "2026-09-19T00:00:03Z"
aliases = ["T-4702"]
labels = ["cli-debloat", "points-2", "milestone:0.533.0", "component:docs"]
scope = ["docs/design/cli-regrouping.md", "tests/unit/test_docs_commands_coverage.py", "docs/commands/check.md", "docs/commands/cli-vocabulary.md", "docs/commands/cycle.md", "docs/commands/deploy.md", "docs/commands/exports.md", "docs/commands/format.md", "docs/commands/gitlog.md", "docs/commands/map.md", "docs/commands/narrative.md", "docs/commands/outline.md", "docs/commands/parse.md", "docs/commands/refactor.md", "docs/commands/release.md", "docs/commands/run.md", "docs/commands/scaffold.md", "docs/commands/sync-skills.md", "docs/commands/sys.md", "docs/commands/xref.md", "src/frob/docs/_command_pages.py", "src/frob/app/docs_runner.py", "src/frob/_cli_parsers/_core.py", "src/frob/app/config.py", "src/frob/app/_config_external.py", "docs/commands/ack.md", "docs/commands/agent.md", "docs/commands/claude.md", "docs/commands/clean.md", "docs/commands/coverage.md", "docs/commands/doctor.md", "docs/commands/explore.md", "docs/commands/fleet.md", "docs/commands/graph.md", "docs/commands/mutate.md", "docs/commands/natives.md", "docs/commands/perf.md", "docs/commands/pool.md", "docs/commands/process.md", "docs/commands/profile.md", "docs/commands/registry.md", "docs/commands/serve.md", "docs/commands/status.md", "docs/commands/test.md", "docs/commands/verify.md", "docs/commands/vet.md", "docs/commands/worktree.md", "docs/index.md", "docs/modules/app.md", "tests/unit/test_app_config_from_external_t1276.py", "design/frob.strata", "docs/design/registry/capability-via-ratchet.lock.json"]

[[links]]
kind = "blocked-by"
target = "01M2VFD1JJD17QEF1ZFXA7C3R1"

[[links]]
kind = "blocked-by"
target = "01M2VFD1JM87727BCPQ26VDTSN"

[[links]]
kind = "blocked-by"
target = "01M2VFD1JQJT6H8RBEMNSTDSVN"

[[links]]
kind = "blocked-by"
target = "01M2VFD1JRS4WQNT3DRA7MFAJM"

[[links]]
kind = "blocked-by"
target = "01M2VFD1JTK81G3H4P1R244YCR"

[[acceptance]]
text = "Given the live argparse tree, when the coverage test runs, then every top-level verb has a docs/commands entry and every docs/commands entry names a live verb"
bound = false

[[acceptance]]
text = "Given a planted verb with no doc and a planted doc with no verb, when the coverage test runs, then it fails on each -- the assertion is proven to fire in both directions"
bound = false

[[acceptance]]
text = "Given ~/.claude/refs/frob.md, when this ticket closes, then the Done report lists each stale spelling with file:line and replacement text and the file itself is unmodified"
bound = true
+++

POINTS: 2. Parent story T-4687. blocked_by T-4690, T-4692, T-4695, T-4696,
T-4698 -- it documents the FINAL surface, so it cannot start until the surface
has stopped moving.

MEASURED 2026-09-19: docs/commands/ holds 18 files (check, cli-vocabulary,
cycle, deploy, exports, format, gitlog, map, narrative, outline, parse,
refactor, release, scaffold, sync-skills, sys, ticket, xref) against 51
top-level verbs and 54 ticket subverbs. It documented a third of the surface
before this story started, and this story moves or deletes most of what it does
cover (cycle, exports, gitlog, map, outline, parse, xref all move).

WORK:
1. Regenerate docs/commands/ from the FINAL surface. Prefer generating it from
   the argparse tree over hand-writing 18 more files -- if a generator does not
   exist, write one and wire it so the docs cannot drift again silently. Say in
   the Done report whether it was generated or hand-written and why.
2. Update docs/commands/cli-vocabulary.md and docs/design/cli-regrouping.md:
   the latter is the design doc that JUSTIFIED the four group verbs T-4690
   deletes. It must record that the regrouping was reverted, and why (the
   groups added four names and removed zero).
3. `git grep` every removed spelling across docs/ and fix the citations.

OUT OF SCOPE, REPORT ONLY: ~/.claude/refs/frob.md is the OWNER'S file. Do not
edit it. The Done report must list, line by line, the edits it needs: each stale
verb spelling, its file:line, and the replacement text -- so the owner can apply
them without re-deriving anything.

POSITIVE CONTROL (acceptance): a test that walks the live argparse tree and
asserts every top-level verb has a docs/commands entry AND every docs/commands
entry names a live verb -- it must FAIL if a verb is added without docs or a
doc outlives its verb. Plant one of each in the test fixture to prove the
assertion fires in both directions.

FILES (declared scope):
  docs/commands/**
  docs/design/cli-regrouping.md
  tests/unit/test_docs_commands_coverage.py (new)

## Reopen log
- 2026-09-22: closed-but-unlanded: refused land wrote state=done with land_commit null and no code on dev
