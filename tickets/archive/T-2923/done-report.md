## Done report

Changed:
- src/frob/strata/_shrink.py (new): shrink_report/apply_shrink, the ONLY
  direction this repo now writes a `.strata` declaration in -- dropping a
  declared-but-never-observed `may` capability atom (SYS101). Reuses
  check_self_conformance (the same join `frob sys audit` trusts) as the
  single source of truth for what is stale, rather than re-deriving the
  observed/declared join. Conservative on a partially-stale kind (some
  but not all via-scoped instances stale): leaves it untouched entirely
  rather than guessing which via to drop.
- src/frob/app/sys_runner.py, src/frob/_cli_parsers/_misc.py,
  src/frob/app/config.py, src/frob/app/_config_external.py: CLI wiring
  for `frob sys shrink [--check] [path]`.
- design/frob.strata: declared fs.read/fs.write may grants for the new
  _shrink.py module by hand (SYS100 fired on my own diff -- the new
  module genuinely performs fs.read/fs.write; declared explicitly, never
  auto-widened by any tool); added tests/unit/strata/test_shrink.py to
  the testsuite node's net via-list (real requests.get(...) needle
  literals the fixtures need).
- docs/design/registry/capability-via-ratchet.lock.json: raised the
  SYS111 ratchet ceiling for stratamod::fs.read (9->10),
  stratamod::fs.write (3->4), testsuite::net (12->13) -- the exact,
  measured growth this ticket's new files caused, each with a reason
  naming the real declaring file.
- docs/commands/sys.md: new `frob sys shrink` section.
- tests/unit/strata/test_shrink.py (new): 11 tests across three classes.

