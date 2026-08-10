## Done report

Added the `frob ops` verb group (T-1569, same shape as T-1567/T-1568,
following `frob explore`/T-1238): release/natives/doctor/clean/fleet/
deploy/scaffold/gitlog/stats grouped under `frob ops <subcommand>`, each
dispatching straight into the existing standalone runner's `run(cfg)`.
Every standalone top-level form stays a permanent alias.

`registry` (the "could go either way" note in docs/design/cli-regrouping.
md's original `frob ops` bucket) stayed under `frob design` only (T-1568)
-- not duplicated into `frob ops` -- since it is read-only design-
knowledge inspection, not an operational/infra action; the design doc's
`frob ops` section now records this resolution explicitly.

Avoided argparse duplication the same way T-1567/T-1568 did: extracted
_populate_release_actions/_populate_stats_args/_populate_doctor_args/
_populate_clean_args/_populate_natives_actions (_misc.py, previously
inline) and _populate_fleet_actions/_populate_gitlog_args (_reporting.
py, previously inline) and _populate_scaffold_actions (_core.py,
previously inline); reused deploy's already-factored _add_deploy_
generate_parser/_add_deploy_audit_parser + _DEPLOY_EPILOG directly. Both
the standalone parser and the new ops-group parser call the same helper
per member.

Wired: Subcommand.ops + AppConfig.ops_command (config.py), _STRING_
FIELDS entry (_config_external.py), ops_runner module name in all three
app.py registries. Re-added frob:ticket T-1569 edges alongside T-1567/
T-1568's existing ones on the app.py/config.py symbols this ticket ALSO
touched (COV002 requires an edge per ticket whose diff touches the
symbol).

Docs: docs/modules/cli.md regenerated (41 live commands now); docs/
design/cli-regrouping.md's `frob ops` section marked IMPLEMENTED with the
registry-bucket resolution noted; docs/modules/app.md gained an
ops_runner Runners paragraph (AFFECT001); README.md gained a `frob ops`
command-table row and the 40->41 count bump (DOC005); docs/commands/
scaffold.md and docs/guides/install.md each gained a one-line pointer to
the new alias (AFFECT001 on _add_scaffold_parser's/_add_doctor_parser's
own affects()-closure docs).

Landing hazard hit and worked around (not a code defect): main advanced
past this worktree's merge-base twice during T-1568's land (two other
agents landed concurrently), each time surfacing an OutOfScopeWaive
Deletion refusal naming files this ticket never touched. Per playbook
section 1.0/9, re-ran `git merge main` immediately before each land retry
(confirming `git diff main --diff-filter=D` stayed empty of anything
outside declared scope each time) rather than treating the refusal as a
real defect to fix.

Verification: `uv run frob check --only gates-fast --ticket T-1569` and
`--only gates-native --only gates-security --ticket T-1569` both clean (0
errors); `uv run frob check --land-parity` clean (0 unscoped errors);
`pytest tests/unit/test_app_runners.py` 67 passed.

### Changed
```
 tickets/T-1569/ticket.md | 125 ++++++++++++++++++++++++++++++++++++++++++++++-
 1 file changed, 124 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_app_runners.py::TestOpsRunner::test_subcommand_delegates_to_matching_runner[release]` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestOpsRunner::test_subcommand_delegates_to_matching_runner[natives]` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestOpsRunner::test_subcommand_delegates_to_matching_runner[doctor]` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestOpsRunner::test_subcommand_delegates_to_matching_runner[clean]` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestOpsRunner::test_subcommand_delegates_to_matching_runner[fleet]` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestOpsRunner::test_subcommand_delegates_to_matching_runner[deploy]` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestOpsRunner::test_subcommand_delegates_to_matching_runner[scaffold]` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestOpsRunner::test_subcommand_delegates_to_matching_runner[gitlog]` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestOpsRunner::test_stats_subcommand_delegates_to_stats_runner` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners.py::TestOpsRunner::test_unknown_subcommand_exits_1` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 10 passed (from 10 evidence id(s))
- gates: 0 error(s), 785 warning(s), 745 waived
- error-findings: none (measured, zero errors)
