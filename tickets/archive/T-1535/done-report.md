## Done report

`frob check --land-parity` (T-1535): runs the EXACT same unscoped-error
evaluation the land pre-commit/post-land sweeps already run
(`_unscoped_error_findings` + `_drop_checkpoint_exempt_findings`, both
reused verbatim -- no second parser or exemption list), against the
worktree's CURRENT tree with no baseline diff, cache-bypassed
(`FROB_NO_GATE_CACHE=1` forced into the SPAWNED check's own environment
via `_unscoped_error_findings`'s new `env=` param, never mutating this
process's own `os.environ`). Wired as a new `_handle_early_exit_modes`
branch (`--land-parity` -> `_run_land_parity`) exactly like `--budget`;
exits 0 clean, 1 with every `(rule, file)` finding printed (or `--json`),
or 1 with a loud "could not evaluate" message on an unmeasurable run --
never a false-clean pass.

Real gap found and fixed while wiring the CLI flag (not hypothetical --
this is exactly the class of divergence this ticket exists to catch):
WIRE001 flagged that `check_land_parity` never appeared in
`_config_external.py`'s bool-flag passthrough tuple, so argparse parsed
the flag but `AppConfig.from_external` silently dropped it before
`AppConfig(**d)` -- the CLI flag existed and did nothing. `frob check
--land-parity` itself, run against this ticket's own uncommitted state
via `frob check --only test/archgate/coverage/sys`, never would have
caught this (`--only`/`--ticket` skip WIRE); only running a REAL unscoped
`frob check --land-parity` end to end (once the flag actually worked)
surfaced it directly as "full check ran instead of short-circuiting."
Fixed by adding `"check_land_parity"` to the passthrough tuple; verified
by then running the real CLI (`frob check --land-parity`) and confirming
it short-circuits to the one-line spawn-and-report path instead of a full
check.

The property test this ticket names: `TestLandParityFindings.
test_parity_with_the_land_sweeps_own_exemption_function` pins that
`land_parity_findings`'s output on a fixed raw finding set is
byte-identical to calling the land sweeps' OWN `_drop_checkpoint_exempt_
findings` directly against that same set -- same parser, same exclusions,
by construction (both consumers of the one shared function), not by
convention.

Playbook gains section 6g ("run `frob check --land-parity` before writing
your Done report"), docs/modules/tickets.md gains the `## frob check
--land-parity (T-1535)` section.

Scoped verification: `frob check --only test --only archgate --only
coverage --only sys --ticket T-1535` -- 0 errors (two rounds of real
self-inflicted findings fixed along the way: ARCH001 on
`_rewrite_node_may_grants`, T-1531's own function, split into
`_widen_existing_may_grants`/`_insert_new_may_grants`; a batch of missing
`frob:ticket T-1531`/`T-1535` markers on symbols COV002 correctly flagged
as changed-with-no-open-ticket-edge; SELFAUDIT001 SYS100/SYS104 drift on
`design/frob.strata` fixed by running THIS REPO'S OWN sync_may_report/
apply_sync_may plus sync_interface_report/apply_sync_interface directly,
same dogfood pattern T-1531's Done report also used). `frob check
--land-parity` itself (run for real, per this ticket's own instruction,
after the WIRE001 fix) -- 0 errors, matches the scoped result. `ruff
check`/`ruff format` clean on every touched file. `git diff main
--diff-filter=D --stat` is empty.

### Changed
```
 design/frob.strata                         | 1038 ++++++++++++++--------------
 docs/guides/agent-playbook.md              |   32 +
 docs/modules/gates.md                      |   68 ++
 docs/modules/tickets.md                    |   71 ++
 src/frob/_cli_parsers/_check.py            |   12 +
 src/frob/_cli_parsers/_ticket/_closeout.py |   13 +
 src/frob/app/_config_external.py           |    4 +
 src/frob/app/check_runner.py               |   54 +-
 src/frob/app/config.py                     |   13 +
 src/frob/app/ticket_runner/_land_cmd.py    |   88 ++-
 src/frob/app/ticket_runner/_verify.py      |   69 +-
 src/frob/gates/_fix_engine.py              |  125 ++++
 src/frob/strata/_sync_may.py               |  412 +++++++++++
 src/frob/tickets/__init__.py               |    2 +
 src/frob/tickets/_evidence.py              |  158 +++++
 src/frob/tickets/_models.py                |    9 +
 tests/test_gates.py                        |   93 +++
 tests/test_ticket_work_and_land_finish.py  |   73 ++
 tests/test_tickets_evidence_cli.py         |  183 +++++
 tests/unit/strata/test_sync_may.py         |  167 +++++
 tickets.md                                 |  556 ++++++++++++++-
 21 files changed, 2704 insertions(+), 536 deletions(-)
```

### Evidence
- `tests/test_ticket_work_and_land_finish.py::TestLandParityFindings::test_none_when_unmeasurable` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestLandParityFindings::test_forces_no_gate_cache_env_on_the_spawn` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestLandParityFindings::test_parity_with_the_land_sweeps_own_exemption_function` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 1 error(s), 537 warning(s), 799 waived
- error-findings: PRE001@tickets/T-1535
