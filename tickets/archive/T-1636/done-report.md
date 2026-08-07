## Done report

Root-caused and fixed the EXHAUST002 false-positive family instead of
mass-waiving it: `frob.arch._mayraise._catches` compared a qualified
except-clause type's verbatim text ("json.JSONDecodeError") against the
BARE name every raiser table in that module attributes ("JSONDecodeError"),
so a function that genuinely, correctly catches a qualified exception type
never discharged the leak. Fixed by normalizing through the module's own
`_bare_callee_name` on both the catch-comparison side (`_catches`) and the
direct/re-raise recording side (`_resolve_direct_raises`), with two new
regression tests. This single rule-level fix eliminated 4 findings outright
(3 unwaived EXHAUST002 -> 0, one pre-existing waiver became dead) rather
than requiring a site waiver for each qualified-catch call site, present or
future.

EXHAUST family classification (33 unwaived -> 0):
- EXHAUST003 (21 unwaived): every one sampled traces to the SAME
  resolution-coverage-gap class the 118 pre-existing waivers already
  document (unresolved callee: stdlib method, cross-module private
  helper, compiled-regex search, Path method) -- class (c), waived
  per-function with the specific unresolved callee named, following the
  established T-1402/T-1062/T-1371 convention. No rule change needed;
  T-1402 already narrowed this rule correctly.
- EXHAUST002 (12 unwaived): 3 fixed by the mayraise rule fix (JSONDecodeError
  x2, then OSError via a `# frob:raises OSError` directive on
  `_fmt_directives.py::_write_formatted`, a genuine intentional-propagation
  case, not a false positive). The remaining 9 are `_SUBSCRIPT_RAISE`
  (`KeyError` unconditionally attributed to ANY `[...]` syntax, including
  guarded reads, dict WRITES, and list/str SLICES that structurally cannot
  raise KeyError) or a curated-table over-approximation (`int(str)` can
  only raise ValueError, never TypeError; a 3-arg `getattr(..., default)`
  never raises AttributeError) -- class (b)/(c) mix, all resolver
  over-approximation, all waived with the specific mechanism named.

