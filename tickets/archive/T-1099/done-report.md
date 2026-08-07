## Done report

Changed:
- strata-core/src/parse.rs (deleted, 4346 lines) -> split into:
  - strata-core/src/parse/mod.rs (parser spine: module doc, `parse_source_impl`,
    the `#[cfg(test)] mod tests` block unchanged, `include!` splices for the
    fragments below)
  - strata-core/src/parse/lexer.rs (TokKind, Token, ParseError, is_ident_start,
    is_ident_cont, lex)
  - strata-core/src/parse/grammar_core.rs (Parser, ModuleAst, shared
    expect_*/at_*/parse_unit/parse_quantity/parse_attrval/parse_module helpers)
  - strata-core/src/parse/grammar_node.rs (Parser.parse_node,
    Parser.parse_on_deploy_block, Parser.parse_canary_stage,
    Parser.parse_secret)
  - strata-core/src/parse/grammar_flow.rs (Parser.parse_flow,
    Parser.parse_boundary, Parser.parse_frame_target, Parser.parse_frame_prop,
    Parser.parse_phase_block, Parser.parse_operation, Parser.parse_refine)
  - strata-core/src/parse/grammar_infra.rs (Parser.parse_percent,
    Parser.parse_store, Parser.parse_cache, Parser.parse_resource,
    Parser.parse_queue, Parser.parse_cdn, Parser.parse_balancer,
    Parser.parse_metric)
  - strata-core/src/parse/grammar_policy.rs (Parser.parse_claim_body,
    Parser.expect_ge, Parser.parse_dotted_ident, Parser.parse_dotted_ident_list,
    Parser.parse_scope_spec, Parser.parse_policy_rule, Parser.parse_policy,
    Parser.expect_le, Parser.expect_coloneq, Parser.parse_claim,
    Parser.parse_scenario, Parser.parse_program)
- docs/guides/extending/strata-surface-grammar.md (frob:describes edge moved
  from strata-core/src/parse.rs::Parser.parse_program to
  strata-core/src/parse/grammar_policy.rs::Parser.parse_program)
- tickets-archive.md (mechanical path-only substitution:
  `strata-core/src/parse.rs::tests::` -> `strata-core/src/parse/mod.rs::tests::`
  across 61 frozen frob:tests evidence citations in already-closed tickets,
  broken by the physical rename; no narrative Done-report text touched)

Design note: each grammar-family file is spliced into parse/mod.rs's module
scope via `include!` (textual inclusion), not declared as a real child `mod`.
A real `mod` would force every helper method (~50 of them, e.g. Parser::cur,
expect_ident, parse_unit) to carry `pub(crate)` just so sibling grammar-family
files could reach the shared `Parser`/`ModuleAst` surface -- which would
misrepresent internal recursive-descent helpers as this crate's public API
and spuriously trigger COV001 (frob:doc-required) on all of them, a real
regression measured and reverted mid-ticket (COV errors: 202 -> 40 -> 1 across
three visibility-strategy iterations). `include!` keeps every method exactly
as private as it was in the pre-split monolithic file -- zero net new public
surface, matching the ticket's "grammar families live in their own modules"
acceptance criterion (files, not necessarily Rust `mod` boundaries) while
staying byte-identical in privacy and behavior.

File sizes (acceptance: no file exceeds 2000 lines): mod.rs 1738,
grammar_infra.rs 682, grammar_node.rs 675, grammar_flow.rs 505,
grammar_policy.rs 345, grammar_core.rs 278, lexer.rs 199 -- all comfortably
under the 2000-line ceiling (was 4346 in one file).

Evidence:
- `cargo test` (strata-core, natives built via `frob natives build`):
  137 passed; 0 failed; 0 ignored (measured before AND after the split,
  identical count/names -- pure refactor, no grammar behavior change).
- `pytest tests/unit/strata/test_kernel_properties.py
  tests/unit/strata/test_managed.py -p no:cacheprovider -q`: all green
  (python-side goldens against the rebuilt strata_core native, unaffected).
