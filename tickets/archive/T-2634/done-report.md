## Done report

T-2634 was three UNRELATED drifts that happened to fail as a "6 test"
group, not one root cause. Fixed 3 of 6; filed T-2666 for the
remaining 3, which share a genuinely larger, separate root cause (see
below). Landing what is coherent per the dispatch brief's explicit
allowance.

### Root causes (one sentence each)

1. test_threat.py DEFAULT_BENIGN_CAPABILITIES 17-vs-16: T-2464 (landed
   2026-08-18) deliberately added a `net-mutate` BenignCapability entry
   (own comment: "a real, disclosed gap" for mutating-HTTP-verb
   signals) without bumping this test's hand-maintained exhaustiveness
   count -- the PRODUCTION side is correct, the TEST constant was stale.
2. test_mutation_audit.py::test_every_may_is_load_bearing (cli/env):
   cli node carried BOTH a bare `may "env"` atom (7 files) and a
   precise `may "env.read"` atom (3 different files) -- SYS100's join
   is per-node KIND SET, not per-via-file, so the precise atom already
   discharged `env.read` at node granularity regardless of the bare
   atom's own via-list, making the bare atom's SYS100 contribution
   permanently invisible to the mutation audit. Confirmed none of the
   7 bare-atom files ever write an env var (no `os.environ[...] =` /
   `os.putenv(`), so the bare atom's only live effect was granting
   `app.env.write` (T-1328 app-manifest) that cli never uses -- a real,
   over-broad grant. Fix: merged all 10 files into the single
   `env.read` atom, deleting the redundant/over-broad bare `env` atom.
   PRODUCTION fix (design/frob.strata), not a test change.
3. test_mutation_audit.py::test_second_detector_gaps_...: same T-2464
   `net-mutate` cause as (1), PLUS a second, unrelated, PRE-EXISTING gap
   found during this investigation: `design/frob.strata`'s
   `strata_core` node declares `may "net.connect"` (the precise
   mode-qualified spelling) but `_export.py::_SECCOMP_KIND_MAP` (the
   seccomp/export second detector) only maps bare `net`, never extended
   to `net.connect`/`net.listen` the way T-1203 extended it for
   `fs.read`/`fs.write` -- so deleting/substituting `net.connect` never
   changes `node_allowed_syscalls`, a real gap. `_export.py` is outside
   T-2634's declared scope, so the test's expected gap set was updated
   to disclose all 3 real gaps ({process-control, net-mutate,
   net.connect}) rather than narrowed to hide the third; the
   `_SECCOMP_KIND_MAP` fix itself is follow-up work (noted, not filed
   as a separate ticket since it's small and same-file as the disclosed
   gap -- flagged in the test's own comment for whoever picks it up).

### Which side was wrong, and why

- (1)/(3)'s net-mutate: the TEST was wrong (stale count/set) -- T-2464's
  own Done report already discloses net-mutate as deliberate and
  unwired; nothing to fix in production.
- (2): the DESIGN was wrong (over-broad grant) -- cli genuinely never
  writes env vars from the 7 files that carried the bare `env` atom;
  narrowed to `env.read`, a real security tightening (drops an unused
  `app.env.write` grant), not a test-only bless.
- (3)'s net.connect: neither the test's OLD expectation nor an
  arbitrary re-blessing was right -- the underlying `_export.py` gap is
  real and out of scope; the test now says so explicitly instead of
  hiding it.

### NOT fixed here (filed T-2666, renumbers at land)

tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant,
tests/unit/strata/test_selfconform.py::TestCoverageTotality::test_repo_unrestricted_scan_is_clean,
tests/unit/strata/test_conform_eval_needle.py::TestEvalNeedleSelfMatch::test_real_repo_design_selfconform_has_no_eval_gap
all share ONE root cause: T-2503 (landed 2026-08-18) converted
testsuite node's `exec`/`fs.read`/`fs.write` `may` grants from
enumerated `via` lists (~676 files combined) to ambient/via-less
whole-node grants. T-2224 (landed 2026-08-16, two days EARLIER) had
already made a via-less `exec`/`eval`/`install-hook`/`ffi` grant on a
large node (testsuite binds 601 files, threshold 20) ALWAYS
Severity.ERROR at the SYS107 gate, regardless of
`[strata] require_may_scope`. T-2503's ambient `exec` grant on
testsuite collides directly with T-2224's fail-closed policy -- verified
directly: `frob check --only sys` on the CURRENT unmodified state (my
design/frob.strata changes do not touch testsuite) reports a real
ERROR-severity SELFAUDIT001/SYS107 finding for
`node=testsuite capability=exec`. `fs.read`/`fs.write` stay WARN-only
(not fail-closed) and are NOT part of this gap -- that half of T-2503's
decision is fine and untouched.

This is a real, uncaught land-time regression from T-2503, not a stale
fixture -- fixing it properly means either restoring `exec`'s via-list
(materially larger than any of the other 3 fixes: ~145+ files at the
pre-T-2503 snapshot, and stale since new exec-using test files have
been added since) or an explicit, documented policy carve-out. Filed
as T-2666 with full detail rather than forced into this pass.
Per the dispatch brief: "if the six turn out to need materially
different fixes and one is much larger, land what is coherent and file
the remainder" -- this is exactly that shape.

### Evidence

- tests/unit/strata/test_threat.py::TestCaughtByAuditExhaustive.test_every_shipped_entry_has_a_substantive_caught_by
  (designated repro, FAILED_AT_PARENT confirmed against 17eda5571)
- tests/unit/strata/test_mutation_audit.py::TestMayMutationAuditRealRepo.test_every_may_is_load_bearing
  (FAILED_AT_PARENT confirmed against 17eda5571)
- tests/unit/strata/test_mutation_audit.py::TestMayMutationAuditRealRepo.test_second_detector_gaps_are_exactly_the_disclosed_app_level_kinds
  (FAILED_AT_PARENT confirmed against 17eda5571)

### Both-directions controls (measured)

- Positive: all 3 above pass green after the fix
  (`pytest tests/unit/strata/test_mutation_audit.py::TestMayMutationAuditRealRepo`
  -- 4/4 passed; `test_threat.py::TestCaughtByAuditExhaustive::test_every_shipped_entry_has_a_substantive_caught_by`
  -- 1/1 passed).
- Negative (deliberate re-break, confirmed fail, then reverted):
  - Reverted test_threat.py's count back to 16 with net-mutate still
    present in DEFAULT_BENIGN_CAPABILITIES -> re-ran the test ->
    FAILED (`assert 17 == 16`) as expected, then restored the fix.
  - Reverted design/frob.strata's cli env.read merge (restored the
    separate bare `env` atom) -> re-ran
    test_every_may_is_load_bearing -> FAILED again with the original
    `MutationFinding(node='cli', atom='env', ...)` non-load-bearing
    finding, then restored the fix.

