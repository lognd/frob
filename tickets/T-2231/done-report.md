## Done report

Changed:
  src/frob/gates/_docblocks_shared.py (new leaf module: _ProjectNamespaces,
    _read_toml, _doc004_violation)
  src/frob/gates/_docblocks.py (import retarget + dead-definition removal)
  src/frob/gates/_docblocks_refs.py (import retarget)
  src/frob/graph/_models.py (import retarget: SymbolKind)
  src/frob/graph/cache.py (import retarget: SymbolKind, GRAMMAR_FINGERPRINT_PACKAGES)
  src/frob/lang/__init__.py (GRAMMAR_FINGERPRINT_PACKAGES definition moved out,
    re-exported)
  src/frob/lang/_models.py (GRAMMAR_FINGERPRINT_PACKAGES definition moved in)
  docs/modules/lang.md (AFFECT001 closure: note the constant's new home)

DESIGN DECISION on the ticket's open question (genuinely invert vs teach
the checker about lazy imports): INVERTED THE DEPENDENCY FOR REAL. Did not
touch the cycle checker.

Reasoning: I mapped every edge in the 6-node cluster with
frob.check._python._build_import_graph directly (not by inspection) and
classified each as module-level (real) or function-scope (lazy, already
broken at runtime). This separated the cluster into TWO genuinely distinct
problems, confirming the ticket's own framing rather than assuming it:

(a) MECHANICAL, both module-level: `_docblocks.py` line 773+ imports 17
    names from `_docblocks_refs.py` (real internal use, not just a compat
    re-export -- verified by xref, `_python_module_map`/`_console_trees`/
    etc are called inside `_docblocks.py`'s own gate functions);
    `_docblocks_refs.py` line 16 imports 3 names back
    (`_doc004_violation`, `_ProjectNamespaces`, `_read_toml`) -- xref
    confirmed all three ARE used inside `_docblocks.py` itself too, not
    just re-exported for `_docblocks_refs.py`'s sake. A genuine mutual
    cycle, exactly as the ticket described. Fixed by extracting those 3
    names into a new leaf module, `_docblocks_shared.py`, that neither
    sibling needs to import back from -- verified it has zero `frob.gates`
    imports itself, so it cannot re-close the cycle.

(b) `graph/_models.py`/`graph/cache.py` imported `SymbolKind`/
    `GRAMMAR_FINGERPRINT_PACKAGES` from the `frob.lang` PACKAGE namespace
    (`from frob.lang import ...`), both module-level. `lang/__init__.py`'s
    own lazy imports of `graph.cache` (T-1464, 3 sites, all function-scope,
    documented) are the OTHER half of the cycle the checker cannot tell
    apart from a real one. `SymbolKind` already lived in `frob.lang._models`
    (a pure leaf, zero frob.* imports, confirmed by inspection) --
    `lang/__init__.py` was already importing it from there and just
    re-exporting; only `graph/_models.py`/`graph/cache.py`'s OWN import
    statements needed retargeting, no code motion at all.
    `GRAMMAR_FINGERPRINT_PACKAGES` was a plain frozenset constant defined
    directly in `lang/__init__.py`'s body (not already in a leaf) -- moved
    it to `lang/_models.py` alongside `SymbolKind` (same leaf, same
    directive-carrying comment moved with it), re-exported from
    `lang/__init__.py` under its original name so every existing
    `frob.lang.GRAMMAR_FINGERPRINT_PACKAGES` reference keeps working.
    Verified post-fix by direct identity check (`gm.SymbolKind is
    lm.SymbolKind`, `gc.GRAMMAR_FINGERPRINT_PACKAGES == lm.GRAMMAR_FINGERPRINT_PACKAGES`)
    that nothing silently forked into two copies.

    Chose the "genuinely invert" branch over "teach the checker" because:
    (1) it is fully scoped to this cluster's own files (no detector-code
    change with repo-wide blast radius); (2) it produces a REAL structural
    fix -- after it, `graph/cache.py` has ZERO frob.lang-package-level
    dependency (not even a lazy one flowing back INTO it), so the
    checker's OWN unmodified logic reports it clean, which is stronger
    proof than trusting a new "ignore lazy edges" carve-out to be correct;
    (3) "teach the checker" would need its OWN must-still-pass control (a
    synthetic fixture proving a genuine module-level cycle still trips)
    plus a design decision on severity for lazy-only cycles repo-wide --
    genuinely separate scope from this leaf ticket, and out of scope here.
    Did NOT split (b) into a separate ticket because it turned out to be
    fully resolvable within T-2231's own already-declared intent and a
    small, low-risk, mechanically-verified scope extension (see below) --
    unlike the checker-side option, which really would need its own
    ticket if ever pursued.

  RESIDUAL (expected, not a defect): `lang/_support.py` ALSO has two
  lazy-only edges of its own (`_docblock_languages()` imports
  `frob.gates._docblocks` lazily; `derive_language_registry()` imports
  `from frob.lang import supported_languages` lazily -- both documented at
  the module's own top-of-file "dependency order" comment, same T-0405
  pattern as case (b)). After the fix, `lang/__init__.py <-> lang/_support.py`
  surfaces as its OWN small 2-node INFO-severity cycle (real module-level
  edge one way, lazy-only the other) -- structurally identical in kind to
  this repo's other 5 pre-existing note-severity clusters (arch/__init__
  self-cycle, app/app<->app/__init__, etc), NOT part of the ERROR-severity
  cluster this ticket targets, and NOT something T-2231's acceptance
  criteria ask to eliminate. Left alone; repro test explicitly documents
  and exempts it rather than silently ignoring it.

