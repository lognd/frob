## Done report

T-4689 -- telemetry records verb and subverb on every frob invocation

WHAT CHANGED

src/frob/app/telemetry/__init__.py
  - record_cli_event(): new `subverb: str | None = None` kwarg. Writes
    two new fields into the kind="cli" record: `verb` (same value as the
    existing `subcommand`, kept verbatim for back-compat -- footgun
    dedup keys on (subcommand, args_head) and frob.stats._agentic already
    read `subcommand`, neither is touched) and `subverb`. Logs the
    classification decision at DEBUG.
  - _finish_timed_call() / timed_call(): thread a new `subverb` kwarg
    through to record_cli_event, unexamined.
  - Docstrings updated to describe the new fields and the deliberate gap
    (argparse's own --help/usage-error SystemExit happens before App is
    even constructed, so timed_call is never entered for those -- filed
    as a new ticket, see "Filed" below, not silently absorbed into this
    one's scope).

src/frob/app/app.py
  - App.__call__: after resolving `subcommand`, reads `subverb =
    getattr(self._cfg, f"{verb}_command", None)` -- the same `<verb>_
    command` naming convention every group verb's AppConfig field
    already follows (ticket_command, explore_command, quality_command,
    ...). Passed through to timed_call. Logs at DEBUG. Added `# frob:
    ticket T-4689` on the `App` class itself (COV002 needs the ticket
    edge on the changed symbol, not just a nearby comment).
  - This file was NOT in T-4689's declared or implicit scope (the call
    site the ticket assumed lived in __main__.py actually lives in
    app.py's App.__call__) -- added via `frob ticket scope T-4689 --add
    src/frob/app/app.py` from inside the worktree after confirming no
    other in-progress ticket leases it.

.claude/hooks/tool-call-telemetry.py
  - New `_is_frob_token`, `_extract_verb_subverb`, `_frob_verb_subverb`:
    a lexical scan of a Bash tool call's `command` string that finds the
    first (leftmost, across `&&`/`;`/`|`/backtick/`$(`-separated
    segments) resolvable `frob <verb> [<subverb>]` invocation. Recognizes
    the frob executable by exact basename match (`tok.rsplit("/", 1)[-1]
    == "frob"`), which uniformly covers `frob`, `uv run frob`,
    `.venv/bin/frob`, `python -m frob`, and `nice -n 10 ... frob` without
    any per-wrapper special case -- none of `uv`, `run`, `python`, `-m`,
    `nice`, `-n`, `10` ever match the basename test, so the scan simply
    passes over them. `_extract_verb_subverb` requires strict token
    adjacency for the subverb (tokens[0]=verb, tokens[1]=subverb only if
    it sits immediately after with no flag in between) specifically so a
    flag's VALUE (`--only dup`'s `dup`) is never misclassified as a
    subverb -- there is no parsed AppConfig to disambiguate on this side,
    unlike record_cli_event.
  - `_build_record` calls `_frob_verb_subverb` for `Bash` calls only and
    adds `verb`/`subverb` to the record ONLY when resolved -- a non-frob
    command (or a frob command whose verb could not be resolved) omits
    both fields entirely, never writes them as None/empty-string.
  - Added a stdlib `logging.getLogger` module logger (no `frob` import,
    matching the file's existing constraint): DEBUG on every successful
    classification, INFO when a frob-looking command could not be
    classified.
  - Module docstring updated with a short T-4689 paragraph.

tests/unit/test_telemetry_verb_recording.py (new)
  - test_record_cli_event_carries_verb_and_subverb /
    test_record_cli_event_subverb_defaults_to_none: kind="cli" record
    shape.
  - TestAppDispatchRecordsSubverb: drives the real App.__call__ end to
    end against a tmp_path telemetry root (git-free -- App/timed_call
    never spawns git for verb/subverb, only for tree_hash, which
    tolerates "unknown"). test_ticket_show_records_verb_ticket_subverb_
    show is the ticket's own named positive control (verb=ticket,
    subverb=show for `frob ticket show T-xxxx`). A second test proves a
    leaf verb (`frob dup`, no `dup_command` field) records subverb=None.
  - TestHookParsesFrobVerbFromBash: loads the hook module by path (same
    way Claude Code invokes it) and asserts on all five ticket-named
    command shapes (uv run / .venv/bin / python -m / nice -n 10 /
    compound-with-several-frob-calls) plus the non-frob negative case and
    _build_record's field-omission behavior.

docs/guides/agentic-time-profiling.md
  - "What gets recorded" section: new paragraph on verb/subverb for the
    kind="cli" side.
  - "Tool-call telemetry (T-2912)" section: new paragraph on verb/subverb
    for the kind="tool" side, naming all five recognized command shapes.
  - Public API code block: record_cli_event and timed_call signatures
    updated with the new `subverb=None` kwarg.

WHY

Measured (T-4687/T-4689's own body): 34,388 telemetry rows, 91% (31,418)
with an empty `subcommand`. Every kind=tool row was empty because the
hook never parsed a verb at all; kind=cli rows only ever kept the FIRST
word, so `frob ticket show` and `frob ticket land` were indistinguishable
(2,165 of 2,970 cli rows collapsed into one "ticket" bucket). This blocks
the rest of the CLI-surface-reduction story (T-4690..T-4698) from ranking
the tail of 51 top-level verbs / 54 ticket subverbs from real usage data,
forcing it to fall back on git-grep citation counts. This ticket makes the
NEXT round data-driven and gives future sunset shims a way to prove
nobody still calls a deprecated spelling.

ACCEPTANCE CRITERIA -> EVIDENCE

[1] "Given a fixture telemetry root, when frob ticket show T-xxxx runs,
    then the appended .frob/telemetry.jsonl row carries verb=ticket and
    subverb=show" ->
    tests/unit/test_telemetry_verb_recording.py::TestAppDispatchRecordsSubverb::test_ticket_show_records_verb_ticket_subverb_show
    Drives the real App(cfg)() with AppConfig(subcommand=Subcommand.
    ticket, ticket_command="show") against a tmp_path root and asserts
    the written row's verb/subverb fields directly.

[2] "Given a kind=tool hook payload whose Bash command invokes frob, when
    the hook records it, then the row carries the same verb/subverb
    fields; a non-frob Bash command records neither rather than a
    guess" ->
    tests/unit/test_telemetry_verb_recording.py::TestHookParsesFrobVerbFromBash
    (test_uv_run_frob, test_dot_venv_bin_frob, test_python_dash_m_frob,
    test_nice_wrapped_frob, test_compound_command_several_frob_calls,
    test_non_frob_bash_command_records_neither,
    test_build_record_omits_verb_subverb_for_non_frob_command,
    test_build_record_includes_verb_subverb_for_frob_command)

Test node ids bound as evidence (frob ticket evidence T-4689, --base-ref
dev):
  tests/unit/test_telemetry_verb_recording.py::TestAppDispatchRecordsSubverb::test_ticket_show_records_verb_ticket_subverb_show
  tests/unit/test_telemetry_verb_recording.py::TestHookParsesFrobVerbFromBash::test_uv_run_frob
  tests/unit/test_telemetry_verb_recording.py::TestHookParsesFrobVerbFromBash::test_dot_venv_bin_frob
  tests/unit/test_telemetry_verb_recording.py::TestHookParsesFrobVerbFromBash::test_python_dash_m_frob
  tests/unit/test_telemetry_verb_recording.py::TestHookParsesFrobVerbFromBash::test_nice_wrapped_frob
  tests/unit/test_telemetry_verb_recording.py::TestHookParsesFrobVerbFromBash::test_compound_command_several_frob_calls
  tests/unit/test_telemetry_verb_recording.py::TestHookParsesFrobVerbFromBash::test_non_frob_bash_command_records_neither

Full local run (all green): tests/unit/test_telemetry_verb_recording.py
(12 passed), tests/test_telemetry.py (40 passed, unaffected by the new
kwargs), tests/unit/test_app_lazy_dispatch.py + tests/unit/test_app_runners.py
(113 passed, App/app.py dispatch unaffected).

COMMITS
  48c25934a feat(telemetry): record verb and subverb on every frob invocation
  0534f5f65 fix(telemetry): bind App to T-4689 and format the new test file
  (plus ticket-ledger self-commits from `frob ticket scope`/`evidence`)

SCOPE

Declared scope was .claude/hooks/tool-call-telemetry.py,
src/frob/app/telemetry/**, tests/unit/test_telemetry_verb_recording.py.
Added src/frob/app/app.py via `frob ticket scope T-4689 --add` after
discovering App.__call__ (the timed_call call site) lives there, not in
__main__.py as the ticket's implicit_scope grant assumed; app.py was not
leased by any other in-progress ticket at the time.

FILED (out of scope, not touched)

T-5128 "record verb/subverb for --help and argparse usage-error
exits" -- argparse's own --help/usage-error SystemExit happens inside
parser.parse_args, before App()/timed_call is ever entered, so those
exits currently record no telemetry row at all (not even an empty one).
Scoped to src/frob/__main__.py. Filed from ROOT per the sanctioned
`frob ticket new` path.

## Pre-READY checks

`frob check --only sys --files .claude/hooks/tool-call-telemetry.py --files src/frob/app/app.py --files src/frob/app/telemetry/__init__.py --files tests/unit/test_telemetry_verb_recording.py --base dev`
  -> FAIL overall (gate:DRIFT 6 errors/5 waived, gate:DSL 1 error) but
  ZERO findings on any of the four touched files -- every DRIFT001/DSL001
  hit is on pre-existing, unrelated files (src/frob/app/ticket_runner/
  _rapid_sweep.py, src/frob/gates/invariants.py, src/frob/tickets/
  _evidence.py, tests/test_app.py). No SELFAUDIT001 anywhere in the
  output. Confirmed by `grep` for each touched path against the raw
  output: no hits.

`frob check --only arch --files .claude/hooks/tool-call-telemetry.py --files src/frob/app/app.py --files src/frob/app/telemetry/__init__.py --files tests/unit/test_telemetry_verb_recording.py --base dev`
  -> pass: frob-arch 20 warnings (36 waived), 546 suggestions -- 0 errors,
  no ARCH001/LARGE001, none of the pattern-recommendation/anti-pattern
  hits name any touched file.

`frob check --only coverage --files .claude/hooks/tool-call-telemetry.py --files src/frob/app/app.py --files src/frob/app/telemetry/__init__.py --files tests/unit/test_telemetry_verb_recording.py --base dev`
  -> First run surfaced one real finding: COV002 on src/frob/app/app.py
  (App changed with no frob:ticket edge) -- fixed by adding `# frob:
  ticket T-4689` on the App class, then re-ran clean for that file (21
  errors overall afterward, all pre-existing/unrelated: gate:COV's
  remaining 9 are private-symbol frob:doc waived-precedent hits in
  src/frob/vet/*, gate:DRIFT's 6 are the same pre-existing hits as above,
  gate:DSL's 1 is tests/test_app.py:387 (pre-existing), gate:TODO's 5 are
  pre-existing unrelated frob:todo bindings). No COV002/COV005/COV007 on
  any touched file in the second run.

`ruff check .claude/hooks/tool-call-telemetry.py src/frob/app/app.py src/frob/app/telemetry/__init__.py tests/unit/test_telemetry_verb_recording.py`
  -> All checks passed!

`ty check src/frob/app/app.py src/frob/app/telemetry/__init__.py tests/unit/test_telemetry_verb_recording.py`
  -> All checks passed!

(also ran, not part of the required five but relevant: `ruff format
--check` initially flagged the new test file -- reformatted with `ruff
format`, then `ruff check` and the full pytest run above re-verified
green.)

### Changed
```
 .claude/hooks/_root_write_guard_lib.py             |  24 +-
 .claude/hooks/frob-suggest.py                      |  46 +-
 .claude/hooks/frob-timeout-guard.py                | 127 ++-
 .claude/hooks/tool-call-telemetry.py               | 109 +++
 .frob-release.json                                 |   2 +-
 .github/workflows/ci.yml                           | 107 ++-
 CHANGELOG.md                                       |  71 ++
 changelog.d/T-2965.md                              |   2 +
 changelog.d/T-3020.md                              |   2 +
 changelog.d/T-3232.md                              |   2 +
 changelog.d/T-3233.md                              |   2 +
 changelog.d/T-3612.md                              |   2 +
 changelog.d/T-3613.md                              |   2 +
 changelog.d/T-3615.md                              |   2 +
 changelog.d/T-3856.md                              |   2 +
 changelog.d/T-3943.md                              |   2 +
 changelog.d/T-3961.md                              |   2 +
 changelog.d/T-4111.md                              |   2 +
 changelog.d/T-4116.md                              |   2 +
 changelog.d/T-4214.md                              |   2 +
 changelog.d/T-4221.md                              |   2 +
 changelog.d/T-4230.md                              |   2 +
 changelog.d/T-4413.md                              |   2 +
 changelog.d/T-4414.md                              |   2 +
 changelog.d/T-4415.md                              |   2 +
 changelog.d/T-4491.md                              |   2 +
 changelog.d/T-4492.md                              |   2 +
 changelog.d/T-4493.md                              |   2 +
 changelog.d/T-4494.md                              |   2 +
 changelog.d/T-4495.md                              |   2 +
 changelog.d/T-4496.md                              |   2 +
 changelog.d/T-4498.md                              |   2 +
 changelog.d/T-4501.md                              |   2 +
 changelog.d/T-4502.md                              |   2 +
 changelog.d/T-4503.md                              |   2 +
 changelog.d/T-4507.md                              |   2 +
 changelog.d/T-4508.md                              |   2 +
 changelog.d/T-4510.md                              |   2 +
 changelog.d/T-4511.md                              |   2 +
 changelog.d/T-4512.md                              |   2 +
 changelog.d/T-4514.md                              |   2 +
 changelog.d/T-4517.md                              |   2 +
 changelog.d/T-4519.md                              |   2 +
 changelog.d/T-4520.md                              |   2 +
 changelog.d/T-4521.md                              |   2 +
 changelog.d/T-4522.md                              |   2 +
 changelog.d/T-4523.md                              |   2 +
 changelog.d/T-4524.md                              |   2 +
 changelog.d/T-4531.md                              |   2 +
 changelog.d/T-4532.md                              |   2 +
 changelog.d/T-4535.md                              |   2 +
 changelog.d/T-4536.md                              |   2 +
 changelog.d/T-4540.md                              |   2 +
 changelog.d/T-4543.md                              |   2 +
 changelog.d/T-4547.md                              |   2 +
 changelog.d/T-4548.md                              |   2 +
 changelog.d/T-4550.md                              |   2 +
 changelog.d/T-4552.md                              |   2 +
 changelog.d/T-4553.md                              |   2 +
 changelog.d/T-4554.md                              |   2 +
 changelog.d/T-4555.md                              |   2 +
 changelog.d/T-4556.md                              |   2 +
 changelog.d/T-4562.md                              |   2 +
 changelog.d/T-4563.md                              |   2 +
 changelog.d/T-4572.md                              |   2 +
 changelog.d/T-4579.md                              |   2 +
 changelog.d/T-4582.md                              |   2 +
 changelog.d/T-4583.md                              |   2 +
 changelog.d/T-4588.md                              |   2 +
 changelog.d/T-4596.md                              |   2 +
 changelog.d/T-4607.md                              |   2 +
 changelog.d/T-4633.md                              |   2 +
 changelog.d/T-4634.md                              |   2 +
 changelog.d/T-4642.md                              |   2 +
 changelog.d/T-4646.md                              |   2 +
 changelog.d/T-4649.md                              |   2 +
 changelog.d/T-4650.md                              |   2 +
 changelog.d/T-4659.md                              |   2 +
 design/frob.strata                                 | 167 ++--
 docs/commands/check.md                             |  88 +-
 docs/commands/narrative.md                         |   8 +
 docs/commands/scaffold.md                          |  50 +-
 docs/commands/ticket.md                            |  72 ++
 docs/commands/xref.md                              |  16 +-
 docs/design/cli-regrouping.md                      |  73 ++
 .../registry/capability-via-ratchet.lock.json      |  87 +-
 docs/design/registry/check-coverage.yaml           |   7 +-
 docs/guides/agentic-time-profiling.md              |  26 +-
 docs/guides/extending/comment-dsl-directives.md    |  13 +-
 docs/guides/install.md                             |  40 +
 docs/guides/release.md                             |  37 +
 docs/guides/unity.md                               |  83 ++
 docs/modules/app.md                                |  20 +
 docs/modules/dup.md                                |  12 +
 docs/modules/gate-sys111-ratchet-auto-accept.md    |  95 ++
 docs/modules/gate-time-stable-invariant.md         |  74 ++
 docs/modules/gates.md                              | 165 +++-
 docs/modules/graph.md                              |  39 +
 docs/modules/lang.md                               |  33 +
 docs/modules/testing.md                            |  37 +
 docs/modules/tickets-data-storage.md               |   8 +
 docs/modules/tickets-landing.md                    | 239 ++++-
 docs/modules/tickets-lifecycle.md                  |  58 ++
 docs/modules/tickets.md                            |  70 +-
 docs/strata/surface.md                             |  40 +
 frob.lock                                          |  42 +-
 frob.toml                                          |  18 +
 pyproject.toml                                     |  22 +-
 src/frob/__init__.py                               |   2 +
 src/frob/__main__.py                               |  26 +-
 src/frob/_cli_parsers/__init__.py                  |   2 +
 src/frob/_cli_parsers/_check.py                    | 295 ++++++-
 src/frob/_cli_parsers/_core.py                     |  33 +-
 src/frob/_cli_parsers/_design.py                   |  24 +-
 src/frob/_cli_parsers/_explore.py                  | 102 ++-
 src/frob/_cli_parsers/_misc.py                     |  56 +-
 src/frob/_cli_parsers/_ops.py                      |  38 +-
 src/frob/_cli_parsers/_root.py                     |  20 +-
 src/frob/_cli_parsers/_ticket/__init__.py          |  55 +-
 .../_cli_parsers/_ticket/_closeout_evidence.py     |  21 +
 src/frob/_cli_parsers/_ticket/_metadata.py         |  53 +-
 src/frob/_cli_parsers/_ticket/_progress.py         | 144 ++-
 src/frob/app/_config_external.py                   |  19 +
 src/frob/app/app.py                                |  15 +-
 src/frob/app/check_runner.py                       | 154 +++-
 src/frob/app/config.py                             |  92 +-
 src/frob/app/telemetry/__init__.py                 |  47 +-
 src/frob/app/ticket_runner/__init__.py             | 125 ++-
 src/frob/app/ticket_runner/_close_cmd.py           |  10 +-
 src/frob/app/ticket_runner/_land_cmd.py            | 532 ++++++++++-
 src/frob/app/ticket_runner/_lifecycle.py           |  79 +-
 src/frob/app/ticket_runner/_mutate.py              |  39 +-
 src/frob/app/ticket_runner/_rapid_sweep.py         | 664 +++++++++++++-
 src/frob/app/ticket_runner/_verify.py              | 245 +++++-
 src/frob/check/__init__.py                         | 244 ++++--
 src/frob/check/_python.py                          | 152 +++-
 src/frob/docs/__init__.py                          |  64 +-
 src/frob/doctor.py                                 | 227 ++++-
 src/frob/dup/_legacy.py                            |  60 +-
 src/frob/dup/_legacy_cs.py                         | 207 +++++
 src/frob/excludes.py                               |  83 +-
 src/frob/gates/__init__.py                         | 263 +++---
 src/frob/gates/_claim_lint.py                      | 202 +++++
 src/frob/gates/_coverage.py                        | 203 ++++-
 src/frob/gates/_fix_engine.py                      |  94 +-
 src/frob/gates/_fix_engine_sync.py                 |  69 +-
 src/frob/gates/_guard_closure.py                   | 301 +++++++
 src/frob/gates/_inv.py                             | 359 ++++++++
 src/frob/gates/_lang_conformance.py                |  36 +-
 src/frob/gates/_models.py                          |   7 +
 src/frob/gates/_narrative_blocks.py                |  28 +-
 src/frob/gates/_suppress.py                        |  46 +-
 src/frob/gates/_waive.py                           | 170 +++-
 src/frob/graph/affects.py                          |  53 ++
 src/frob/graph/dsl.py                              | 185 +++-
 src/frob/lang/__init__.py                          |  17 +-
 src/frob/lang/_extract.py                          |  13 +
 src/frob/lang/_nodes.py                            | 159 +++-
 src/frob/lang/_project_detect.py                   | 147 ++++
 src/frob/lang/_support.py                          |  23 +-
 src/frob/lang/_walk_csharp.py                      | 111 ++-
 src/frob/scaffold/_unity_project.py                | 193 ++++
 .../scaffold/data/types/unity-project/frob.toml.j2 |  64 ++
 src/frob/scaffold/project.py                       |   6 +-
 src/frob/strata/_effects.py                        | 780 +++++++++++++++--
 src/frob/strata/_unity_asmdef.py                   | 412 +++++++++
 src/frob/testing/__init__.py                       |   9 +
 src/frob/testing/_collect.py                       |  21 +-
 src/frob/testing/_collect_csharp.py                | 327 +++++++
 src/frob/testing/_dotnet_runner.py                 | 251 ++++++
 src/frob/testing/_runners.py                       |  10 +
 src/frob/testing/_stackdump.py                     |  68 +-
 src/frob/testing/_unity_batchmode.py               | 298 +++++++
 src/frob/tickets/__init__.py                       |   2 +
 src/frob/tickets/_land.py                          | 274 +++++-
 src/frob/tickets/_land_compose.py                  | 209 +++--
 src/frob/tickets/_land_git_ops.py                  | 149 +++-
 src/frob/tickets/_land_queue.py                    | 151 +++-
 src/frob/tickets/_land_squash.py                   | 263 +++++-
 src/frob/tickets/_leases.py                        | 617 +++++++++----
 src/frob/tickets/_models.py                        |  80 +-
 src/frob/tickets/_registry_files.py                | 145 +++
 src/frob/tickets/_setters.py                       | 113 +--
 src/frob/tickets/_store.py                         | 120 ++-
 src/frob/tickets/_worktree_sweep.py                |  17 +-
 src/frob/vet/_capability.py                        |  10 +-
 src/frob/vet/_capability_csharp.py                 | 465 ++++++++++
 .../_dangerous_ops_bash_csharp.py                  |  17 +
 src/frob/vet/_capability_registry/_dotnet_bcl.py   | 214 +++++
 src/frob/vet/_capability_registry/_matrix.py       |  13 +-
 src/frob/vet/_capability_registry/_unity_api.py    | 305 +++++++
 src/frob/vet/_capability_scan.py                   |  13 +-
 src/frob/xref/__init__.py                          |  75 +-
 .../csharp_dup_docblock/Sample/Dup/Duplicate.cs    |  37 +
 tests/fixtures/csharp_dup_docblock/guide.md        |  36 +
 .../python_control/duplicate.py                    |  29 +
 tests/fixtures/dsl_todo_notes/sample.c             |   3 +
 tests/fixtures/dsl_todo_notes/sample.cpp           |   3 +
 tests/fixtures/dsl_todo_notes/sample.cs            |   3 +
 tests/fixtures/dsl_todo_notes/sample.cu            |   3 +
 tests/fixtures/dsl_todo_notes/sample.java          |   3 +
 tests/fixtures/dsl_todo_notes/sample.kt            |   3 +
 tests/fixtures/dsl_todo_notes/sample.py            |   9 +
 tests/fixtures/dsl_todo_notes/sample.rs            |   3 +
 tests/fixtures/dsl_todo_notes/sample.sh            |   3 +
 tests/fixtures/dsl_todo_notes/sample.ts            |   3 +
 tests/fixtures/dsl_todo_notes/sample.zig           |   3 +
 tests/fixtures/lang/csharp/alias_using_fs_write.cs |  14 +
 .../lang/csharp/combined_static_and_namespace.cs   |  16 +
 tests/fixtures/lang/csharp/directives.cs           |  44 +
 .../dotnet_bcl_activator_createinstance_eval.cs    |  12 +
 .../lang/csharp/dotnet_bcl_assembly_load_eval.cs   |  12 +
 .../lang/csharp/dotnet_bcl_directory_fs_write.cs   |  12 +
 tests/fixtures/lang/csharp/dotnet_bcl_dns_net.cs   |  12 +
 .../dotnet_bcl_jsonserializer_deserialize.cs       |  12 +
 .../lang/csharp/dotnet_bcl_registry_fs_write.cs    |  12 +
 .../lang/csharp/dotnet_bcl_sqlcommand_sql.cs       |  13 +
 .../lang/csharp/dotnet_bcl_streamreader_fs_read.cs |  13 +
 .../csharp/dotnet_bcl_streamwriter_fs_write.cs     |  13 +
 .../lang/csharp/dotnet_bcl_type_gettype_eval.cs    |  12 +
 .../fixtures/lang/csharp/nested_property_event.cs  |  37 +
 tests/fixtures/lang/csharp/no_dangerous_apis.cs    |  17 +
 tests/fixtures/lang/csharp/plain_using_fs_write.cs |  12 +
 tests/fixtures/lang/csharp/static_using_console.cs |  12 +
 .../fixtures/lang/csharp/tests/SampleNunitTests.cs |  30 +
 .../fixtures/lang/csharp/tests/SampleUnityTests.cs |  15 +
 .../lang/csharp/tests/malformed_results.xml        |   5 +
 .../fixtures/lang/csharp/tests/sample_results.trx  |  15 +
 .../lang/csharp/tests/sample_unity_results.xml     |   9 +
 tests/fixtures/lang/csharp/unity/coroutine.cs      |  20 +
 .../lang/csharp/unity/lifecycle_methods.cs         |  21 +
 tests/fixtures/lang/csharp/unity/menu_item.cs      |  18 +
 tests/fixtures/lang/csharp/var_local_httpclient.cs |  12 +
 .../Assets/Editor/Editor.asmdef                    |   6 +
 .../Assets/Editor/Editor.asmdef.meta               |   2 +
 tests/fixtures/unity_sample_asmdef/Assets/Loose.cs |   2 +
 .../Assets/Runtime/Runtime.asmdef                  |   6 +
 .../Assets/Runtime/Runtime.asmdef.meta             |   2 +
 .../Assets/RuntimeUtils/RuntimeUtils.asmdef        |   6 +
 .../Assets/RuntimeUtils/RuntimeUtils.asmdef.meta   |   2 +
 .../unity_sample_asmdef/Assets/Tests/Tests.asmdef  |   6 +
 .../Assets/Tests/Tests.asmdef.meta                 |   2 +
 .../unity_sample_asmdef/Packages/manifest.json     |   3 +
 .../ProjectSettings/ProjectVersion.txt             |   2 +
 tests/gates_suite/test_claim_lint.py               | 163 ++++
 tests/gates_suite/test_coverage.py                 | 132 ++-
 tests/gates_suite/test_fix_engine.py               | 123 +++
 tests/gates_suite/test_guard_closure.py            | 228 +++++
 tests/gates_suite/test_invariant.py                | 116 +++
 tests/test_check_gate_base.py                      |  54 ++
 tests/test_docenum_gate.py                         |  41 +
 tests/test_excludes.py                             |  75 ++
 tests/test_gates_suppress.py                       |  34 +-
 tests/test_hook_frob_suggest.py                    |  47 +
 tests/test_hook_frob_timeout_guard.py              |  54 ++
 tests/test_hook_root_write_guard.py                |  89 ++
 tests/test_lang.py                                 |  90 ++
 tests/test_lang_conformance_gate.py                |  81 +-
 tests/test_narrative_blocks.py                     |  27 +
 tests/test_testing.py                              | 106 ++-
 tests/test_ticket_leases.py                        | 313 ++++---
 tests/test_ticket_work_and_land_finish.py          | 206 +++--
 tests/test_tickets_migration.py                    | 121 ++-
 tests/test_tickets_parent.py                       | 208 +++++
 tests/test_tickets_registry_files.py               | 206 +++++
 tests/test_waive_gate.py                           | 145 +++
 tests/ticket_land_suite/test_verify_intent.py      |  85 +-
 tests/unit/graph/test_dsl.py                       | 164 +++-
 tests/unit/graph/test_dsl_invariant_property.py    |  69 ++
 tests/unit/lang/test_csharp_directives.py          | 115 +++
 tests/unit/rapid_sweep_suite/test_dispose.py       |  39 +
 tests/unit/rapid_sweep_suite/test_filing.py        |  33 +
 tests/unit/rapid_sweep_suite/test_window.py        | 457 ++++++++++
 tests/unit/strata/test_effects.py                  |  44 +
 tests/unit/strata/test_selfconform.py              | 460 +++++++++-
 tests/unit/strata/test_unity_asmdef.py             | 160 ++++
 ...t_app_config_pyproject_root_t_draft_1f1ae69b.py |  57 ++
 tests/unit/test_app_runners_batch7.py              | 128 +--
 tests/unit/test_check_scoped_files.py              | 566 ++++++++++++
 tests/unit/test_check_skip_flag.py                 | 192 ++++
 tests/unit/test_ci_self_gate_unscoped.py           | 189 ++++
 tests/unit/test_cli_group_parity.py                | 220 +++++
 tests/unit/test_cli_lang_choices_drift.py          | 113 +++
 tests/unit/test_cli_single_child_groups.py         | 106 +++
 tests/unit/test_dev_branch_workflow.py             |  50 ++
 tests/unit/test_docs_module.py                     |  60 +-
 tests/unit/test_doctor.py                          | 116 +++
 tests/unit/test_done_report_check_scope.py         | 177 ++++
 tests/unit/test_dotnet_runner.py                   | 194 ++++
 tests/unit/test_land_cas_ledger_retry.py           | 312 +++++++
 tests/unit/test_land_default_queue.py              | 128 +++
 tests/unit/test_land_in_progress_window.py         | 351 ++++++++
 tests/unit/test_land_leaked_tickets_lease_hoist.py |  95 ++
 tests/unit/test_land_merge_conflict_drop.py        | 198 +++++
 tests/unit/test_land_queue.py                      | 114 +++
 tests/unit/test_land_stackdump.py                  | 321 +++++++
 tests/unit/test_lang_project_detect.py             | 108 +++
 tests/unit/test_lease_lifecycle.py                 | 180 ++++
 tests/unit/test_leases_staleness_perf.py           | 310 +++++++
 tests/unit/test_lifecycle_work_base.py             | 217 +++++
 tests/unit/test_pyproject_data_memoization.py      | 124 +++
 tests/unit/test_rel002_dev_suffix.py               | 113 +++
 tests/unit/test_scaffold_unity_project.py          | 128 +++
 tests/unit/test_store_mode_memoization.py          | 110 +++
 tests/unit/test_support_csharp.py                  | 190 ++++
 tests/unit/test_suppress_worktree_path.py          |  87 ++
 tests/unit/test_telemetry_verb_recording.py        | 200 +++++
 tests/unit/test_ticket_cli_surface.py              | 182 ++++
 tests/unit/test_ticket_runner_land_cmd_flags.py    |   5 +-
 tests/unit/test_ticket_store.py                    |  44 +-
 tests/unit/test_unity_batchmode.py                 | 194 ++++
 tests/unit/test_xref.py                            | 118 +++
 tests/vet_suite/test_capability_registry_unity.py  | 130 +++
 tests/vet_suite/test_capability_scan_csharp.py     |  84 ++
 tests/vet_suite/test_capability_scan_dotnet_bcl.py | 119 +++
 tickets/T-1661/ticket.md                           |  23 +-
 tickets/T-1778/ticket.md                           |  17 +-
 tickets/T-1820/ticket.md                           |  17 +-
 tickets/T-1831/ticket.md                           |  17 +-
 tickets/T-2451/ticket.md                           |  17 +-
 tickets/T-2752/ticket.md                           |  17 +-
 tickets/T-2803/ticket.md                           |  17 +-
 tickets/T-2835/ticket.md                           |  17 +-
 tickets/T-2837/ticket.md                           |  17 +-
 tickets/T-2856/ticket.md                           |  17 +-
 tickets/T-2886/ticket.md                           |  17 +-
 tickets/T-2889/ticket.md                           |  23 +-
 tickets/T-2939/ticket.md                           |  17 +-
 tickets/T-2962/ticket.md                           |  17 +-
 tickets/T-2965/done-report.md                      | 149 ++++
 tickets/T-2965/ticket.md                           |  41 +-
 tickets/T-2994/ticket.md                           |  16 +-
 tickets/T-3020/done-report.md                      | 578 ++++++++++++
 tickets/T-3020/ticket.md                           |  50 +-
 tickets/T-3022/ticket.md                           |  16 +-
 tickets/T-3032/ticket.md                           |  83 +-
 tickets/T-3053/ticket.md                           |  32 +-
 tickets/T-3063/ticket.md                           |  17 +-
 tickets/T-3067/ticket.md                           |  17 +-
 tickets/T-3082/ticket.md                           |  63 +-
 tickets/T-3083/ticket.md                           |  17 +-
 tickets/T-3102/ticket.md                           |  17 +-
 tickets/T-3127/ticket.md                           |  17 +-
 tickets/T-3193/ticket.md                           |  17 +-
 tickets/T-3213/ticket.md                           |  17 +-
 tickets/T-3221/ticket.md                           |  17 +-
 tickets/T-3229/ticket.md                           |  17 +-
 tickets/T-3232/done-report.md                      | 179 ++++
 tickets/T-3232/ticket.md                           |  88 +-
 tickets/T-3233/done-report.md                      | 606 +++++++++++++
 tickets/T-3233/ticket.md                           |  62 +-
 tickets/T-3241/ticket.md                           |  17 +-
 tickets/T-3259/ticket.md                           |  24 +-
 tickets/T-3262/ticket.md                           |  17 +-
 tickets/T-3270/ticket.md                           |  17 +-
 tickets/T-3274/ticket.md                           |  16 +-
 tickets/T-3327/ticket.md                           |  17 +-
 tickets/T-3330/ticket.md                           |  17 +-
 tickets/T-3335/ticket.md                           |  17 +-
 tickets/T-3351/ticket.md                           |  17 +-
 tickets/T-3357/ticket.md                           |  17 +-
 tickets/T-3359/ticket.md                           |  17 +-
 tickets/T-3377/ticket.md                           |  17 +-
 tickets/T-3412/ticket.md                           |  34 +-
 tickets/T-3415/ticket.md                           |  17 +-
 tickets/T-3459/ticket.md                           |  17 +-
 tickets/T-3504/ticket.md                           |  17 +-
 tickets/T-3505/ticket.md                           |  16 +-
 tickets/T-3513/ticket.md                           |  17 +-
 tickets/T-3559/ticket.md                           |  17 +-
 tickets/T-3564/ticket.md                           |  17 +-
 tickets/T-3602/ticket.md                           |  16 +-
 tickets/T-3611/ticket.md                           |   8 +-
 tickets/T-3612/done-report.md                      | 221 +++++
 tickets/T-3612/ticket.md                           | 156 +++-
 tickets/T-3613/done-report.md                      | 106 +++
 tickets/T-3613/ticket.md                           | 212 ++++-
 tickets/T-3614/ticket.md                           | 111 ++-
 tickets/T-3615/done-report.md                      |  33 +
 tickets/T-3615/ticket.md                           |  30 +-
 tickets/T-3620/ticket.md                           |  16 +-
 tickets/T-3646/ticket.md                           |  17 +-
 tickets/T-3659/ticket.md                           |  16 +-
 tickets/T-3660/ticket.md                           |  17 +-
 tickets/T-3677/ticket.md                           |  17 +-
 tickets/T-3714/ticket.md                           |  17 +-
 tickets/T-3716/ticket.md                           |  17 +-
 tickets/T-3728/ticket.md                           |  17 +-
 tickets/T-3729/ticket.md                           |  17 +-
 tickets/T-3739/ticket.md                           |  17 +-
 tickets/T-3758/ticket.md                           |  17 +-
 tickets/T-3783/ticket.md                           |  16 +-
 tickets/T-3789/ticket.md                           |  17 +-
 tickets/T-3802/ticket.md                           |  27 +-
 tickets/T-3811/ticket.md                           |  16 +-
 tickets/T-3821/ticket.md                           |  46 +-
 tickets/T-3822/ticket.md                           |  45 +-
 tickets/T-3823/ticket.md                           |  45 +-
 tickets/T-3825/ticket.md                           |  49 +-
 tickets/T-3832/ticket.md                           |  44 +-
 tickets/T-3833/ticket.md                           |  44 +-
 tickets/T-3850/ticket.md                           |  17 +-
 tickets/T-3851/ticket.md                           |  26 +
 tickets/T-3854/ticket.md                           |  21 +-
 tickets/T-3856/done-report.md                      | 247 ++++++
 tickets/T-3856/ticket.md                           |  60 +-
 tickets/T-3859/ticket.md                           |  17 +-
 tickets/T-3867/ticket.md                           |  17 +-
 tickets/T-3882/ticket.md                           |  17 +-
 tickets/T-3883/ticket.md                           |  17 +-
 tickets/T-3896/ticket.md                           |  17 +-
 tickets/T-3899/ticket.md                           |  26 +
 tickets/T-3904/ticket.md                           |  17 +-
 tickets/T-3917/ticket.md                           |  17 +-
 tickets/T-3918/ticket.md                           |  16 +-
 tickets/T-3919/ticket.md                           |  17 +-
 tickets/T-3920/ticket.md                           |  87 +-
 tickets/T-3923/ticket.md                           |  17 +-
 tickets/T-3927/ticket.md                           |  21 +-
 tickets/T-3929/ticket.md                           |  22 +-
 tickets/T-3943/done-report.md                      | 626 +++++++++++++
 tickets/T-3943/ticket.md                           |  49 +-
 tickets/T-3953/ticket.md                           |   9 +-
 tickets/T-3961/done-report.md                      | 701 +++++++++++++++
 tickets/T-3961/ticket.md                           |  47 +-
 tickets/T-3962/ticket.md                           |  21 +-
 tickets/T-3964/ticket.md                           |  22 +-
 tickets/T-3986/ticket.md                           |   2 +-
 tickets/T-3995/ticket.md                           |  19 +-
 tickets/T-3997/ticket.md                           |  25 +-
 tickets/T-4010/ticket.md                           |  17 +-
 tickets/T-4011/ticket.md                           |  16 +-
 tickets/T-4019/ticket.md                           |  11 +-
 tickets/T-4029/ticket.md                           |  16 +-
 tickets/T-4035/ticket.md                           |   2 +
 tickets/T-4073/ticket.md                           |  12 +-
 tickets/T-4111/done-report.md                      | 726 +++++++++++++++
 tickets/T-4111/ticket.md                           |  29 +-
 tickets/T-4112/ticket.md                           |  57 +-
 tickets/T-4113/ticket.md                           |  58 +-
 tickets/T-4114/ticket.md                           |  10 +-
 tickets/T-4115/ticket.md                           |  10 +-
 tickets/T-4116/done-report.md                      | 707 +++++++++++++++
 tickets/T-4116/ticket.md                           |  17 +-
 tickets/T-4118/ticket.md                           |  30 +-
 tickets/T-4127/ticket.md                           |  55 +-
 tickets/T-4185/ticket.md                           |   7 +-
 tickets/T-4186/ticket.md                           |   7 +-
 tickets/T-4212/ticket.md                           |  16 +-
 tickets/T-4214/done-report.md                      | 667 ++++++++++++++
 tickets/T-4214/ticket.md                           |  46 +-
 tickets/T-4221/done-report.md                      | 706 +++++++++++++++
 tickets/T-4221/ticket.md                           |  92 +-
 tickets/T-4230/done-report.md                      | 723 +++++++++++++++
 tickets/T-4230/ticket.md                           |  15 +-
 tickets/T-4240/ticket.md                           |   2 +-
 tickets/T-4254/ticket.md                           |  10 +-
 tickets/T-4365/ticket.md                           |   6 +-
 tickets/T-4392/ticket.md                           |  11 +-
 tickets/T-4413/done-report.md                      |  71 ++
 tickets/T-4413/ticket.md                           |  75 +-
 tickets/T-4414/done-report.md                      |  21 +
 tickets/T-4414/ticket.md                           |  23 +-
 tickets/T-4415/done-report.md                      |  25 +
 tickets/T-4415/ticket.md                           |  24 +-
 tickets/T-4416/ticket.md                           |  56 +-
 tickets/T-4418/ticket.md                           |  17 +-
 tickets/T-4419/ticket.md                           | 242 ++++-
 tickets/T-4420/ticket.md                           | 382 +++++++-
 tickets/T-4421/ticket.md                           | 483 +++++++++-
 tickets/T-4422/ticket.md                           |  17 +-
 tickets/T-4423/ticket.md                           |  17 +-
 tickets/T-4437/ticket.md                           |  17 +-
 tickets/T-4438/ticket.md                           |   7 +-
 tickets/T-4447/ticket.md                           |  11 +-
 tickets/T-4469/ticket.md                           |   7 +-
 tickets/T-4471/ticket.md                           |   7 +-
 tickets/T-4491/done-report.md                      |  23 +
 tickets/T-4491/ticket.md                           |  69 ++
 tickets/T-4492/done-report.md                      |  34 +
 tickets/T-4492/ticket.md                           |  67 ++
 tickets/T-4493/done-report.md                      |  19 +
 tickets/T-4493/ticket.md                           |  61 ++
 tickets/T-4494/done-report.md                      | 138 +++
 tickets/T-4494/ticket.md                           |  73 ++
 tickets/T-4495/done-report.md                      | 197 +++++
 tickets/T-4495/ticket.md                           |  64 ++
 tickets/T-4496/done-report.md                      |  23 +
 tickets/T-4496/ticket.md                           |  56 ++
 tickets/T-4497/ticket.md                           |  31 +
 tickets/T-4498/done-report.md                      | 147 ++++
 tickets/T-4498/ticket.md                           |  55 ++
 tickets/T-4499/ticket.md                           |  52 ++
 tickets/T-4500/ticket.md                           |  41 +
 tickets/T-4501/done-report.md                      |  24 +
 tickets/T-4501/ticket.md                           |  81 ++
 tickets/T-4502/done-report.md                      |  19 +
 tickets/T-4502/ticket.md                           |  73 ++
 tickets/T-4503/done-report.md                      | 592 +++++++++++++
 tickets/T-4503/ticket.md                           |  94 ++
 tickets/T-4504/ticket.md                           |  69 ++
 tickets/T-4505/ticket.md                           |  38 +
 tickets/T-4506/ticket.md                           |  40 +
 tickets/T-4507/done-report.md                      | 793 +++++++++++++++++
 tickets/T-4507/ticket.md                           |  57 ++
 tickets/T-4508/done-report.md                      | 689 +++++++++++++++
 tickets/T-4508/ticket.md                           | 114 +++
 tickets/T-4509/ticket.md                           |  48 +
 tickets/T-4510/done-report.md                      | 149 ++++
 tickets/T-4510/ticket.md                           |  81 ++
 tickets/T-4511/done-report.md                      |  97 ++
 tickets/T-4511/ticket.md                           | 103 +++
 tickets/T-4512/done-report.md                      | 524 +++++++++++
 tickets/T-4512/ticket.md                           | 102 +++
 tickets/T-4513/ticket.md                           |  36 +
 tickets/T-4514/done-report.md                      | 179 ++++
 tickets/T-4514/ticket.md                           |  66 ++
 tickets/T-4515/done-report.md                      |  24 +
 tickets/T-4515/ticket.md                           |  62 ++
 tickets/T-4516/ticket.md                           |  32 +
 tickets/T-4517/done-report.md                      | 180 ++++
 tickets/T-4517/ticket.md                           |  94 ++
 tickets/T-4518/ticket.md                           |  34 +
 tickets/T-4519/done-report.md                      | 869 ++++++++++++++++++
 tickets/T-4519/ticket.md                           |  79 ++
 tickets/T-4520/done-report.md                      | 163 ++++
 tickets/T-4520/ticket.md                           |  58 ++
 tickets/T-4521/done-report.md                      | 228 +++++
 tickets/T-4521/ticket.md                           | 125 +++
 tickets/T-4522/done-report.md                      |  99 +++
 tickets/T-4522/ticket.md                           |  49 ++
 tickets/T-4523/done-report.md                      | 104 +++
 tickets/T-4523/ticket.md                           |  40 +
 tickets/T-4524/done-report.md                      | 209 +++++
 tickets/T-4524/ticket.md                           |  52 ++
 tickets/T-4526/ticket.md                           |  45 +
 tickets/T-4529/ticket.md                           |  76 ++
 tickets/T-4530/ticket.md                           |  64 ++
 tickets/T-4531/done-report.md                      |  21 +
 tickets/T-4531/ticket.md                           | 110 +++
 tickets/T-4532/done-report.md                      |  24 +
 tickets/T-4532/ticket.md                           |  66 ++
 tickets/T-4533/ticket.md                           |  35 +
 tickets/T-4534/ticket.md                           |  69 ++
 tickets/T-4535/done-report.md                      |  64 ++
 tickets/T-4535/ticket.md                           |  61 ++
 tickets/T-4536/done-report.md                      |  78 ++
 tickets/T-4536/ticket.md                           | 128 +++
 tickets/T-4537/ticket.md                           |  33 +
 tickets/T-4538/ticket.md                           |  63 ++
 tickets/T-4539/ticket.md                           |  29 +
 tickets/T-4540/done-report.md                      | 543 ++++++++++++
 tickets/T-4540/ticket.md                           |  55 ++
 tickets/T-4541/ticket.md                           | 112 +++
 tickets/T-4542/ticket.md                           |  58 ++
 tickets/T-4543/done-report.md                      | 115 +++
 tickets/T-4543/ticket.md                           |  79 ++
 tickets/T-4546/ticket.md                           |  84 ++
 tickets/T-4547/done-report.md                      | 137 +++
 tickets/T-4547/ticket.md                           |  45 +
 tickets/T-4548/done-report.md                      |  59 ++
 tickets/T-4548/ticket.md                           |  50 ++
 tickets/T-4549/ticket.md                           |  53 ++
 tickets/T-4550/done-report.md                      | 545 ++++++++++++
 tickets/T-4550/ticket.md                           |  59 ++
 tickets/T-4552/done-report.md                      | 146 ++++
 tickets/T-4552/ticket.md                           | 100 +++
 tickets/T-4553/done-report.md                      | 501 +++++++++++
 tickets/T-4553/ticket.md                           |  55 ++
 tickets/T-4554/done-report.md                      | 541 ++++++++++++
 tickets/T-4554/ticket.md                           |  63 ++
 tickets/T-4555/done-report.md                      | 556 ++++++++++++
 tickets/T-4555/ticket.md                           |  78 ++
 tickets/T-4556/done-report.md                      | 602 +++++++++++++
 tickets/T-4556/ticket.md                           |  46 +
 tickets/T-4558/ticket.md                           |  30 +
 tickets/T-4559/ticket.md                           |  57 ++
 tickets/T-4560/ticket.md                           |  41 +
 tickets/T-4561/ticket.md                           |  38 +
 tickets/T-4562/done-report.md                      | 665 ++++++++++++++
 tickets/T-4562/ticket.md                           |  54 ++
 tickets/T-4563/done-report.md                      | 556 ++++++++++++
 tickets/T-4563/ticket.md                           |  47 +
 tickets/T-4566/ticket.md                           | 157 ++++
 tickets/T-4567/ticket.md                           |  27 +
 tickets/T-4571/ticket.md                           |  43 +
 tickets/T-4572/done-report.md                      | 972 +++++++++++++++++++++
 tickets/T-4572/ticket.md                           |  73 ++
 tickets/T-4573/ticket.md                           |  27 +
 tickets/T-4574/ticket.md                           |  29 +
 tickets/T-4575/ticket.md                           |  38 +
 tickets/T-4578/ticket.md                           |  52 ++
 tickets/T-4579/done-report.md                      | 522 +++++++++++
 tickets/T-4579/ticket.md                           |  68 ++
 tickets/T-4580/ticket.md                           |  47 +
 tickets/T-4581/ticket.md                           |  47 +
 tickets/T-4582/done-report.md                      | 551 ++++++++++++
 tickets/T-4582/ticket.md                           |  56 ++
 tickets/T-4583/done-report.md                      | 620 +++++++++++++
 tickets/T-4583/ticket.md                           |  87 ++
 tickets/T-4588/done-report.md                      | 715 +++++++++++++++
 tickets/T-4588/ticket.md                           |  67 ++
 tickets/T-4589/ticket.md                           |  56 ++
 tickets/T-4596/done-report.md                      | 640 ++++++++++++++
 tickets/T-4596/ticket.md                           |  43 +
 tickets/T-4597/ticket.md                           |  34 +
 tickets/T-4598/ticket.md                           |  46 +
 tickets/T-4599/ticket.md                           |  69 ++
 tickets/T-4600/ticket.md                           |  28 +
 tickets/T-4601/ticket.md                           |  27 +
 tickets/T-4602/ticket.md                           |  44 +
 tickets/T-4603/ticket.md                           |  30 +
 tickets/T-4605/ticket.md                           |  82 ++
 tickets/T-4606/ticket.md                           |  27 +
 tickets/T-4607/done-report.md                      | 803 +++++++++++++++++
 tickets/T-4607/ticket.md                           |  81 ++
 tickets/T-4608/ticket.md                           |  41 +
 tickets/T-4609/ticket.md                           |  27 +
 tickets/T-4610/ticket.md                           |  28 +
 tickets/T-4611/ticket.md                           |  28 +
 tickets/T-4612/ticket.md                           | 116 +++
 tickets/T-4615/ticket.md                           | 107 +++
 tickets/T-4616/ticket.md                           |  43 +
 tickets/T-4617/ticket.md                           |  27 +
 tickets/T-4618/ticket.md                           |  52 ++
 tickets/T-4619/ticket.md                           |  64 ++
 tickets/T-4620/ticket.md                           |  52 ++
 tickets/T-4622/ticket.md                           | 107 +++
 tickets/T-4623/ticket.md                           |  64 ++
 tickets/T-4624/ticket.md                           |  52 ++
 tickets/T-4625/ticket.md                           |  43 +
 tickets/T-4626/ticket.md                           |  27 +
 tickets/T-4627/ticket.md                           |  52 ++
 tickets/T-4628/ticket.md                           |  53 ++
 tickets/T-4629/ticket.md                           |  46 +
 tickets/T-4630/ticket.md                           |  54 ++
 tickets/T-4631/ticket.md                           |  71 ++
 tickets/T-4632/ticket.md                           |  41 +
 tickets/T-4633/done-report.md                      | 743 ++++++++++++++++
 tickets/T-4633/ticket.md                           |  86 ++
 tickets/T-4634/done-report.md                      | 851 ++++++++++++++++++
 tickets/T-4634/ticket.md                           |  54 ++
 tickets/T-4635/ticket.md                           |  30 +
 tickets/T-4640/ticket.md                           |  30 +
 tickets/T-4641/ticket.md                           |  29 +
 tickets/T-4642/done-report.md                      | 671 ++++++++++++++
 tickets/T-4642/ticket.md                           |  52 ++
 tickets/T-4643/ticket.md                           |  29 +
 tickets/T-4644/ticket.md                           |  29 +
 tickets/T-4645/ticket.md                           |  59 ++
 tickets/T-4646/done-report.md                      | 914 +++++++++++++++++++
 tickets/T-4646/ticket.md                           |  43 +
 tickets/T-4647/ticket.md                           |  49 ++
 tickets/T-4648/ticket.md                           |  28 +
 tickets/T-4649/done-report.md                      | 888 +++++++++++++++++++
 tickets/T-4649/ticket.md                           | 105 +++
 tickets/T-4650/done-report.md                      | 961 ++++++++++++++++++++
 tickets/T-4650/ticket.md                           | 166 ++++
 tickets/T-4651/ticket.md                           |  55 ++
 tickets/T-4652/ticket.md                           |  46 +
 tickets/T-4653/ticket.md                           |  44 +
 tickets/T-4654/ticket.md                           |  48 +
 tickets/T-4655/ticket.md                           |  43 +
 tickets/T-4656/ticket.md                           |  47 +
 tickets/T-4657/ticket.md                           |  74 ++
 tickets/T-4658/ticket.md                           |  65 ++
 tickets/T-4659/done-report.md                      | 962 ++++++++++++++++++++
 tickets/T-4659/ticket.md                           |  92 ++
 tickets/T-4660/ticket.md                           |  60 ++
 tickets/T-4661/ticket.md                           |  66 ++
 tickets/T-4662/ticket.md                           |  85 ++
 tickets/T-4663/ticket.md                           |  88 ++
 tickets/T-4664/ticket.md                           |  68 ++
 tickets/T-4665/ticket.md                           |  69 ++
 tickets/T-4666/ticket.md                           |  72 ++
 tickets/T-4667/ticket.md                           |  63 ++
 tickets/T-4668/ticket.md                           | 146 ++++
 tickets/T-4669/ticket.md                           |  89 ++
 tickets/T-4670/ticket.md                           |  86 ++
 tickets/T-4671/ticket.md                           | 105 +++
 tickets/T-4672/ticket.md                           | 139 +++
 tickets/T-4673/ticket.md                           |  83 ++
 tickets/T-4674/ticket.md                           |  90 ++
 tickets/T-4675/ticket.md                           | 104 +++
 tickets/T-4676/ticket.md                           |  91 ++
 tickets/T-4677/done-report.md                      |  40 +
 tickets/T-4677/ticket.md                           | 173 ++++
 tickets/T-4678/ticket.md                           | 110 +++
 tickets/T-4679/ticket.md                           |  29 +
 tickets/T-4680/done-report.md                      |  55 ++
 tickets/T-4680/ticket.md                           | 211 +++++
 tickets/T-4681/ticket.md                           |  96 ++
 tickets/T-4684/ticket.md                           |  65 ++
 tickets/T-4685/ticket.md                           |  52 ++
 tickets/T-4686/ticket.md                           |  33 +
 tickets/T-4687/ticket.md                           | 207 +++++
 tickets/T-4688/ticket.md                           | 149 ++++
 tickets/T-4689/ticket.md                           | 114 +++
 tickets/T-4690/ticket.md                           | 200 +++++
 tickets/T-4691/ticket.md                           |  88 ++
 tickets/T-4692/ticket.md                           | 195 +++++
 tickets/T-4693/ticket.md                           | 131 +++
 tickets/T-4694/ticket.md                           |  94 ++
 tickets/T-4695/ticket.md                           | 168 ++++
 tickets/T-4696/ticket.md                           | 149 ++++
 tickets/T-4697/ticket.md                           |  93 ++
 tickets/T-4698/ticket.md                           | 152 ++++
 tickets/T-4702/ticket.md                           |  97 ++
 tickets/T-4703/ticket.md                           | 115 +++
 tickets/T-4709/ticket.md                           | 158 ++++
 tickets/T-4710/ticket.md                           | 109 +++
 tickets/T-4711/ticket.md                           |  73 ++
 tickets/T-4712/ticket.md                           |  71 ++
 tickets/T-4713/ticket.md                           |  83 ++
 tickets/T-4714/ticket.md                           |  79 ++
 tickets/T-4715/ticket.md                           | 159 ++++
 tickets/T-4716/ticket.md                           |  41 +
 tickets/T-4717/ticket.md                           |  75 ++
 tickets/T-4718/ticket.md                           | 156 ++++
 tickets/T-4719/ticket.md                           | 163 ++++
 tickets/T-4720/ticket.md                           |  29 +
 tickets/T-4721/ticket.md                           |  29 +
 tickets/T-4722/ticket.md                           | 155 ++++
 tickets/T-4723/ticket.md                           | 159 ++++
 tickets/T-4724/ticket.md                           |  29 +
 tickets/T-4735/ticket.md                           |  62 ++
 tickets/T-4736/ticket.md                           |  63 ++
 tickets/T-4737/ticket.md                           | 113 +++
 tickets/T-4738/ticket.md                           |  62 ++
 tickets/T-4739/ticket.md                           |  58 ++
 tickets/T-4740/ticket.md                           |  60 ++
 tickets/T-4741/ticket.md                           | 172 ++++
 tickets/T-4742/ticket.md                           |  72 ++
 tickets/T-4743/ticket.md                           |  73 ++
 tickets/T-4757/ticket.md                           |  79 ++
 tickets/T-4758/ticket.md                           |  87 ++
 tickets/T-4759/ticket.md                           |  95 ++
 tickets/T-4760/ticket.md                           |  93 ++
 tickets/T-4761/ticket.md                           | 106 +++
 tickets/T-4762/ticket.md                           |  62 ++
 tickets/T-4763/ticket.md                           |  64 ++
 tickets/T-4764/ticket.md                           |  78 ++
 tickets/T-4765/ticket.md                           | 101 +++
 tickets/T-4766/ticket.md                           |  77 ++
 tickets/T-4767/ticket.md                           | 159 ++++
 tickets/T-4768/ticket.md                           |  77 ++
 tickets/T-4769/ticket.md                           |  67 ++
 tickets/T-4770/ticket.md                           | 157 ++++
 tickets/T-4771/ticket.md                           |  70 ++
 tickets/T-4772/ticket.md                           |  87 ++
 tickets/T-4773/ticket.md                           | 102 +++
 tickets/T-4774/ticket.md                           |  75 ++
 tickets/T-4804/ticket.md                           | 121 +++
 tickets/T-4805/ticket.md                           | 114 +++
 tickets/T-4998/ticket.md                 | 112 +++
 tickets/T-4999/ticket.md                 | 149 ++++
 tickets/T-5000/ticket.md                 |  87 ++
 tickets/T-5002/ticket.md                 |  92 ++
 tickets/T-draft-1f0f55cb/ticket.md                 |  65 ++
 tickets/T-5003/ticket.md                 |  77 ++
 tickets/T-5004/ticket.md                 | 116 +++
 tickets/T-5128/ticket.md                 |  29 +
 tickets/T-5006/ticket.md                 |  34 +
 tickets/T-draft-36c347fe/ticket.md                 |  68 ++
 tickets/T-5007/ticket.md                 |  31 +
 tickets/T-5008/ticket.md                 |  77 ++
 tickets/T-5009/ticket.md                 |  53 ++
 tickets/T-5010/ticket.md                 |  77 ++
 tickets/T-5011/ticket.md                 |  78 ++
 tickets/T-5013/ticket.md                 |  77 ++
 tickets/T-5014/ticket.md                 |  36 +
 tickets/T-5015/ticket.md                 |  45 +
 tickets/T-5016/ticket.md                 |  35 +
 tickets/T-5017/ticket.md                 |  38 +
 tickets/T-5018/ticket.md                 |  67 ++
 tickets/T-5019/ticket.md                 |  77 ++
 tickets/T-5020/ticket.md                 |  52 ++
 tickets/T-5021/ticket.md                 |  70 ++
 tickets/T-5022/ticket.md                 |  30 +
 tickets/T-5025/ticket.md                 |  77 ++
 tickets/T-draft-d7180dc1/ticket.md                 |  75 ++
 tickets/T-5026/ticket.md                 |  77 ++
 tickets/T-5027/ticket.md                 |  77 ++
 tickets/T-5028/ticket.md                 |  78 ++
 tickets/T-5029/ticket.md                 |  43 +
 tickets/T-5030/ticket.md                 |  61 ++
 tickets/T-5031/ticket.md                 |  77 ++
 tickets/T-5032/ticket.md                 |  66 ++
 tickets/archive/T-0090/ticket.md                   |  18 +
 tickets/archive/T-0240/ticket.md                   |  18 +
 tickets/archive/T-0292/ticket.md                   |  18 +
 tickets/archive/T-0336/ticket.md                   |  18 +
 tickets/archive/T-0364/ticket.md                   |  24 +
 tickets/archive/T-0403/ticket.md                   |  18 +
 tickets/archive/T-0470/ticket.md                   |  17 +
 tickets/archive/T-0525/ticket.md                   |  18 +
 tickets/archive/T-0553/ticket.md                   |  18 +
 tickets/archive/T-0557/ticket.md                   |  18 +
 tickets/archive/T-0730/ticket.md                   |  18 +
 tickets/archive/T-0814/ticket.md                   |  26 +
 tickets/archive/T-1148/ticket.md                   |  18 +
 tickets/archive/T-1265/ticket.md                   |  18 +
 tickets/archive/T-1266/ticket.md                   |  18 +
 tickets/archive/T-1402/ticket.md                   |  18 +
 tickets/archive/T-1421/ticket.md                   |  31 +-
 tickets/archive/T-1651/ticket.md                   |  11 +-
 tickets/archive/T-1746/ticket.md                   |  94 +-
 tickets/archive/T-1748/ticket.md                   |  36 +
 tickets/archive/T-2314/ticket.md                   |   9 +
 tickets/archive/T-2338/ticket.md                   |   9 +
 tickets/archive/T-2438/ticket.md                   |   9 +
 tickets/archive/T-2454/ticket.md                   |   9 +
 tickets/archive/T-2688/ticket.md                   |   9 +
 tickets/archive/T-2710/ticket.md                   |   9 +
 tickets/archive/T-3128/ticket.md                   |  28 +
 tickets/archive/T-3255/ticket.md                   |   9 +
 tickets/archive/T-3664/ticket.md                   |  11 +-
 tickets/archive/T-3665/ticket.md                   |  10 +-
 tickets/archive/T-3667/ticket.md                   |  11 +-
 uv.lock                                            |   2 +-
 820 files changed, 76315 insertions(+), 2274 deletions(-)
```

### Evidence
- `tests/unit/test_telemetry_verb_recording.py::TestAppDispatchRecordsSubverb::test_ticket_show_records_verb_ticket_subverb_show` (pytest node id, verified passing when recorded)
- `tests/unit/test_telemetry_verb_recording.py::TestHookParsesFrobVerbFromBash::test_uv_run_frob` (pytest node id, verified passing when recorded)
- `tests/unit/test_telemetry_verb_recording.py::TestHookParsesFrobVerbFromBash::test_dot_venv_bin_frob` (pytest node id, verified passing when recorded)
- `tests/unit/test_telemetry_verb_recording.py::TestHookParsesFrobVerbFromBash::test_python_dash_m_frob` (pytest node id, verified passing when recorded)
- `tests/unit/test_telemetry_verb_recording.py::TestHookParsesFrobVerbFromBash::test_nice_wrapped_frob` (pytest node id, verified passing when recorded)
- `tests/unit/test_telemetry_verb_recording.py::TestHookParsesFrobVerbFromBash::test_compound_command_several_frob_calls` (pytest node id, verified passing when recorded)
- `tests/unit/test_telemetry_verb_recording.py::TestHookParsesFrobVerbFromBash::test_non_frob_bash_command_records_neither` (pytest node id, verified passing when recorded)
