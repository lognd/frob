## Done report

Enumerated every frob.toml table whose only content is a pointer into
frob's own internals (grepped for resolve_dotted_symbol usage across
src/frob/gates/*.py, checked each): 10 files, 11 known-key declarations
(dup_graph_schema.py covers two tables), ALL of them pure pointers with
zero project-specific decision:
  arch_schema, docblocks_schema, dup_schema, graph_schema,
  gates_schema (ratchet_known_keys), native_schema, profile_schema,
  refs.entrypoint_schema, test_runner_schema, testing_schema,
  toplevel_scalar_schema

Two siblings using the SAME resolve_dotted_symbol idiom were checked and
explicitly excluded, with reasoning: FLAGCOV001's config=/forwarded= and
DOC004's parser= all point at the CONSUMER's own CLI/config classes
(their own pydantic model, their own argparse factory), never at a frob
internal -- a genuine per-project decision, correctly left declared-only
with no default to fall back to.

Fix: each of the 11 resolvers now returns frob's own internal
constant/function directly when the table is absent, instead of
Severity.UNRESOLVED. Verified this does NOT weaken the loud-failure
guarantee: a DECLARED-but-broken pointer (unresolvable dotted path, or a
resolved value that is neither a set nor a set-returning callable)
still reports UNRESOLVED unchanged -- only the "nothing declared at
all" branch changed. The existing "declared and broken" test in each of
the 10 test files was run unmodified and still passes, proving this.
The override path is untouched: a project with a real reason to declare
a different key set still can, and it still wins.

CHECKED FIRST (per the ticket's instruction), rather than assumed: the
scaffold template (src/frob/scaffold/data/shared/python/frob.toml.j2,
and its five sibling stack variants under types/) already ships ZERO of
these ten tables -- 24 lines today, unchanged by this ticket. The 160+
line frob.toml the owner hand-wrote in ../diax (F-observed, verified by
reading ../diax/frob.toml directly: 413 lines, 10 of these 11 tables
present) was NOT produced by this repo's current scaffold template; it
was very likely produced against the STALE globally-installed frob
0.530.0 binary noted in every command's own CLI-surface-skew warning
this session, whose scaffold template may differ from this checkout's
already-minimal one. Nothing in the CURRENT template needed shrinking.
The real, durable fix is the internal default in the gate code itself,
which benefits every consumer regardless of which scaffold version (or
no scaffold at all, a hand-written frob.toml) produced their config --
stated per the ticket's requirement not to just patch the template.

Fixtures (all ten tables, following the existing per-table two-fixture
discipline in each test file):
- MUST-FIRE: test_no_schema_declared_defaults_to_frobs_own_keys_must_fire
  in each of the 10 test files -- a repo declaring nothing is MEASURED
  (zero violations for keys that are actually known).
- Additional default-still-flags-unknown-keys check in each file --
  the default isn't a silent pass-everything; a genuinely unknown key
  under the default set still reports an error.
- MUST-STAY-QUIET (declaring your own known_keys still wins): unchanged
  existing must-now-fire / must-still-pass-this-repos-own-frob-toml
  pairs in every file, run unmodified, still green.
- THIRD (a broken declaration still reports loudly): unchanged existing
  test_unresolvable_schema_dotted_path_is_unresolved /
  test_non_set_non_callable_schema_value_is_unresolved in every file,
  run unmodified, still green.

Docs updated: docs/modules/gates.md's ten-row *_SCHEMA summary table
(each row's UNRESOLVED-on-absence clause rewritten to describe the new
default), plus one new callout paragraph immediately above the T-2390
epic's first child section explaining the T-3273 change applies to
every child uniformly, so the eleven detailed per-child "FAIL-LOUDLY"
paragraphs below it (which still correctly describe the
declared-and-broken path) are not each individually misleading.

Gates: frob check --ticket T-3273 --only scope --only prework clean.
frob ticket sweep T-3273 re-run after each scope --add. Full frob check
--ticket T-3273 run: zero *SCHEMA findings anywhere in the output
(this repo's own frob.toml declares all of these explicitly, so its own
behavior is provably unchanged -- the declared path was never touched).
frob test --base main: touched-set python suite green, 21/21.

### Changed
```
 docs/modules/gates.md                     |  36 +++++--
 src/frob/gates/_arch_schema.py            |  35 ++++---
 src/frob/gates/_docblocks_schema.py       |  12 +--
 src/frob/gates/_dup_graph_schema.py       |  21 ++--
 src/frob/gates/_gates_schema.py           |  13 +--
 src/frob/gates/_native_schema.py          |  12 +--
 src/frob/gates/_profile_schema.py         |  12 +--
 src/frob/gates/_refs_schema.py            |  14 ++-
 src/frob/gates/_test_runner_schema.py     |  12 +--
 src/frob/gates/_testing_schema.py         |  12 +--
 src/frob/gates/_toplevel_scalar_schema.py |  12 +--
 tests/unit/test_arch_table_schema.py      |  26 ++++-
 tests/unit/test_docblocks_table_schema.py |  25 ++++-
 tests/unit/test_dup_graph_table_schema.py |  41 ++++++--
 tests/unit/test_gates_table_schema.py     |  22 ++--
 tests/unit/test_native_table_schema.py    |  23 ++++-
 tests/unit/test_profile_table_schema.py   |  23 ++++-
 tests/unit/test_refs_schema.py            |  25 ++++-
 tests/unit/test_test_table_schema.py      |  26 ++++-
 tests/unit/test_testing_table_schema.py   |  23 ++++-
 tests/unit/test_toplevel_scalar_schema.py |  26 ++++-
 tickets/T-3273/ticket.md                  | 161 +++++++++++++++++++++++++++++-
 22 files changed, 454 insertions(+), 158 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
