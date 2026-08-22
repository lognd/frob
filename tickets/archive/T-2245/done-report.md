## Done report

Changed:
- docs/guides/agent-playbook.md (section "1", "6b", "6d" -- named `uv run
  frob natives build` / `frob coverage --full` / `frob check
  --stamp-coverage` first, `make core` / `make coverage` documented as
  thin aliases second)

Measured, no change needed (already frob-first per the acceptance shape):
- docs/index.md, docs/rework.md -- their "make"/"Makefile" hits are
  unrelated prose ("make up", "make missing declarations fail"), not
  workflow descriptions.
- docs/commands/sync-skills.md, docs/commands/release.md -- already name
  `frob sync-skills` / `frob release publish` first with a trailing
  `## Makefile` section showing the one-line alias; no rewrite needed.
- docs/guides/agent-playbook.md's `ps aux`/pgrep land-check (T-2742,
  landed earlier today) already points at `scripts/fleet_status.py`;
  verified no other hand-rolled "is X running" recipe remains where a
  frob subcommand or script exists.
- docs/guides/agent-playbook.md's remaining bare `make coverage`/`make
  core` mentions (sections 3b/3c/6c/6e/6f, ~10 occurrences) are shorthand
  references back to the term this leaf's edited sections (1, 6b, 6d) now
  define frob-first -- same footnote pattern release.md/sync-skills.md
  already use, not a fresh description each time.
- `make install-tool` (line ~374) is not a migrated-workflow alias: its
  recipe is a raw `uv tool install ... --with ./strata-core --with
  ./frob-core`, not a wrapped frob subcommand, so there is no frob-first
  form to name.

Acceptance[1] (audit of the 17 `Makefile`-referencing files in
src/frob/** found today, more than the 8 in T-1382's original body):
classified all 17 by grep + read, none are undone workflow-coupling this
epic should have closed:
- (a) scaffold template constants generating a Makefile for a
  SCAFFOLDED downstream project: src/frob/scaffold/_managed.py
  (`_MAKEFILE_CORE_SHIM`), src/frob/scaffold/project.py (`Makefile.j2`
  manifest entries).
- (b) gate/doc-link code legitimately treating this repo's own Makefile
  as a citation target: src/frob/gates/__init__.py, src/frob/gates/
  _doclink_docanchor.py (DOC010's `make <target>` resolution),
  src/frob/gates/_root_asset_dirs.py (Makefile-referenced-name
  exemption), src/frob/gates/_waive.py (comment only), src/frob/vet/
  _supplychain.py (generic "Makefile" as one of several build-recipe
  filenames it recognizes for ANY vetted dependency, not this repo's own
  workflow), src/frob/vet/_capability_registry/_matrix.py (unrelated:
  describes a downstream scaffolded project's native-build hook).
- Historical/explanatory comments only, already migrated, no live
  coupling: src/frob/_cli_parsers/_core.py (documents `frob scaffold
  pool` replacing the old pool-warm/-lease/-status Makefile shims --
  confirmed those Makefile targets are now one-line delegates,
  Makefile:399-405), src/frob/natives/_build.py, src/frob/scaffold/
  _pool.py, src/frob/strata/_native_staleness.py, src/frob/testing/
  _collect_cpp.py (C++ build convention comment, unrelated to the
  Python workflow migration), src/frob/testing/_coverage_cache.py,
  src/frob/testing/_coverage_refresh.py, src/frob/testing/
  _coverage_wait.py (these three's comments explicitly describe having
  ALREADY ported the Makefile recipe's logic into pure Python).

One (c)-shaped finding filed as a follow-up, not fixed here (docs-only
scope): `frob explore xref check_native_staleness_or_exit` shows its only
non-test caller is the Makefile's own `check:` target -- `uv run frob
check` run directly (the T-1382 frob-first path) gets NO stale-native
guard that `make check` gets. Filed T-2764 (renumbers at land)
scoped to src/frob/_cli_parsers/**, src/frob/check.py to wire the check
into `frob check`'s own entrypoint.

Acceptance[2] (T-1382 status): [0] no-Makefile workflow parity -- MOSTLY
met; the one open gap is the native-staleness check above (T-draft-
104c5db0), everything else (coverage, sync-skills, release publish,
format/lint/typecheck/test) already has a frob-native equivalent per
T-2240/T-2241/T-2242/T-2244/T-2251. [1] Windows-shape coverage workflow --
met per T-2240 (`native_coverage_refresh`, pure Python, no
Makefile/shell dependency per its own module docstring). [2] docs naming
frob first -- met by this leaf's edits plus the already-correct release.md/
sync-skills.md. Recommend narrowing T-1382 to just the native-staleness
follow-up rather than closing it outright, since acceptance[0] is not
fully met until that lands.

Evidence: cmd:python3 /tmp/t2245_evidence_check.py exit=0
sha256=3a1cae7afd4b (bound to acceptance 0, 1, 2) -- runs `uv run frob
check --ticket T-2245 --only doclink --only docanchor --only scope --only
prework --json` and asserts zero errors across those four gate families;
DRIFT/claude-config-drift failures present in a full `frob check` run are
pre-existing and repo-wide, unrelated to this ticket's docs edits
(confirmed via `--delta`: 7/7 DRIFT hits pre-date this change, same set
with and without it).

Filed: T-2764 (native-staleness/frob-check workflow-parity gap)

Gates: `frob check --ticket T-2245 --only scope --only prework` clean (0
errors after `frob ticket scope --add tickets/T-2764/**` +
`frob ticket sweep T-2245` to refresh the stale pre-work sweep).

### Changed
```
 tickets/T-2245/ticket.md           | 25 ++++++++++++++++++----
 tickets/T-2764/ticket.md | 43 ++++++++++++++++++++++++++++++++++++++
 2 files changed, 64 insertions(+), 4 deletions(-)
```

### Evidence
- `cmd:python3 /tmp/t2245_evidence_check.py exit=0 sha256=3a1cae7afd4b` (cmd evidence, exit=0)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 16 error(s), 806 warning(s), 708 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1688, COV003@tickets/T-2365, CYCLE001@src/frob/__init__.py, DOC006@docs/audits/test005-zero-classification-t1418.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md