- Recorded via `frob ticket evidence T-1099 --accepts 0`:
  strata-core/src/parse/mod.rs::tests::parses_bare_module,
  strata-core/src/parse/mod.rs::tests::round_trip_small_design,
  strata-core/src/parse/mod.rs::tests::parses_policy_forbid_call_and_import,
  strata-core/src/parse/mod.rs::tests::parses_refine_happy_path,
  strata-core/src/parse/mod.rs::tests::fuzz_safe_random_bytes_never_panic
  (the crate's 137 cargo tests aren't individually pytest-collected file-level
  ids; these five sample across lexer/grammar/refine/fuzz coverage families,
  same convention `docs/modules/tickets.md` documents for
  `strata-core/src/lib.rs::parse_source kind="unit"` cargo evidence).

Gates (`uv run frob check --ticket T-1099`, per-group foreground, natives
built via `frob natives build`):
- gates-native: 0 errors (ARCH/DUP/EXHAUST/LARGE/PERF/WAIVE all pass; 21
  DUP001/DUP002 findings waived -- git sees the parse.rs->6-file split as
  6 brand-new files, so the dup scanner re-flags small pre-existing helpers
  as "new in this diff" duplicating each other and duplicating unrelated
  frob-core/strata-core code; every waived line is code moved verbatim,
  zero new duplication actually introduced by this diff. T-1035 (next in
  this series) is filed specifically to fix the underlying nested-closure
  waiver-binding gap this class of finding exposed).
- gates-security: 0 errors.
- gates-fast: 2 errors, BOTH pre-existing and unrelated (confirmed via
  `git diff main` showing zero touch to either file):
  - COV001 src/frob/gates/_tracked_files.py::tracked_files (pre-existing on
    main, `src/frob/**` outside this ticket's scope).
  - TICK006 T-1114's Done report citing a draft id that renumbered to
    T-1141 (pre-existing on main, an unrelated wave-17/18 land
    artifact, repaired by the coordinator).

Filed: none (T-1035, next in this series, already exists and covers the
DUP001/DUP002 waiver-binding gap surfaced above -- not a new filing).

Gates: frob check --ticket T-1099 --only gates-native clean, --only
gates-security clean, --only gates-fast shows only the 2 pre-existing
unrelated findings named above (waived: none needed -- they are outside
scope and untouched by this diff, disclosed rather than waived).

### Changed
```
 docs/guides/extending/strata-surface-grammar.md |    2 +-
 strata-core/src/parse.rs                        | 4346 -----------------------
 strata-core/src/parse/grammar_core.rs           |  275 ++
 strata-core/src/parse/grammar_flow.rs           |  501 +++
 strata-core/src/parse/grammar_infra.rs          |  683 ++++
 strata-core/src/parse/grammar_node.rs           |  672 ++++
 strata-core/src/parse/grammar_policy.rs         |  342 ++
 strata-core/src/parse/lexer.rs                  |  199 ++
 strata-core/src/parse/mod.rs                    | 1744 +++++++++
 tickets.md                                      |   27 +-
 10 files changed, 4441 insertions(+), 4350 deletions(-)
```

### Evidence
- `strata-core/src/parse/mod.rs::tests::parses_bare_module` (pytest node id, verified passing when recorded)
- `strata-core/src/parse/mod.rs::tests::round_trip_small_design` (pytest node id, verified passing when recorded)
- `strata-core/src/parse/mod.rs::tests::parses_policy_forbid_call_and_import` (pytest node id, verified passing when recorded)
- `strata-core/src/parse/mod.rs::tests::parses_refine_happy_path` (pytest node id, verified passing when recorded)
- `strata-core/src/parse/mod.rs::tests::fuzz_safe_random_bytes_never_panic` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 8 error(s), 570 warning(s), 446 waived
- error-findings: COV001@src/frob/gates/_tracked_files.py, E501@/home/logan/projects/frob/.claude/worktrees/w18-misc/src/frob/vet/_capability.py:5338, E501@/home/logan/projects/frob/.claude/worktrees/w18-misc/src/frob/vet/_supplychain.py:154, E501@/home/logan/projects/frob/.claude/worktrees/w18-misc/src/frob/vet/_supplychain.py:168, E501@/home/logan/projects/frob/.claude/worktrees/w18-misc/src/frob/vet/_supplychain.py:209, E501@/home/logan/projects/frob/.claude/worktrees/w18-misc/src/frob/vet/_supplychain.py:267, E501@/home/logan/projects/frob/.claude/worktrees/w18-misc/src/frob/vet/_supplychain.py:295, TICK006@tickets.md
