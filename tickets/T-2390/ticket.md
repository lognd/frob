---
id: T-2390
title: 'config-file keys are never validated: an unknown or misspelled frob.toml key
  is silently ignored'
state: done
kind: bug
origin: human
created: '2026-08-18'
priority: high
parent: null
tier: epic
sprint: null
runs_last: false
scope:
- src/frob/app/_config_external.py
evidence_scope:
- tests/unit/test_native_table_schema.py
- tests/unit/test_profile_table_schema.py
- tests/unit/test_toplevel_scalar_schema.py
- tests/unit/test_testing_table_schema.py
- tests/unit/test_arch_table_schema.py
- tests/unit/test_docblocks_table_schema.py
- tests/unit/test_gates_table_schema.py
- tests/unit/test_test_table_schema.py
- tests/unit/test_dup_graph_table_schema.py
- tests/unit/test_refs_schema.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: tier
  old_value: ticket
  new_value: epic
  reason: 'restructured per coordinator instruction: 12-table, ~121-leaf surface with
    ~10 disjoint hand-rolled readers needs a schema-declaration idiom applied per-table,
    each with its own must-fire/must-still-pass fixture -- epic-shaped, not a single
    ticket; the T-2390 investigation (attempt 1''s fail-log) is the design input for
    this decomposition'
  actor: logan
  at: '2026-08-18'
body_changes:
- mode: append
  reason: 'record the epic decomposition: disjoint-readers finding, DupConfig/GateConfig-not-bound-to-raw-tables
    fact, and the 10 filed children'
  actor: logan
  at: '2026-08-18'
  old_length: 4383
  new_length: 9048
- mode: append
  reason: 'BUG002 front door (T-2393): epic rollup ticket with no code of its own
    -- all runtime behavior change happened in the ten already-landed children (T-2428..T-2437),
    each with its own BUG002-satisfying evidence; T-2390 itself only carries the aggregate
    closure-bar evidence (11 must-still-pass tests across all ten schema families)
    proving the union of children meets acceptance[2]'
  actor: logan
  at: '2026-08-18'
  old_length: 19278
  new_length: 19664
- mode: append
  reason: 'BUG002 front door (T-2393): epic rollup ticket with no code of its own
    -- all runtime behavior change happened in the ten already-landed children (T-2428..T-2437),
    each with its own BUG002-satisfying evidence; T-2390 itself only carries the aggregate
    closure-bar evidence (11 must-still-pass tests across all ten schema families)
    proving the union of children meets acceptance[2]'
  actor: logan
  at: '2026-08-18'
  old_length: 19665
  new_length: 20051
evidence:
- tests/unit/test_native_table_schema.py::TestNativeSchemaGate::test_must_still_pass_this_repos_own_frob_toml
- tests/unit/test_profile_table_schema.py::TestProfileSchemaGate::test_must_still_pass_this_repos_own_frob_toml
- tests/unit/test_toplevel_scalar_schema.py::TestTopLevelScalarSchemaGate::test_must_still_pass_this_repos_own_frob_toml
- tests/unit/test_testing_table_schema.py::TestTestingSchemaGate::test_must_still_pass_this_repos_own_frob_toml
- tests/unit/test_arch_table_schema.py::TestArchSchemaGate::test_must_still_pass_this_repos_own_frob_toml
- tests/unit/test_docblocks_table_schema.py::TestDocblocksSchemaGate::test_must_still_pass_this_repos_own_frob_toml
- tests/unit/test_gates_table_schema.py::TestGatesSchemaGate::test_must_still_pass_this_repos_own_frob_toml
- tests/unit/test_test_table_schema.py::TestTestRunnerSchemaGate::test_must_still_pass_this_repos_own_frob_toml
- tests/unit/test_dup_graph_table_schema.py::TestDupGraphSchemaGate::test_dup_must_still_pass_this_repos_own_frob_toml
- tests/unit/test_dup_graph_table_schema.py::TestDupGraphSchemaGate::test_graph_must_still_pass_this_repos_own_frob_toml
- tests/unit/test_refs_schema.py::TestRefsSchemaGate::test_must_still_pass_this_repos_own_frob_toml
- tests/unit/test_gates_table_schema.py::TestGatesSchemaGate::test_must_now_fire_reports_the_undeclared_ratchet_key
- tests/unit/test_gates_table_schema.py::TestGatesSchemaGate::test_no_ratchet_schema_declared_is_unresolved_not_empty
designated_repro_test: null
acceptance:
- text: Given a frob.toml containing a key no declared config schema claims, when
    any frob command loads config, then the unknown key is reported with its file
    and key name, rather than silently ignored.
  evidence:
  - tests/unit/test_gates_table_schema.py::TestGatesSchemaGate::test_must_now_fire_reports_the_undeclared_ratchet_key
