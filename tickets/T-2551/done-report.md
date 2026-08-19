## Done report

COV007 fired 78 times on four standalone executables. Fixed by scoping,
not by compliance: the rule's remedy ("move the anchor onto the public
caller") would collapse per-symbol doc obligations onto one symbol and
destroy the per-symbol digest bindings AFFECT001/DRIFT001 depend on.

HOW THE EXEMPTION IS EXPRESSED. Keyed on the project's own per-file
`[[refs.entrypoint]]` declaration in frob.toml -- an existing mechanism
(REF001/REF002's anti-orphan allowlist, `frob.gates._refs._load_
allowlist`, each entry carrying a MANDATORY `reason`), read here rather
than re-derived, so there is one owner and one parser for the fact.
Deliberately NOT a path glob such as `.claude/hooks/*`: a glob silently
mutes the rule for every file a directory later grows, which is this
repo's own "an exemption matching the normal case disables the guard"
failure. A new file added beside a declared one fires normally until
someone declares it and says why. That property is pinned by a test, not
just asserted here.

POSITIVE CONTROLS, BOTH DIRECTIONS (tests/unit/gates/test_cov007_
entrypoint_exemption.py, 3 tests, all passing; the repro genuinely FAILS
at the parent per --check-repro):
- a DECLARED executable with a private doc anchor -> zero COV007;
- the BYTE-IDENTICAL tree with the declaration removed -> COV007 fires;
- a library module with a private doc anchor still fires while a
  different file is declared (the declaration exempts only what it names).

MEASURED, unbudgeted `frob check --only coverage --json`, live warnings
only: COV007 114 -> 35 (79 cleared: the 78 in scripts/.claude/hooks plus
src/frob/__main__.py, which this repo ALREADY declared an entrypoint --
the exemption found it for free, which is the sign the predicate is the
right one). Bucket total 132 -> 53. `frob check --land-parity`: 40
unscoped errors, none in this ticket's files.

I CORRECTED MY OWN EARLIER CLAIM. The ticket body (written by me during
T-2370's triage) said these files' "entire surface is main() plus private
helpers by design". That is true for the three hooks (2, 1 and 0 public
symbols) but FALSE for scripts/fleet_status.py, which has 31 public
symbols -- measured with frob.lang.parse_file before relying on it. So
"no public surface" is NOT the predicate that justifies the exemption;
"executed, never imported" is, and that is exactly what [[refs.
entrypoint]] already declares. The fix rests on the correct property.

DISCLOSED SIDE EFFECT, deliberately not hidden: the four new declarations
also exempt those files from REF001/REF002's anti-orphan check. All four
are non-orphans today, so nothing changes now, but a future orphaning of
one of them will no longer be reported. The frob.toml comment says so at
the declaration site so a reader cannot miss it. Reverse the entries if
that protection is worth more than COV007's noise; the gate change itself
is independent and would then simply exempt nothing.

I ALSO REJECTED AN ALTERNATIVE, having measured it rather than reasoned
about it. Candidate redesign: fire COV007 only when the private symbol's
anchor is ALSO bound to a public symbol (the "directive rode onto the
wrong symbol" case the docstring names). Measured over the real graph:
276 private doc edges, 192 of them share an anchor with a public symbol.
That redesign would have flagged MORE of the edges people already
consider correct -- a section documenting a subsystem is routinely
anchored from both its public entry and its private helpers. Dropped.

SCOPE NOTE: the controls live in their own file because tests/test_gates.
py is under T-2543's live write lease (`scope --add` refused with
ScopeLeaseConflict). The two evidence ids that still cite test_gates.py
are PRE-EXISTING tests, not new ones.

Does not close T-2370: 53 findings remain (COV006 18, COV007 35), so the
family must NOT be promoted to ERROR.

### Changed
```
 frob.lock                                          |  20 +++-
 frob.toml                                          |  27 ++++++
 src/frob/gates/__init__.py                         |  26 +++++-
 .../unit/gates/test_cov007_entrypoint_exemption.py | 101 +++++++++++++++++++++
 tickets/T-2551/ticket.md                           |  48 +++++++++-
 5 files changed, 217 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/unit/gates/test_cov007_entrypoint_exemption.py::TestCov007EntrypointExemption::test_declared_entrypoint_is_exempt` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_cov007_entrypoint_exemption.py::TestCov007EntrypointExemption::test_same_file_undeclared_still_fires` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCoverageGate::test_cov007_still_fires_for_a_python_private_helper_after_t2549` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCoverageGate::test_cov007_flags_doc_anchor_on_private_helper` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_cov007_entrypoint_exemption.py::TestCov007EntrypointExemption::test_library_module_still_fires_when_another_file_is_declared` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2561/ticket.md, DOC006@tickets/T-2565/ticket.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2551/src/frob/app/ticket_runner/_verify.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2551/src/frob/scaffold/project.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2551, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
