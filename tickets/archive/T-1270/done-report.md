## Done report

Split 2 of the 32 residue files from T-1270's brief; re-filed the other 51-file
LARGE001 residue (repo-wide re-measurement, includes files newly grown over
threshold and 2 native/.rs files not on the original brief list) as a follow-up
ticket rather than closing silently.

1. src/frob/_cli_parsers/_ticket.py (1115 lines) -> package split. This module
   was a flat list of ~24 independent argparse-subparser-builder functions with
   a real grouping seam (creation / read-only query / state-progress-and-plumbing
   / closeout / metadata-mutation) and exactly one name (_add_ticket_parser) used
   outside the module. Split into _cli_parsers/_ticket/{_new,_query,_progress,
   _closeout,_metadata}.py (127-349 lines each) plus an __init__.py that
   re-exports the identical public surface via __all__, so _cli_parsers/__init__.py's
   own `from ._ticket import (...)` needed no changes. Pure move, no behavior change.

2. src/frob/app/config.py (1199 lines by the time this ticket started, up from
   1167 at brief time) -> extracted its two procedural blocks, which were the
   real seam distinct from the AppConfig pydantic schema itself:
   - AppConfig.from_external's ~380-line argparse-Namespace-to-kwargs field-copy
     loop -> app/_config_external.py's _build_external_config_kwargs(args, file,
     subcommand_cls); from_external is now a 2-line wrapper. subcommand_cls is
     passed as a parameter (not imported) specifically to avoid a config.py <->
     _config_external.py import cycle.
   - load_arch_config/_declared_frob_version/stale_install_warning plus the
     ARCH_DEFAULT_* constants (both read frob.toml/pyproject.toml directly and
     never touch an AppConfig instance) -> app/_config_meta.py, re-exported from
     config.py via a new __all__ so every existing `from frob.app.config import
     load_arch_config` (etc.) import keeps working unmodified.
   config.py is now 671 lines (was 1199); AppConfig's field-declaration block
   itself was left alone -- splitting a single pydantic model's field list would
   change the flat config.<dest> attribute shape every command handler reads by
   name, a structural change outside this ticket's pure-organizational scope,
   not a genuine split boundary.

Considered and rejected as force-splits: none waived this pass -- both files
turned out to have real procedural seams once read closely, so no
frob:waive LARGE001 was needed (an initial file-level waiver drafted for
config.py before the from_external/meta extraction was found was removed once
the real split landed).

Re-measured repo-wide LARGE001 after both splits: 51 unwaived findings (was 53
at T-1270's own brief measurement, 2 cleared). Filed the residue as a new
ticket (renumbered from T-1420 on land) carrying the full current
line-count list, the same split-first/waive-sparingly instruction, and a note
that src/frob/tickets/**/app/ticket_runner/** overlaps other concurrent
tickets' scope -- narrow via `frob ticket scope` before starting.

"Zero LARGE001 repo-wide" was not reachable in this one pass; 51 files remain,
tracked in the follow-up ticket rather than left unaccounted for.

### Changed
```
 src/frob/_cli_parsers/_ticket.py           | 1115 ----------------------------
 src/frob/_cli_parsers/_ticket/__init__.py  |  132 ++++
 src/frob/_cli_parsers/_ticket/_closeout.py |  349 +++++++++
 src/frob/_cli_parsers/_ticket/_metadata.py |  221 ++++++
 src/frob/_cli_parsers/_ticket/_new.py      |  145 ++++
 src/frob/_cli_parsers/_ticket/_progress.py |  240 ++++++
 src/frob/_cli_parsers/_ticket/_query.py    |  127 ++++
 src/frob/app/_config_external.py           |  415 +++++++++++
 src/frob/app/_config_meta.py               |  209 ++++++
 src/frob/app/config.py                     |  606 +--------------
 tickets.md                                 |  103 ++-
 11 files changed, 1978 insertions(+), 1684 deletions(-)
```

### Evidence
- `tests/unit/test_config.py::test_reads_override` (pytest node id, verified passing when recorded)
- `tests/unit/test_config.py::test_missing_toml_defaults` (pytest node id, verified passing when recorded)
- `tests/unit/test_config.py::test_stale_install_warning_flags_version_mismatch` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_config_from_external_t1276.py::TestFromExternal::test_reads_and_merges_tool_frob_table` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_config_from_external_t1276.py::TestFromArgs::test_delegates_to_from_external_with_pyproject_default` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_ticket.py::TestTicketRoundTrip::test_new_list_doable` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_ticket.py::TestTicketRoundTrip::test_close_with_evidence_and_done_report_succeeds` (pytest node id, verified passing when recorded)
- `tests/unit/test_main_entry.py::TestMainSigint::test_keyboard_interrupt_prints_clean_message_and_exits_130` (pytest node id, verified passing when recorded)
- `tests/unit/test_doctor_runner_t1276.py::TestDoctorRunnerHealthy::test_healthy_plain_prints_all_available_and_does_not_exit` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 9 passed (from 9 evidence id(s))
- gates: 12 error(s), 2112 warning(s), 692 waived
- error-findings: AFFECT001@src/frob/app/_config_meta.py, ARCH001@src/frob/app/_config_external.py, DRIFT002@docs/guides/agentic-workflow.md, DRIFT002@docs/modules/arch.md, DRIFT002@tests/unit/test_arch.py, DRIFT002@tests/unit/test_ticket_runner_land_cmd_flags.py, INV006@src/frob/_cli_parsers/_ticket/__init__.py, INV006@src/frob/_cli_parsers/_ticket/_closeout.py, INV006@src/frob/_cli_parsers/_ticket/_metadata.py, INV006@src/frob/_cli_parsers/_ticket/_progress.py, INV006@src/frob/_cli_parsers/_ticket/_query.py, PRE001@tickets/T-1270
