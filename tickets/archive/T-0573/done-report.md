## Done report

frob.fleet (new package, src/frob/fleet/__init__.py) is the cross-repo
status/gate rollup and ticket router the ticket asked for. FleetManifest/
RepoEntry parse a fleet.toml ([[repo]] name/path, relative paths rebased
against the manifest file's own directory, not the process cwd).
collect_status probes one repo's git branch/dirty state (subprocess), a
gate summary (subprocess, see review-fix note below), and its own doable-
ticket count via frob.tickets.load_queue/doable (no subprocess). rollup
sorts every probed repo reddest-first (most gate errors, then warnings,
then doable tickets). route_ticket files a TicketSpec straight into a
named sibling's own ledger via frob.tickets.new_ticket(root=<that
sibling>, spec) -- no second frob process, no coordinator-memory
copy-paste.

CLI wiring follows the existing App/AppConfig runner pattern exactly:
src/frob/app/fleet_runner.py (`frob fleet status [--manifest] [--json]
[--skip-gates]`, `frob fleet route --repo NAME --title TEXT [--kind]
[--priority] [--scope...] [--body]`), Subcommand.fleet + AppConfig fields
in config.py, the dispatch-table entry in app.py, and the argparse wiring
in __main__.py's _add_fleet_parser.

REVIEW ROUND 1 -- REJECTED, two findings, both fixed in this worktree:

1. CRITICAL: _gate_summary_probe originally shelled a bare ["frob",
   "check", "--json"] with cwd=sibling. This machine's PATH `frob` is a
   documented stale 0.9.0 global (docs/guides/agent-playbook.md section
   2), so every sibling's gate counts would silently come from the WRONG
   binary while looking correct (same-shaped table, wrong numbers). Also
   caught while fixing: the JSON-parsing logic assumed a fictional
   top-level {"violations": [...]} schema (copied from frob.vet --json's
   shape by mistake) instead of the REAL frob.check.CheckResult.as_json
   schema ({"path", "results": [{"tool", "diagnostics": [{"severity":
   "error"|"warning"|...}]}]}) -- the original unit test used a fake
   payload matching the wrong schema, so it never caught this. Both are
   now fixed: `_check_probe_argv` builds ["uv", "run", "--project",
   str(repo_path), "frob", "check", "--json"] (verified end to end
   against a REAL sibling, /home/logan/projects/lithos: `uv run --project
   /home/logan/projects/lithos frob check --json` correctly resolved and
   ran lithos's own pinned frob against lithos's own tree -- confirmed by
   diagnostic content specific to lithos's codebase and a run time
   matching lithos's much larger size, not this repo's ~15s baseline);
   `_count_diagnostics` now walks the real results/diagnostics/severity
   shape. A new regression test,
   TestCollectStatus.test_collect_status_probes_sibling_pinned_frob_not_bare_path_frob,
   monkeypatches subprocess.run, captures the constructed argv, and
   asserts argv[0] != "frob" plus the full expected uv-run-project argv --
   this is a load-bearing assertion on the exact invocation, not just
   "did it not crash".

2. MINOR: route_ticket did not verify the target repo was frob-enabled
   before calling new_ticket, which would silently BOOTSTRAP a brand-new
   tickets.md in an unrelated directory reached by a typo'd --repo name
   (new_ticket's own create-on-first-write behavior, correct for a human
   deliberately initializing a repo, wrong for an automated fleet route).
   Fixed: route_ticket now checks frob.tickets._store.ledger_path(resolved)
   .exists() or tickets_dir(resolved).is_dir() before calling new_ticket,
   returning Err(RouteFailed) with a clear log message otherwise. New test
   TestRouteTicket.test_route_ticket_not_frob_enabled covers it (asserts
   RouteFailed AND that no tickets.md got created).

docs/modules/fleet.md and the FleetError table were updated to describe
both fixes (the uv-run-project probe rationale, and the ledger-presence
check).

Test suite: 16/16 passing, foreground:
`uv run pytest tests/unit/fleet/ tests/unit/test_fleet_runner.py
tests/integration/test_fleet_integration.py -p no:cacheprovider -q`
(up from 14 before the review round; 2 new tests added: the argv
regression test and the not-frob-enabled routing test).

