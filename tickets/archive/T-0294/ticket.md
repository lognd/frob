---
id: T-0294
title: 'DSL parser: eliminate 13 malformed-directive false positives (secret-fake
  marker, kinds, trailing prose)'
state: done
kind: bug
origin: agent
created: '2026-07-19'
priority: medium
blocked_by:
- T-0286
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/graph/dsl.py
- src/frob/gates/_secrets.py
- tests/**
- src/frob/fuzz/**
- src/frob/app/perf_runner.py
- docs/modules/graph.md
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: condense narrative into cited ticket body per T-4691 C5 sweep
  actor: logan
  at: '2026-09-19'
  old_length: 1522
  new_length: 4471
evidence:
- tests/unit/graph/test_dsl.py::TestReservedMarkerVerbs::test_secret_fake_is_silently_skipped
- tests/unit/graph/test_dsl.py::TestReservedMarkerVerbs::test_unreserved_unknown_verb_still_reports_malformed
- tests/system/test_cli_check.py::TestCheckTicketScopedAlwaysReportsOnFailure::test_ticket_scoped_nonzero_exit_has_diagnostic_output
- tests/unit/strata/test_selfconform.py::TestExtendedKindsDriftLock::test_extended_kinds_is_disjoint_from_kind_map
- tests/test_dup_rungs.py::TestR6Probing::test_fires_on_equivalent_functions_with_renamed_multi_arg_params
- tests/gates_suite/test_coverage.py::TestCoverageLoad::test_parses_line_to_symbol_span
designated_repro_test: null
acceptance:
- text: given the intentional frob:secret-fake fixture marker (_secrets.py _FAKE_MARKER,
    a deliberately-unregistered literal the secrets gate scans for), when parse_directives
    sees it, then it is recognized as a RESERVED marker and skipped silently -- no
    "unknown verb secret-fake" malformed-directive warning (3 occurrences in test_secrets_gate.py
    cleared)
  evidence: []
- text: given a frob:tests directive with kind=drift or kind=system, when parsed,
    then either the kind is corrected to a valid unit/integration/e2e value in the
    3 real directives (test_selfconform.py x2 drift-lock=unit, test_cli_check.py system=e2e),
    so no invalid-kind warning fires
  evidence: []
- text: 'given the 7 directives with same-line trailing prose (frob:ticket/frob:todo/frob:tests
    followed by -- prose or bare prose: perf_runner.py, fuzz/_arbitrary.py, fuzz/_run.py,
    test_dup_rungs.py x3, test_gates.py), when parsed under the T-0286 continuation/prose-tolerance
    rule, then the prose is accepted (or the directives are split) with no bad-attribute-syntax
    warning'
  evidence: []
- text: given a full frob check, when the graph is built, then the malformed-directive
    warning count from these 13 sources is ZERO
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Investigated 2026-07-19: the 13 "malformed directive" warnings are NOT sloppy comments -- they are a DSL-parser robustness gap in three classes. (1) frob:secret-fake is an INTENTIONAL cross-subsystem literal marker (src/frob/gates/_secrets.py:15,66 -- "unregistered marker, the literal substring frob:secret-fake"); the secrets gate scans for it to discharge a fixture token, but graph/dsl.py::parse_directives treats frob:<anything> as a directive and warns "unknown verb secret-fake". Fix: reserve secret-fake (and audit for any other intentional literal markers) as a known no-op verb the parser skips silently -- the two subsystems must agree on the vocabulary. (2) Three real frob:tests directives use kind=drift/system, outside the unit/integration/e2e enum -- correct them (a drift-lock conformance test is unit; a CLI system test is e2e). (3) Seven directives carry same-line explanatory prose (frob:ticket T-0027 -- propagate...; frob:todo T-0002 registry is process-global...) that the attr parser rejects; this is the SAME ergonomic gap as T-0286 (multi-line/prose-tolerant reasons), hence blocked_by T-0286 -- once prose/continuation is tolerated, split or annotate these. NOTE scope collision: fuzz/_arbitrary.py and fuzz/_run.py are also touched by the in-flight core-commands arch burndown -- sequence this ticket AFTER that merges, or coordinate, to avoid a conflict. This is the right fix: papering the warnings over by mangling test comments would hide a real parser/secrets-gate vocabulary disagreement.

<!-- narrative-moved:src/frob/graph/dsl.py:294:T-0294 -->
: Verbs that are intentional `frob:<verb>` literal markers owned by a
: DIFFERENT subsystem (never routed through `_VERB_TABLE`, never turned
: into a graph edge) -- the DSL parser must recognize and silently skip
: them rather than reporting "unknown verb", or the two subsystems'
: vocabularies drift out of agreement (T-0294). Each entry names its owner
: so a future reader knows where the marker's contract actually lives.
: - "secret-fake": owned by `frob.gates._secrets._FAKE_MARKER` -- a
:   fixture-discharge token scanned directly out of tracked-file text,
:   deliberately never a graph edge (see that module's docstring, T-0157).
: - "used-by": owned by `frob.gates._refs` (T-0396) -- the anti-orphan
:   gate's own regex scan over each tracked file's raw text (`frob:used-by
:   <consumer>`, REF001/REF002/REF003), independent of `frob.graph`'s
:   symbol/EdgeKind model since a `frob:used-by` target is a whole FILE,
:   not a symbol, and every non-source tracked type (yaml/md/toml/...)
:   must carry it too, most of which `frob.lang` never parses at all.
: - "raises": owned by `frob.gates._exhaustive_handling` (T-0688/T-1022) --
:   the declared-propagation directive (`# frob:raises <ExceptionType>`,
:   one type per directive line, stacked above a `def`) that marks a
:   function's intentional uncaught exception escape for EXHAUST002. Its
:   own module scans directive text directly (`_DIRECTIVE_PREFIX`), never
:   a graph edge.
: - "callee-raises": owned by `frob.arch._python`/`frob.arch._ffi`/
:   `frob.gates._ffi_boundary` (T-0689/T-0931) -- the call-site sibling of
:   "raises", a same-line trailing comment (`# frob:callee-raises
:   ValueError, OSError`, or the bare empty-set form `# frob:callee-raises`)
:   declaring a call's own exception escapes for FFI002/EXHAUST002. T-2875:
:   this verb WAS previously omitted here on the claim that a same-line
:   trailing comment is one the DSL's line-based scan "never matches in
:   the first place" -- that claim is false (confirmed against
:   `parse_directives` for both a same-line trailing placement and a
:   standalone full-line placement of a bare `# frob:callee-raises`
:   comment; both produced a DSL001 unknown-verb `MalformedDirective`
:   before this fix). `_RESERVED_MARKER_VERBS` is a hand-maintained set
:   with no single canonical source to derive it from: each owning
:   subsystem above keeps its own private marker literal/regex
:   (`frob.gates._secrets._REAL_FAKE_MARKER_REASON_RE`,
:   `frob.gates._refs`'s `"frob:used-by"` prefix check,
:   `frob.gates._exhaustive_handling._DIRECTIVE_PREFIX`,
:   `frob.arch._python._FROB_RAISES_RE`) with no shared registry module;
:   introducing one is a bigger cross-subsystem change than this ticket's
:   scope. Keep this list and its per-entry owner comment in sync BY HAND
:   whenever a new call-site/marker-style verb is added elsewhere.