- text: Given a project that declares no config surface at all, when the check runs,
    then it reports that no configuration surface is declared and does not report
    a silent zero.
  evidence:
  - tests/unit/test_gates_table_schema.py::TestGatesSchemaGate::test_no_ratchet_schema_declared_is_unresolved_not_empty
- text: 'EPIC CLOSURE BAR (not any single child''s): once every child ticket below
    has landed, this repo''s own frob.toml -- all ~121 leaf values across its 12 top-level
    tables -- reports zero unknown keys under the union of every child''s declared
    schema, proving the check was not calibrated by weakening it. A child''s OWN acceptance
    is its own table''s must-fire/must-still-pass pair (see each child''s body); this
    criterion is the epic-level aggregate, checked only once the last child lands.'
  evidence:
  - tests/unit/test_native_table_schema.py::TestNativeSchemaGate::test_must_still_pass_this_repos_own_frob_toml
  - tests/unit/test_profile_table_schema.py::TestProfileSchemaGate::test_must_still_pass_this_repos_own_frob_toml
  - tests/unit/test_toplevel_scalar_schema.py::TestTopLevelScalarSchemaGate::test_must_still_pass_this_repos_own_frob_toml
  - tests/unit/test_testing_table_schema.py::TestTestingSchemaGate::test_must_still_pass_this_repos_own_frob_toml
  - tests/unit/test_arch_table_schema.py::TestArchSchemaGate::test_must_still_pass_this_repos_own_frob_toml
  - tests/unit/test_docblocks_table_schema.py::TestDocblocksSchemaGate::test_must_still_pass_this_repos_own_frob_toml
  - tests/unit/test_gates_table_schema.py::TestGatesSchemaGate::test_must_still_pass_this_repos_own_frob_toml
  - tests/unit/test_test_table_schema.py::TestTestRunnerSchemaGate::test_must_still_pass_this_repos_own_frob_toml
  - tests/unit/test_dup_graph_table_schema.py::TestDupGraphSchemaGate::test_dup_must_still_pass_this_repos_own_frob_toml
  - tests/unit/test_dup_graph_table_schema.py::TestDupGraphSchemaGate::test_graph_must_still_pass_this_repos_own_frob_toml
  - tests/unit/test_refs_schema.py::TestRefsSchemaGate::test_must_still_pass_this_repos_own_frob_toml
acceptance_amendments:
- op: replace
  index: 2
  old_text: Given this repo's own frob.toml with all 148 leaf values, when the check
    runs, then it reports zero unknown keys, proving the check was not calibrated
    by weakening it.
  new_text: 'EPIC CLOSURE BAR (not any single child''s): once every child ticket below
    has landed, this repo''s own frob.toml -- all ~121 leaf values across its 12 top-level
    tables -- reports zero unknown keys under the union of every child''s declared
    schema, proving the check was not calibrated by weakening it. A child''s OWN acceptance
    is its own table''s must-fire/must-still-pass pair (see each child''s body); this
    criterion is the epic-level aggregate, checked only once the last child lands.'
  reason: 'coordinator instruction: criterion[2]''s all-leaves-zero bar is the EPIC''s
    closure bar, not a single ticket''s -- a partial-coverage child must not be able
    to claim it'
  actor: logan
  at: '2026-08-18'
threat: null
component: config
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED 2026-08-18. frob validates its two input channels to wildly
different standards, and the file channel is the unvalidated one.

    CLI input          unknown flag -> argparse rejects it, and T-0578's
                       suggester even proposes the intended flag
    config-file input  unknown key   -> silently ignored

