## Done report

Changed:
- src/frob/gates/_refs_schema.py (new): REFSCHEMA001 gate --
  refs_schema_gate / _resolve_known_keys / _entrypoint_records /
  _unresolved / _unknown_key_violation, plus this repo's own known-key
  constant REFS_ENTRYPOINT_KNOWN_KEYS
- src/frob/gates/__init__.py: registered refs_schema_gate (import,
  _ALL_GATES, _CANONICAL_GATE_ORDER, dispatch dict, __all__)
- src/frob/gates/_waive.py: added REFSCHEMA001 to _KNOWN_GATE_RULES
- src/frob/check/__init__.py: refs_schema added to _STAGE_GROUPS
  ["gates-fast"] (checked this specifically, per T-2397's own recorded
  lesson: a gate in _ALL_GATES but not a _STAGE_GROUPS member is
  unreachable via --only <group>)
- frob.toml: [refs] entrypoint_schema =
  "frob.gates._refs_schema:REFS_ENTRYPOINT_KNOWN_KEYS" self-declaration
- docs/modules/gates.md: REFSCHEMA001 table row + full prose section +
  frob:enumerates member-list sync
- docs/design/registry/check-coverage.yaml: CHK-GATE-REFSCHEMA001 entry
- tests/unit/test_refs_schema.py (new): 6 tests

T-2390 epic's FIRST child, per coordinator instruction to take the
largest/hardest table first so the pattern the other nine children copy
is established on the hardest case. [[refs.entrypoint]] is this repo's
single largest config table (58 leaf values, 29 entries) and its
array-of-records shape (not a flat scalar table) forced the schema-
declaration idiom to handle both shapes, not just the flat one.

Real defect closed: frob.gates._refs._load_allowlist's own `.get("path")`
/`.get("reason")` reads only ever look at the two names they know -- an
entry with an EXTRA or MISSPELLED key alongside otherwise-valid path/
reason values passes through completely silently (the malformed-entry
warning only fires when path/reason themselves are missing/wrong-typed,
not when a THIRD key is present). refs_schema_gate reads the RAW
[[refs.entrypoint]] records directly (deliberately not through
_load_allowlist's own filtered output) so it can still see the full key
set of an otherwise-valid-looking entry.

PORTABILITY (T-2384): reused T-2397's exact resolve_dotted_symbol idiom
(frob.gates._docblocks_shared) rather than inventing a second resolver
-- [refs] entrypoint_schema = "module:symbol" is portable to any project
without touching this module.

FAIL-LOUDLY (T-2391 via the already-shipped Severity.UNRESOLVED
mechanism, same posture as FLAGCOV001): no entrypoint_schema declared,
an unresolvable dotted path, a non-set/non-callable resolved value, or
missing/unreadable frob.toml itself all report Severity.UNRESOLVED --
4 of the 6 new tests assert this directly.

VERIFIED END TO END: ran refs_schema_gate directly against this repo (0
findings -- must-still-pass control); injected a plausibly misspelled
key ("ptah" alongside valid path/reason) into a temp copy of frob.toml
and confirmed exactly 1 REFSCHEMA001 ERROR fires naming the bad key and
entry index; restored the real file and re-confirmed 0 findings.

Self-review found and fixed real issues before landing (not waived
around): ty invalid-return-type/unsupported-operator (both a cast/assert
narrowing gap, same shape as T-2397's own ty fixes), 2x COV001 (missing
frob:doc on the new public constant and function), DOC002 (my own
frob:doc anchor's slug did not match the actual heading-generated slug
-- fixed by using the real slug, "refschema001-t-2390-epic-child-
t-draft-2654f0be", not the shorter one I first guessed), I001 import
sort, FMT001 (a directive line's trailing `# noqa: E501` defeated frob
fmt's own canonical-wrap detection -- removed the noqa, let frob fmt
wrap it for real), REG010/REG009 (ran frob registry audit
--sync-gate-rules, unlike T-2397's PORT001 courtesy registration this
one IS a fully live, code-enforced rule so the registry entry is
correct and complete, not a placeholder). One EXHAUST003 finding
(ambiguous call-graph resolution around a tomllib.load try/except, same
shape as an existing unflagged sibling function in this same file) is
waived with a reasoned frob:waive citing the sibling comparison, not
dismissed silently.

Epic status: T-2390's own epic-level closure bar (acceptance[2]) is NOT
yet met -- 9 sibling children remain (gates, test, arch, native,
docblocks, testing, profile, dup+graph, top-level scalars). This
child's own acceptance (must-now-fire + must-still-pass for
[[refs.entrypoint]] specifically) is met and landing.

Gates: this ticket's own diff-scoped lint/gates-fast/gates-native runs
are clean of every refs_schema/REFSCHEMA001 finding except the one
reasoned waiver noted above. Remaining errors in an unscoped run are
pre-existing/other agents' in-flight work, none touching a file this
ticket's diff modifies.

### Changed
```
 tickets/T-2428/ticket.md | 57 +++++++++++++++++++++++++++++++++++++-
 1 file changed, 56 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_refs_schema.py::TestRefsSchemaGate::test_must_now_fire_reports_the_undeclared_key` (pytest node id, verified passing when recorded)
- `tests/unit/test_refs_schema.py::TestRefsSchemaGate::test_must_still_pass_this_repos_own_frob_toml` (pytest node id, verified passing when recorded)
- `tests/unit/test_refs_schema.py::TestRefsSchemaGate::test_no_schema_declared_is_unresolved_not_empty` (pytest node id, verified passing when recorded)
- `tests/unit/test_refs_schema.py::TestRefsSchemaGate::test_unresolvable_schema_dotted_path_is_unresolved` (pytest node id, verified passing when recorded)
- `tests/unit/test_refs_schema.py::TestRefsSchemaGate::test_non_set_non_callable_schema_value_is_unresolved` (pytest node id, verified passing when recorded)
- `tests/unit/test_refs_schema.py::TestRefsSchemaGate::test_no_frob_toml_is_unresolved` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@.claude/hooks/root-write-guard.py, ARCH103@src/frob/release/_cli.py, COV001@src/frob/verify/_drain.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, DOC001@docs/commands/release.md, DOC002@src/frob/verify/_drain.py, DOC005@docs/modules/cli.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DOCENUM001@docs/modules/gates.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT002@docs/modules/vet.md, E501@/home/logan/projects/frob/.claude/worktrees/contention-cluster/src/frob/app/ticket_runner/_mutate.py, E501@/home/logan/projects/frob/.claude/worktrees/contention-cluster/src/frob/verify/_worker.py, F401@/home/logan/projects/frob/.claude/worktrees/contention-cluster/src/frob/vet/_capability.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PRE001@tickets/T-2428, RENDER001@src/frob/release/_cli.py, SEC110@.claude/hooks/root-write-guard.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md
