## Done report

Narrowed from T-1674's unscoped ticket to items 1+2 for the `frob ticket
<verb>` dispatch choke point specifically (`app/ticket_runner/__init__.py`
`run()`): item 3 (per-verb ownership refusal) explicitly overlaps T-1669
per the ticket's own body and is left there; widening to every OTHER
frob subcommand family (not just `frob ticket`) is a natural, disclosed
follow-up, not done in this pass.

`_resolve_ticket_root(cfg)`: `--path`/`cfg.ticket_path` when explicitly
given always wins; else `FROB_ROOT` env var; else cwd (unchanged
default). `--path`'s CLI default is the literal string "." (argparse
always supplies something), so `ticket_path == "."` is treated as "not
explicitly overridden" and still checks `FROB_ROOT` -- verified this
distinction manually (see below) since it is the one subtle part of the
implementation.

The resolved root is now logged UNCONDITIONALLY (not behind -v) for
every verb except the read-only allowlist (`_LAND_SAFE_READ_ONLY_VERBS`,
already defined for T-1779's dispatch guard) -- reuses that same set
rather than inventing a second "which verbs matter" classification.

Manually verified against three real invocations in scratch repos (not
just unit tests): plain `frob ticket new` logs its own cwd; `FROB_ROOT=X
frob ticket new` (run from a DIFFERENT directory) correctly targets X and
logs it; `frob ticket new --path Y` with FROB_ROOT also set targets Y,
confirming explicit --path wins.

`frob check --only prework --only scope --only sys --ticket T-1674` is
clean. `frob check --only coverage` shows 0 new COV002/COV005/COV007
findings for touched symbols (COV005/COV007 initially fired because the
frob:doc anchor rode onto the newly-extracted private `_resolve_ticket_
root` instead of staying on the public `run()` caller -- moved back).

### Changed
```
 CHANGELOG.md                              |  18 -----
 rapid-debt.jsonl                          |   1 +
 src/frob/app/ticket_runner/_lifecycle.py  |  66 +++++++++++++++
 tests/test_ticket_work_and_land_finish.py |  74 +++++++++++++++++
 tickets/T-1674/ticket.md                  | 128 +++++++++++++++++++++++++++++-
 tickets/T-1786/ticket.md                  |   5 +-
 tickets/T-1790/done-report.md             |  54 +++++++++++++
 tickets/T-1790/ticket.md                  |  41 +++++++++-
 tickets/T-1795/ticket.md                  |  69 ++++++++++++++++
 tickets/T-1796/ticket.md        |  93 ++++++++++++++++++++++
 10 files changed, 527 insertions(+), 22 deletions(-)
```

### Evidence
- `tests/unit/test_app_runners_batch7.py::TestTicketRunnerRootResolution::test_frob_root_env_used_when_path_not_explicit` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketRunnerRootResolution::test_explicit_path_wins_over_frob_root` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketRunnerRootResolution::test_no_frob_root_falls_back_to_cwd_default` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketRunnerRootResolution::test_resolved_root_is_logged_for_a_mutating_verb` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 3 error(s), 785 warning(s), 725 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/__init__.py, DUP001@src/frob/app/ticket_runner/_lifecycle.py, SEC110@src/frob/app/ticket_runner/__init__.py