Evidence:
  - `AppConfig.model_config` is `{}`, so pydantic's default
    `extra="ignore"` applies across all 356 declared fields.
    `AppConfig(subcommand=None, path=".", tiemout_s=999, notakey="xyz")`
    constructs cleanly and drops both bogus keys with no diagnostic.
  - `frob.toml` in this repo carries 148 leaf values across 12 top-level
    tables (arch, check_base, docblocks, dup, gates, graph,
    min_frob_version, native, profile, refs, test, testing).
  - There is NO unknown-key validation anywhere in src/frob. Every
    "unrecognized" hit in the tree concerns CLI arguments, not config
    keys. `_build_external_config_kwargs` iterates the KNOWN field
    tuples (_STRING_FIELDS/_PATH_FIELDS/_INT_FIELDS/_FLOAT_FIELDS/
    _LIST_FIELDS/_BOOL_FLAGS) pulling from the parsed dict, so a key the
    file contains but no tuple names is never read and never reported.

WHY THIS MATTERS MORE THAN A TYPO. A misspelled `max_function_lines` in
[arch] does not fail -- the limit silently reverts to its built-in
default and the gate keeps reporting green while enforcing a threshold
the operator never chose. The config layer's version of
[[catalogued-is-not-enforced]]: the knob is present, documented, and
inert. Every gate whose strictness is configurable is exposed to this,
which makes it a silent correctness hole across the whole enforcement
surface, not a usability wart.

SAME FAMILY AS T-2387 (filed independently today): three T-2320 flags
parse but never reach AppConfig because `_BOOL_FLAGS` was not updated.
Both are "a configured value silently fails to reach its destination".
T-2387 is the CLI half and already has a purpose-built detector
(`find_dropped_cli_flags`, T-2004) whose test is currently RED on main.
This ticket is the FILE half, which has no detector at all.

REQUIRED SHAPE OF THE FIX (portability is a hard requirement -- see
T-2384; a check that only works on frob's own layout is the bug this
repo is currently paying down):
  - Report an unknown key in a config file against the DECLARED schema
    for that file, resolved through a declaration, not through a
    hardcoded reference to AppConfig. Reuse the existing
    `module:symbol` idiom already proven by
    `[[docblocks.commands]] parser = "frob.__main__:_build_parser"`.
  - A project that declares NO config surface must fail LOUDLY
    ("no configuration surface declared"), never report a silent zero.
    Silent-zero-on-unconfigured is precisely the defect class T-2384
    exists to remove; do not reintroduce it here.
  - Setting `extra="forbid"` on AppConfig is NOT sufficient on its own
    and may not even be safe -- verify before doing it. The forwarding
    layer builds kwargs from known tuples, so file keys never become
    model kwargs in the first place; a stricter model would catch
    programmer error at construction sites but not the operator typo in
    frob.toml, which is the actual bug. Fix the file path, and treat
    model strictness as a separate judgement with its own evidence.

Positive control is mandatory: a must-now-fire fixture (a frob.toml
carrying a plausibly-misspelled real key, e.g. `max_fuction_lines`,
which must be reported) AND a must-still-pass control (this repo's real
frob.toml, all 148 leaf values, must report zero once any genuinely
undeclared-but-intentional keys are declared). If the control does not
pass, the finding is that frob.toml has real undeclared keys -- report
them, do not weaken the check to accommodate them.

## Failure log
- 2026-08-18 attempt 1: Scoped, not coded: frob.toml has 12 top-level tables/121 leaves read by ~10 DISJOINT ad hoc per-table readers (load_arch_config, _dup_config, etc), none bound to a pydantic schema today; a faithful fix needs the module:symbol schema-declaration idiom (docblocks.commands precedent) extended across every table plus a must-fire/must-still-pass fixture PER table -- epic-shaped, not a single-pass bug fix. Requeuing rather than forcing partial coverage that would falsely claim the acceptance[2] all-121-leaves-zero-unknown bar.


## Epic decomposition (2026-08-18, restructured per coordinator instruction from attempt 1's fail-log)