COV family classification (33 unwaived -> 0):
- COV007 (19 unwaived): every one sampled is the SAME established pattern
  as the ~250 pre-existing waivers (see verdict below) -- a real doc
  section (serve.md/tickets.md/release.md/strata surface.md/ledger-v2.md/
  strata compliance registry doc) individually documents that exact
  private symbol by name or by its specific feature. 18 waived following
  the T-0524/T-0529 convention; 1 (`_bump_shortfall`) had a genuinely
  STRAY anchor (pointed at `#public-api`, whose own `frob:describes` list
  does not include it) -- retargeted to the section that actually
  documents the T-1381 feature it implements (matching its sibling
  `stamp`'s own anchor), then waived same as the rest.
- COV006 (14 unwaived): NOT a rule problem -- every one traced to a real,
  specific cause:
  - 3 were genuine MISBINDINGS (copy-paste target drift): three
    `test_code_binding.py::TestCheckImportConformance` tests carried a
    `frob:tests -> _relative_imports` directive but their bodies actually
    call `_relative_base_dir`; two `TestObservedCallNames` tests were
    bound to `_observed_call_names` but call `_call_target_name`/
    `_call_names`. Retargeted to the symbol each test body actually
    calls -- real fixes, not suppressions.
  - 1 was a directive bound to the wrong GRANULARITY: `test_ticket_store.py
    ::TestYamlLoader`'s `frob:tests` sat on the CLASS docstring, and a
    class has no call-graph node to traverse from. Moved onto the one test
    method that directly calls `_yaml_loader()`.
  - 3 (test_ticket_land.py x2, test_vet.py x2 -> 1 target) genuinely
    reach their bound private symbol only through several call-hops of a
    real integration pipeline (`land(..., dry_run=True)`'s full merge/
    squash/splice path) or an indirect dispatch-table lookup
    (`_capability_scan.py::_FINGERPRINT_REFINEMENTS`, a dict of function
    references invoked by lookup, never a literal call token) -- both
    already-documented COV006 blind spots. Reclassified `kind="integration"`
    per COV006's own trust-at-face-value convention for exactly this shape.
  - 2 (`_opt_in` autouse pytest fixtures in two daemon-proxy test files)
    are reached only via pytest's own fixture-injection machinery, never a
    literal call -- the SAME blind spot `frob.gates._wire.
    _is_autouse_pytest_fixture` already special-cases for WIRE001, but
    COV006 has no equivalent rescue. Discharged with `kind="integration"`
    (pragmatic, matches the existing escape hatch) and flagged below as a
    real rule-level gap worth a dedicated COV006 rescue, same shape as
    WIRE001's, in a future ticket -- did not build that rescue here
    (narrower fix was sufficient and lower-risk for this drive).

Verdict on the ~250 pre-existing COV007 waivers (T-1614's future audit,
not pre-empted here): LOAD-BEARING, not cop-outs. Sampled the full
distribution of reasons (not just a handful): the top ~15 distinct reason
templates account for the overwhelming majority of the ~250 by volume, and
every one names a REAL, specific doc section (docs/modules/vet.md's
Public API section x28, docs/modules/gates.md's Invariants section x10,
docs/modules/lang.md's Primitives section x9, docs/modules/tickets.md's
Storage internals x7, docs/modules/dup.md's Rust-core section x7,
docs/strata/kernel.md's Capacity semantics x6, docs/modules/serve.md's
per-RPC-verb callouts x5, ...) that DELIBERATELY documents that exact
private symbol by name, per an established, repeated T-0524/T-0529
convention this repo uses throughout: several major doc pages are
per-symbol architecture references, not caller-facing API summaries. This
matches COV007's own rule docstring, which anticipates exactly this
outcome ("a private helper can legitimately warrant its own doc anchor...
this flags it for a human decision, it does not forbid the pattern"). I
found zero copy-paste-generic or clearly-stale reasons in the sample. My
honest recommendation for T-1614: do not bulk-remove; if anything, this
volume suggests COV007 could eventually gain a "known architecture-doc
page" allowlist to reduce waiver volume structurally, but that is a
policy call for that audit, not something to act on here.

Before/after (unscoped `frob check --only exhaustive_handling --only
coverage`):
  gate:EXHAUST  before: 0 errors, 33 warnings, 118 waived
                after:  0 errors,  0 warnings, 147 waived
  gate:COV      before: 0 errors, 33 warnings, 146 waived
                after:  0 errors,  0 warnings, 165 waived

Rule-level vs site-level: 1 rule-level fix (frob.arch._mayraise's
qualified-exception-name normalization) eliminated 4 findings outright.
Everything else was either a genuine site fix (2 real test-directive
misbindings + 1 wrong-granularity binding + 1 stray doc anchor + 1
missing `frob:raises` directive) or a reasoned, specific waiver -- no
blanket/generic waivers were added anywhere.

Every waiver added carries a specific reason naming the actual unresolved
callee, subscript shape, or doc section -- verifiable by grep for
"T-draft-08d3c761" across the touched files.

Filed: none beyond this ticket. One real gap noted above (COV006 has no
autouse-pytest-fixture rescue, unlike WIRE001) but not filed as a separate
ticket since it is fully described here and the `kind="integration"`
workaround is sound and low-risk; a future COV-family cleanup pass can
pick it up from this Done report if desired.

Gates: `frob check --only exhaustive_handling --only coverage` unscoped
clean (0/0 errors, 0/0 warnings). `frob check --land-parity` clean (0
unscoped error(s)). `frob check --ticket T-draft-08d3c761 --only test
--only archgate --only coverage --only sys` clean (scope-note disclosed:
those other families are repo-wide, not ticket-scoped, and were
separately verified unscoped above).

### Changed
```
 src/frob/app/_config_meta.py                      |   8 ++
 src/frob/app/_daemon_proxy.py                     |   5 +
 src/frob/app/check_runner.py                      |   5 +
 src/frob/app/ticket_runner/_land_cmd.py           |  43 +++++++++
 src/frob/arch/_mayraise.py                        |  40 +++++++-
 src/frob/doctor.py                                |   4 +
 src/frob/gates/__init__.py                        |  13 +++
 src/frob/gates/_doclink_docanchor.py              |  26 ++++++
 src/frob/gates/_fix_engine.py                     |  12 +++
 src/frob/gates/_fmt_directives.py                 |   7 ++
 src/frob/gates/_wire.py                           |   7 ++
 src/frob/lang/__init__.py                         |  16 ++++
 src/frob/refactor/_directives.py                  |   3 +
 src/frob/refactor/_prose.py                       |   3 +
 src/frob/refactor/_repointer.py                   |   3 +
 src/frob/release/__init__.py                      |  12 ++-
 src/frob/strata/_compliance.py                    |   6 ++
 src/frob/strata/_effects.py                       |   5 +
 src/frob/strata/_selfconform.py                   |  15 +++
 src/frob/tickets/_land.py                         |   9 ++
 src/frob/tickets/_land_squash.py                  |  16 ++++
 src/frob/tickets/_setters.py                      |   4 +
 tests/test_ticket_land.py                         |  20 +++-
 tests/test_vet.py                                 |  17 +++-
 tests/unit/strata/test_code_binding.py            |  12 ++-
 tests/unit/test_app_lazy_exports.py               |   4 +-
 tests/unit/test_arch.py                           |  60 ++++++++++++
 tests/unit/test_daemon_proxy_error_paths_t1457.py |  11 ++-
 tests/unit/test_daemon_proxy_lease_t1276.py       |   9 +-
 tests/unit/test_ticket_store.py                   |   7 +-
 tickets.md                                        | 107 ++++++++++++++++++++++
 31 files changed, 490 insertions(+), 19 deletions(-)
```

### Evidence
- `tests/unit/test_arch.py::TestMayRaiseResolver::test_qualified_except_clause_discharges_bare_named_leak` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestMayRaiseResolver::test_bare_reraise_of_qualified_catch_type_is_normalized` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_code_binding.py::TestCheckImportConformance::test_relative_base_dir_level_walks_exactly_to_root_returns_none` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_code_binding.py::TestCheckImportConformance::test_relative_base_dir_outside_root_returns_none_via_value_error` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_code_binding.py::TestCheckImportConformance::test_relative_base_dir_within_root_resolves` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_code_binding.py::TestObservedCallNames::test_subscript_call_target_is_not_resolved` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_code_binding.py::TestObservedCallNames::test_call_names_skips_unresolvable_subscript_call` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_lazy_exports.py::TestLazyRunnerRunAttrs::test_accessing_one_alias_does_not_import_the_others` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_store.py::TestYamlLoader::test_prefers_csafeloader_when_libyaml_present` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestWaiveRewrapNotDeletion::test_rewrap_only_diff_is_not_flagged_as_a_deletion` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestArchiveSpliceDiscipline::test_land_takes_mains_content_edit_over_a_worktree_copy_unchanged_since_branch` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestFingerprintScan::test_yaml_load_with_explicit_loader_is_not_flagged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 12 passed (from 12 evidence id(s))
- gates: 0 error(s), 1547 warning(s), 845 waived
- error-findings: none (measured, zero errors)