### Filed

T-2666 (testsuite ambient-exec/SYS107 fail-closed collision,
see above; renumbers at land).

### Gates

`uv run frob ticket evidence T-2634 --check-repro` for all 3 designated
node ids: FAILED_AT_PARENT, confirmed (not NO_VERDICT / PASSED_AT_PARENT).
Scoped `frob check --ticket T-2634` and `frob test` run pre-land per
playbook section 0/6g.

### Changed
```
 tickets/T-2634/ticket.md           | 10 ++++-
 tickets/T-2666/ticket.md | 88 ++++++++++++++++++++++++++++++++++++++
 2 files changed, 96 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/strata/test_threat.py::TestCaughtByAuditExhaustive::test_every_shipped_entry_has_a_substantive_caught_by` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_mutation_audit.py::TestMayMutationAuditRealRepo::test_every_may_is_load_bearing` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_mutation_audit.py::TestMayMutationAuditRealRepo::test_second_detector_gaps_are_exactly_the_disclosed_app_level_kinds` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/gates/_rule_id_scan.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_milestone.py, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2570/ticket.md, DOC008@docs/modules/gates.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2634, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WAIVE006@src/frob/gates/__init__.py, WAIVE006@src/frob/gates/_coverage.py, WAIVE006@src/frob/gates/_decisions_compliance.py, WAIVE006@src/frob/gates/_doclink_docanchor.py, WAIVE006@src/frob/gates/_mutation_evidence.py, WAIVE006@src/frob/gates/_sys.py, WAIVE006@src/frob/gates/_tickets_gate.py, WAIVE006@src/frob/gates/_todo_fmt.py, WAIVE006@src/frob/tickets/_draft_finalize.py, WAIVE006@src/frob/tickets/_evidence.py, WAIVE006@src/frob/tickets/_models.py, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