FINDING THAT STOPS THE ONE-LINE FIX (write this down so the next person
does not reach for it): frob.toml's ~12 top-level tables / ~121 leaf
values are read by roughly TEN DISJOINT, hand-rolled readers, each its
own function with its own defaults dict or ad hoc tomllib.load()+.get()
chain -- NOT one unified schema. `DupConfig` (src/frob/dup/_models.py)
and `GateConfig`/`TestPolicy` (src/frob/gates/_models.py) are real
pydantic BaseModels, but NONE of them is actually constructed from the
raw frob.toml table today -- each table's own reader manually copies a
handful of named keys into a tuple/dict, so `extra="forbid"` on any of
these models would NOT catch a stray file key: the key is never even
looked at, let alone passed to the model constructor, forbid or not.
This is the actual shape of the bug across the whole file, not just in
[arch]/[dup] (the two tables attempt 1 happened to inspect first).

Readers identified (module::function, leaf count in this repo's own
frob.toml at filing time):
- refs (58 leaves): `frob.gates._refs._load_allowlist`, reads
  `[[refs.entrypoint]]` (array of {path, reason} records)
- gates (19 leaves): `frob.gates._ratchet` (`[gates.ratchet.rules]`) plus
  other [gates]-nested sub-tables; needs its own sub-table inventory
- test (16 leaves): readers spread across `frob.check._native` and
  `frob.gates.__init__`; needs its own inventory pass
- arch (9 leaves): `frob.app._config_meta.load_arch_config` -- hand-lists
  10 named keys against its own calibrated-defaults dict
- native (6 leaves): `[[native]]` array, consumed by
  `frob.natives`/`frob._cli_parsers._misc`/`frob.app.config`
- docblocks (4 leaves): `frob.gates._docblocks_refs._console_command_
  sources` -- NOTE: T-2397 (landed) already extended this reader's own
  `_ConsoleCommandSource` with `config=`/`forwarded=` keys for FLAGCOV001;
  this child's schema-validation work must account for those two NEW
  keys as legitimate, not flag them as unknown
- testing (5 leaves): `TestPolicy` (frob.gates._models, ALREADY a real
  pydantic model) + `frob.gates._sys` -- likely the easiest child, worth
  doing early to prove the pattern generalizes to an already-modeled
  table, not just hand-rolled ones
- profile (2 leaves): `frob.tickets._profile`
- dup (1 leaf currently set): `frob.gates._dup._dup_config`
- graph (1 leaf): `frob.excludes` (`[graph] exclude`)
- min_frob_version / check_base: top-level SCALAR keys, no table at all
  -- read by `frob.app._config_meta`/`frob.app.config` directly; needs
  its own tiny schema declaration, not folded into a table-shaped child

Each child below: same module:symbol schema-declaration idiom (the
`[[docblocks.commands]]`/`_load_parser_factory`/`resolve_dotted_symbol`
precedent, T-1195/T-2397), a must-now-fire fixture (a plausibly
misspelled real key in that table, reported) AND a must-still-pass
control (that table's real keys in THIS repo's frob.toml, zero
findings). If a control fails, the finding is genuinely undeclared keys
in frob.toml -- report them, never weaken the check to accommodate them.
Scope is narrowed to each table's own reader file(s) so several children
can run in parallel (disjoint file scopes, per table).

Taking the largest/hardest child (refs, 58 leaves, array-of-records
shape rather than a flat scalar table) myself first, per coordinator
instruction, to establish the pattern on the hardest case.

Children filed (draft ids, renumber to real ids at land):
- T-2428: [[refs.entrypoint]] (58 leaves) -- TAKEN by this
  session, in progress
- T-2435: [gates] table (incl. [gates.ratchet]) (19 leaves)
- T-2436: [test] table (16 leaves)
- T-2433: [arch] table (9 leaves)
- T-2429: [[native]] table (6 leaves)
- T-2434: [[docblocks.commands]] table (4 leaves, incl.
  T-2397's own new config=/forwarded= keys)
- T-2432: [testing] table (5 leaves, already has a TestPolicy
  pydantic model -- good early pick to test the pattern against an
  already-modeled table)
- T-2430: [profile] table (2 leaves, smallest per-table child)
- T-2437: [dup] + [graph] tables combined (1 leaf each,
  disjoint readers but too small individually to justify separate
  tickets)
- T-2431: top-level scalar keys (min_frob_version, check_base
  -- no enclosing table, structurally different from the rest)

All ten are blocked_by=[] (independent scopes, safe to dispatch in
parallel) except for real overlap on shared infra files a coordinator
should still check before a wave dispatch.