Method (per the epic's own requirements):
- TOKEN/GRAMMAR-based, never lexical: `_shrink.py`'s own line-removal
  scan reuses `_sync_may.py`'s exact `_MAY_LINE_RE`/node-header/
  `node_body_span` (T-1895 shared brace-depth scanner) approach for
  locating `.strata` grant lines, and delegates the actual staleness
  JOIN to `check_self_conformance` (the real, tested SYS101 logic) rather
  than re-deriving observed/declared matching itself. The "does this
  module ever import a widening function" proof test parses the module's
  real AST (ImportFrom nodes), not a substring/regex scan of source text
  -- an early draft used a lexical scan and it false-positived on this
  module's OWN docstring, which names `_sync_may.py`'s widening functions
  in prose while importing none of them; fixed to the grammar-based
  check per this repo's own standing lexical-vs-grammar rule.
- Must-fire fixtures (both from the epic's own acceptance criteria),
  isolated synthetic `.strata` files under pytest tmp_path, not frob's
  own design/:
  - TestShrinkNeverWidensOrBinds::test_capability_escalation_stays_an_error_and_shrink_does_not_widen:
    a node acquires `net` it never declared; check_self_conformance still
    reports SYS100, and shrink_report leaves the `.strata` text
    byte-for-byte unchanged.
  - TestShrinkNeverWidensOrBinds::test_unbound_capability_file_stays_an_error_and_shrink_does_not_bind_it:
    a capability-bearing file no node's code= binds; check_self_conformance
    still reports SYS103, and shrink_report never invents a binding.
- Must-still-pass control on frob's OWN repo, measured before and after
  via `frob sys audit .`:
  - BEFORE (main, no diff): 9 total gaps, 2 self-conformance (both
    SYS107, pre-existing, unrelated to this ticket -- testsuite's
    via-less fs.read/fs.write over the 20-file SYS107 threshold).
    resource-contention: PROVED, zero SYS2xx gaps.
  - AFTER (this diff applied): 9 total gaps, 2 self-conformance (the
    SAME two SYS107 findings, unchanged). resource-contention: PROVED,
    zero SYS2xx gaps -- IDENTICAL to before.
  - Correction to the epic's own stated assumption: frob's own repo does
    NOT currently keep "0 SYS errors" -- it has 2 (SYS107, pre-existing,
    unrelated to this diff). Reporting the measured number rather than
    the epic's convenient assumption; what matters for this control is
    that the count is UNCHANGED by this diff, which it is.
  - `frob sys shrink --check .` against frob's own repo reports "no
    SYS101 (declared-but-never-observed) findings" / "nothing to
    tighten" -- confirmed no unintended writes (git status clean after).
- Scoped proof (honest, per the coordinator's explicit amendment --
  NOT an epic-wide claim): TestNoWideningPath asserts the shrink code
  path THIS TICKET built has no widening branch and no flag/env/config
  parameter reaches one (shrink_report/apply_shrink's full parameter
  lists inspected via `inspect.signature`; the module's own symbol names
  checked structurally; its imports checked via `ast` against
  `_sync_may.py`'s widening functions specifically).

EPIC-LEVEL CRITERION EXPLICITLY UNMET, BY DESIGN: T-2920's "no auto-
widening path exists anywhere in this repo" is NOT proven true by this
ticket, and this ticket does not claim it is. `frob.strata._sync_may`
(sync_may_report/apply_sync_may, sync_may_extended_report/
apply_sync_may_extended, T-1531/T-1545) is a LIVE, wired auto-fix that
WIDENS `may=` declarations on SYS100 (capability escalation) -- the exact
rubber-stamp T-2920 forbids, called from src/frob/gates/_fix_engine_sync.py.
Its own module docstring cites T-1623/T-1628 as the deliberate policy
that put it there ("may= capability sync is DIFFERENT, deliberate, live
work... and stays"). T-2920 REVERSES that policy on the user's explicit
instruction: `may=` is a CEILING whose purpose is to forcibly shrink the
interface, so regenerating it from observation makes the ceiling equal
whatever the code happens to do -- a rubber stamp with no teeth. This is
a deliberate policy supersession, not an oversight. T-2922 (blocks
T-2920, kind=security/critical, scoped to
src/frob/gates/_fix_engine_sync.py) is the ticket that unwires that
caller; T-2920 cannot close DONE claiming the epic-wide property until
T-2922 lands (the blocked_by edge enforces this structurally). This
ticket (T-2923) deliberately does not touch `_sync_may.py` at all --
its widening functions are left physically in place, untouched, so
T-2922's own caller does not break with an ImportError before that
ticket lands.

Filed: none new (T-2922 was already filed by the coordinator before this
ticket started).

Evidence: 11 test node ids bound (see ticket frontmatter), covering the
shrink-only write path, the conservative partial-stale skip, apply/
--check split, both must-fire controls, and the scoped no-widening
proof.

Gates: `frob check --ticket T-2923` -- gate:AFFECT/gate:SCOPE/gate:PRE/
gate:SELFAUDIT(SYS111 ratchet)/gate:ARCH/ty/ruff-check clean on every
file this ticket touched. Every other FAIL in that run (ruff-format
repo-wide, frob-cycle, gate:COV/DOC/TICK/WIRE002, claude-config-drift)
is pre-existing repo-wide baseline noise, none of it in a file this
ticket touched -- confirmed by grepping the check output for this
ticket's own file paths.

### Changed
```
 design/frob.strata                                 |   6 +-
 docs/commands/sys.md                               |  43 +++
 .../registry/capability-via-ratchet.lock.json      |  35 +-
 src/frob/_cli_parsers/_misc.py                     |  44 ++-
 src/frob/app/_config_external.py                   |   2 +
 src/frob/app/config.py                             |  10 +-
 src/frob/app/sys_runner.py                         | 101 +++++-
 src/frob/strata/_shrink.py                         | 365 +++++++++++++++++++++
 tests/unit/strata/test_shrink.py                   | 302 +++++++++++++++++
 tickets/T-2923/ticket.md                           |  56 +++-
 10 files changed, 930 insertions(+), 34 deletions(-)
```

### Evidence
- `tests/unit/strata/test_shrink.py::TestShrinkReportDropsStaleGrants::test_drops_declared_but_never_observed_capability` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_shrink.py::TestShrinkReportDropsStaleGrants::test_no_drift_when_everything_observed` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_shrink.py::TestShrinkReportDropsStaleGrants::test_partially_stale_kind_is_left_untouched` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_shrink.py::TestShrinkReportDropsStaleGrants::test_apply_shrink_writes_only_changed_files` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_shrink.py::TestShrinkReportDropsStaleGrants::test_check_only_report_never_writes` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_shrink.py::TestShrinkNeverWidensOrBinds::test_capability_escalation_stays_an_error_and_shrink_does_not_widen` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_shrink.py::TestShrinkNeverWidensOrBinds::test_unbound_capability_file_stays_an_error_and_shrink_does_not_bind_it` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_shrink.py::TestNoWideningPath::test_module_has_no_widen_or_bind_named_symbol` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_shrink.py::TestNoWideningPath::test_shrink_report_signature_has_no_widening_parameter` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_shrink.py::TestNoWideningPath::test_apply_shrink_signature_has_no_widening_parameter` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_shrink.py::TestNoWideningPath::test_this_module_never_imports_sync_may_widening_functions` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 11 passed (from 11 evidence id(s))
- gates: 19 error(s), 717 warning(s), 852 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV004@tickets/T-2195/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-2244/attachments/01-t-2244-audit-safe-to-repoint-split-test-typecheck-safe-now-lint-blocked-by-newly-found-t-2387-not-t-2359-format-lint-fix-blocked-by-both-test-fast-stays-raw.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, COV004@tickets/T-2328/attachments/02-third-reproduction-t-2323-confirmed-workaround-pre-commit-the-file-yourself-before-land.md, COV004@tickets/T-2328/attachments/03-clarification-titled-work-loss-defect-remains-open-carried-by-t-2351.txt, COV004@tickets/T-2350/attachments/01-diagnosis-timing-visibility-race-not-identity-matching-both-candidate-fix-files-leased-by-t-2351-no-edit-attempted.md, COV004@tickets/T-2543/attachments/01-class-a-options-and-measured-costs-t-2377-survey.md, CYCLE001@src/frob/__init__.py, DOC006@docs/guides/coordinator-scripts.md, DOC006@docs/modules/gates.md, DOC006@tickets/T-2886/ticket.md, DOC006@tickets/T-2920/ticket.md, DOC008@docs/commands/check.md, TICK004@tickets.md, WIRE002@src/frob/tickets/_unlanded.py