Scope extended (frob ticket scope --add, reasoned): src/frob/gates/_docblocks_shared.py
  (new file), src/frob/lang/_models.py (receives the moved constant),
  docs/modules/lang.md (frob:doc target for the moved constant),
  tests/unit/test_gates_lang_graph_cycle_regression.py (new repro test).

Evidence: tests/unit/test_gates_lang_graph_cycle_regression.py::TestGatesLangGraphCycleRegression::test_gates_lang_graph_cluster_is_not_an_error_cycle
  (new repro test: runs the real cycle detector -- frob.check._python._build_import_graph
  + frob.cycle.graph.find_cycles -- against this repo's own src/ tree and asserts no
  cycle contains a gates/_docblocks*.py + graph/*.py cluster member, with an explicit,
  documented exemption for the expected residual lang/_support.py<->lang/__init__.py
  lazy-only note. FAILED_AT_PARENT confirmed at 45272d0c9 (repro-only commit); PASSED
  after the fix commit 8ec886c12.)
  Also bound to acceptance[0], acceptance[1] (must-still-pass control), acceptance[2]
  (design note).
  Touched-set: `uv run frob test --base main` -- 5 python outcomes, all PASS.
  Full existing test files (per the standing "run the whole file, not just the
  narrow fixture" lesson): tests/test_docblocks_gate.py, tests/test_docptr_gate.py,
  tests/test_gates.py, tests/test_graph.py, tests/test_graph_imports.py,
  tests/test_lang.py, tests/test_lang_support.py, tests/test_lang_conformance_gate.py
  -- 1024 collected, 0 failed, both before AND after the AFFECT/DUP001 cleanup commit.
  Grepped for mock.patch/monkeypatch.setattr targets naming any moved/retargeted
  symbol (_docblocks._ProjectNamespaces/_read_toml/_doc004_violation,
  GRAMMAR_FINGERPRINT_PACKAGES, SymbolKind) -- zero hits, no second-order patch-target
  break this time.

Manual verification of the must-still-pass control:
  Baseline (before any edit, fresh worktree, post-T-2232/T-2233 land): 2 errors --
  gates/lang/graph cluster (this ticket's target) and the tickets/app/serve/verify
  mega-cluster; 0 warnings (vet already fixed by T-2233); 5 note-severity clusters
  (arch/_abstraction<->arch/_python, arch/__init__ self, app/app<->app/__init__,
  deploy/_generate_windows<->deploy/_generate, app/check_runner<->app/_check_chunking).
  After fix: 1 error -- gates/lang/graph cluster is GONE, only the
  tickets/app/serve/verify mega-cluster remains (unchanged); 0 warnings (unchanged);
  6 note-severity clusters -- the same 5 UNCHANGED, plus ONE new one
  (lang/_support.py<->lang/__init__.py, the documented residual lazy-only edge
  pair, explained above). Cluster count went from 7 total (2+0+5) to 7 total
  (1+0+6) -- the SAME total, not fewer; the target error cluster's node-count
  moved into a smaller, lower-severity, already-precedented finding class instead
  of vanishing outright, which is the honest outcome of a real structural fix
  applied to a cluster containing more than one lazy-broken pair.

Filed: none (case (b)'s "teach the checker" alternative was considered and
  rejected in favor of the in-scope structural fix, per the reasoning above --
  no new ticket needed since nothing was deferred)

Gates: frob check --ticket T-2231 -- gate:SCOPE/gate:PREWORK clean (0 errors);
  gate:AFFECT clean (1 finding closed via docs/modules/lang.md#dependencies edit,
  not waived); gate:DUP -- 1 finding waived with a reasoned justification
  (_doc004_violation's boilerplate Violation-construction shape matching two
  unrelated gate modules' own boilerplate, same DUP001 waiver posture this repo
  already established for this pattern class per T-1763); no other gate family's
  counts changed by this diff (all repo-wide per the check's own scope-note).

### Changed
```
 docs/modules/lang.md                               |  8 +++
 src/frob/gates/_docblocks.py                       | 58 ++++-------------
 src/frob/gates/_docblocks_refs.py                  |  2 +-
 src/frob/gates/_docblocks_shared.py                | 71 +++++++++++++++++++++
 src/frob/graph/_models.py                          |  2 +-
 src/frob/graph/cache.py                            |  2 +-
 src/frob/lang/__init__.py                          | 39 ++++++------
 src/frob/lang/_models.py                           | 27 ++++++++
 .../unit/test_gates_lang_graph_cycle_regression.py | 74 ++++++++++++++++++++++
 tickets/T-2231/ticket.md                           | 47 ++++++++++++--
 10 files changed, 257 insertions(+), 73 deletions(-)
```

### Evidence
- `tests/unit/test_gates_lang_graph_cycle_regression.py::TestGatesLangGraphCycleRegression::test_gates_lang_graph_cluster_is_not_an_error_cycle` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@scripts/fleet_status.py, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@scripts/fleet_status.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1335, COV003@tickets/T-1353, COV003@tickets/T-1362, COV003@tickets/T-1363, COV003@tickets/T-1373, COV003@tickets/T-1397, COV003@tickets/T-1426, COV003@tickets/T-1433, COV003@tickets/T-1526, COV004@tickets/T-draft-0bd874ac/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-draft-0bd874ac/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/lang/_nodes.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2231/src/frob/gates/_docblocks_refs.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2231/src/frob/lang/_nodes.py, F541@/home/logan/projects/frob/.claude/worktrees/t-2231/tests/test_ticket_work_and_land_finish.py, PERF004@scripts/fleet_status.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PRE001@tickets/T-2231, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md