frob check --ticket T-0573: 0 new violations from this ticket's own code.
Residual FAILs are pre-existing/unrelated: gate:REL (REL001, public API
version bump) is left for the coordinator's land-time release stamp per
this repo's landing workflow (T-0325 precedent); gate:PRE was cleared by
re-running `frob ticket sweep T-0573` after each scope/code change;
gate:COV errors trace to OTHER tickets' (T-0577/T-0595) evidence ids not
resolving against the collection cache, unrelated to any file this ticket
touches; INV004 on the new doc is warn-only advisory, consistent with the
~600-strong pre-existing INV004 debt across docs/ (T-0452/T-0462
burndown).

Ruff (both PATH ruff and project-pinned uv run ruff) and ty are clean
over every touched file. main was merged into this worktree mid-fix
(T-0573's original merge base had gone stale while the review round was
in progress); the deletion-filter check (git diff main --diff-filter=D
--stat) is empty after the merge, confirming nothing else was reverted.

### Changed
```
 README.md                                   |   3 +-
 docs/modules/fleet.md                       | 143 +++++++++++
 fleet.toml                                  |  38 +++
 src/frob/__main__.py                        |  51 ++++
 src/frob/app/app.py                         |   4 +-
 src/frob/app/config.py                      |  29 +++
 src/frob/app/fleet_runner.py                | 140 ++++++++++
 src/frob/fleet/__init__.py                  | 383 ++++++++++++++++++++++++++++
 tests/integration/test_fleet_integration.py |  62 +++++
 tests/unit/fleet/__init__.py                |   0
 tests/unit/fleet/test_manifest.py           |  36 +++
 tests/unit/fleet/test_route.py              |  78 ++++++
 tests/unit/fleet/test_status.py             | 133 ++++++++++
 tests/unit/test_fleet_runner.py             |  77 ++++++
 tickets.md                                  | 282 +++++++++++++++++++-
 uv.lock                                     |   2 +-
 16 files changed, 1454 insertions(+), 7 deletions(-)
```

### Evidence
- `tests/unit/fleet/test_manifest.py::TestLoadManifest::test_load_manifest_ok` (pytest node id, verified passing when recorded)
- `tests/unit/fleet/test_manifest.py::TestLoadManifest::test_load_manifest_missing` (pytest node id, verified passing when recorded)
- `tests/unit/fleet/test_manifest.py::TestLoadManifest::test_load_manifest_malformed` (pytest node id, verified passing when recorded)
- `tests/unit/fleet/test_route.py::TestRouteTicket::test_route_ticket_ok` (pytest node id, verified passing when recorded)
- `tests/unit/fleet/test_route.py::TestRouteTicket::test_route_ticket_unknown_repo` (pytest node id, verified passing when recorded)
- `tests/unit/fleet/test_route.py::TestRouteTicket::test_route_ticket_missing_path` (pytest node id, verified passing when recorded)
- `tests/unit/fleet/test_route.py::TestRouteTicket::test_route_ticket_not_frob_enabled` (pytest node id, verified passing when recorded)
- `tests/unit/fleet/test_status.py::TestCollectStatus::test_collect_status_ok` (pytest node id, verified passing when recorded)
- `tests/unit/fleet/test_status.py::TestCollectStatus::test_collect_status_probes_sibling_pinned_frob_not_bare_path_frob` (pytest node id, verified passing when recorded)
- `tests/unit/fleet/test_status.py::TestCollectStatus::test_collect_status_missing_path` (pytest node id, verified passing when recorded)
- `tests/unit/fleet/test_status.py::TestRollup::test_rollup_orders_reddest_first` (pytest node id, verified passing when recorded)
- `tests/unit/test_fleet_runner.py::TestFleetRunner::test_run_status_table` (pytest node id, verified passing when recorded)
- `tests/unit/test_fleet_runner.py::TestFleetRunner::test_run_status_missing_manifest` (pytest node id, verified passing when recorded)
- `tests/unit/test_fleet_runner.py::TestFleetRunner::test_run_route_ok` (pytest node id, verified passing when recorded)
- `tests/unit/test_fleet_runner.py::TestFleetRunner::test_run_route_missing_flags` (pytest node id, verified passing when recorded)
- `tests/integration/test_fleet_integration.py::TestFleetIntegration::test_fleet_status_table_over_real_repos` (pytest node id, verified passing when recorded)
