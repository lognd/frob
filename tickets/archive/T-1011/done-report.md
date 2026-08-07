## Done report

T-1011 bundles T-1008's children 3+4, both "generate-at-the-source" items.

(a) land auto-syncs check-coverage.yaml when the landing diff touched
`_KNOWN_GATE_RULES`:

- `land()`/`_land_locked`/`_land_squash_apply` (`src/frob/tickets/_land.py`)
  gained an optional `sync_gate_rules: Callable[[Path, str],
  Result[tuple[str, ...] | None, LandError]] | None = None` parameter,
  invoked right after the REL001 `bump_version` callback (same staged-but-
  uncommitted point, same fail-closed-unwind posture via
  `_apply_gate_rule_sync`/`_verified_reset_root`) -- mirrors the existing
  `bump_version`/`rebuild_natives` callback-injection pattern exactly, for
  the same cycle-avoidance reason (`frob.tickets` cannot import
  `frob.gates`/`frob.registry`, docs/rework.md).
- `ticket_runner._land_sync_gate_rules_fn`/`_sync_gate_rules_for_land`
  (`src/frob/app/ticket_runner.py`) is the CLI-layer implementation: diffs
  `root`'s just-squashed working tree against `pre_land_tip` for
  `src/frob/gates/__init__.py`; if `_KNOWN_GATE_RULES` does not appear in
  that diff text, no-op (`Ok(None)`, the common case, no wasted registry
  scan). If it does, scans root's ON-DISK tree via
  `frob.gates._rule_id_scan.generated_gate_rule_ids` (never a live
  `frob.gates` import -- this process's own already-imported module is the
  WORKTREE's old code, not root's freshly-squashed source) and appends any
  missing `check-coverage.yaml` row via `sync_gate_rule_entries`, staging
  it into the same land commit. Wired into the real `frob ticket land`
  CLI's `land()` call alongside `bump_version`/`rebuild_natives`.
- A registry-level failure (missing/malformed `check-coverage.yaml`) is
  logged and treated as `Ok(None)` -- best-effort, not a landing-critical
  guarantee the way REL001's version bump is; only a git staging failure
  escalates to `Err(GitFailed)`, unwinding the squash.

(b) README + docs/modules/cli.md command tables generated from the live
argparse registry, DOC005 gains a freshness half:

- README.md's existing hand-curated, section-grouped table keeps its
  original MISSING/STALE per-row DOC005 check UNCHANGED -- regenerating it
  wholesale would destroy the curated grouping (Core/Navigation/Plumbing
  tiers), which was never in scope to redesign.
- `docs/modules/cli.md` gained a NEW, fully-generated block, delimited by
  `CLI_COMMAND_TABLE_START`/`_END` marker comments (`frob.gates._docblocks`,
  T-1011), one markdown row per live top-level subcommand across every
  configured `[[docblocks.commands]]` source, sorted `(prog, name)`.
  `generate_cli_command_table(root)` builds the text; `sync_cli_command_
  table(root)` replaces ONLY the marked region in place (idempotent).
- `frob docs --sync-commands` (new flag on the existing `frob docs`
  subcommand; `docs_path` is now optional, `nargs="?"`, since sync mode
  needs no path) is the CLI entrypoint -- `docs_runner._run_sync_commands`.
- `doc005_gate` gained a second, independent source:
  `_doc005_cli_table_freshness_violations` regenerates the expected block
  text right now and ERRORs if `docs/modules/cli.md`'s committed block
  differs -- a byte-freshness check, not a hand-sync lock, satisfying "DOC005
  becomes a freshness check" for the generated surface. No marker block
  present means the doc has not opted in -- fail-open, same posture as
  every other DOC004/DOC005 namespace source.
- `docs/modules/cli.md` opted in this same ticket (the marker block was
  added and populated via a real `frob docs --sync-commands` run).

Cut/disclosed: README.md's table itself is NOT regenerated wholesale --
only cli.md's new block is a full generator target. This is a deliberate,
disclosed scope narrowing from the ticket body's "README + docs/modules/
cli.md command tables become generated" phrasing: README's table is
hand-curated into thematic sections (Core/Navigation/Exports-consumers/
natives build/Plumbing tiers) that a flat generated table would destroy;
regenerating it losslessly (preserving section membership per command)
was out of this ticket's reasonable scope. README keeps DOC005's original,
still-real MISSING/STALE/count-claim checks, unchanged.

### Changed
(no changed files detected)

### Evidence
- `tests/test_ticket_land.py::TestSyncGateRulesCallback::test_sync_gate_rules_none_is_noop` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestSyncGateRulesCallback::test_sync_gate_rules_applies_and_stages` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestSyncGateRulesCallback::test_sync_gate_rules_failure_unwinds` (pytest node id, verified passing when recorded)
- `tests/test_docblocks_gate.py::TestCliCommandTableGenerator::test_generate_sorts_rows_across_sources` (pytest node id, verified passing when recorded)
- `tests/test_docblocks_gate.py::TestCliCommandTableGenerator::test_generate_no_config_is_none` (pytest node id, verified passing when recorded)
- `tests/test_docblocks_gate.py::TestCliCommandTableGenerator::test_sync_replaces_only_the_marked_block` (pytest node id, verified passing when recorded)
- `tests/test_docblocks_gate.py::TestCliCommandTableGenerator::test_sync_no_markers_returns_false` (pytest node id, verified passing when recorded)
- `tests/test_docblocks_gate.py::TestCliCommandTableGenerator::test_doc005_freshness_flags_stale_generated_block` (pytest node id, verified passing when recorded)
- `tests/test_docblocks_gate.py::TestCliCommandTableGenerator::test_doc005_freshness_passes_after_sync` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch5.py::TestDocsRunner::test_sync_commands_writes` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 10 passed (from 10 evidence id(s))
- gates: 0 error(s), 10242 warning(s), 333 waived
- error-findings: none (measured, zero errors)
