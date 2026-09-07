## Done report

Registered BARETOOL001 (T-4146's gate) in every enumerating list its
rule id needed: _KNOWN_GATE_RULES (frob.gates._waive), the package
audit (frob.lang._support.LANGUAGE_SENSITIVE_PACKAGES, for the newly-
visible frob.process package), the vet exports policy
(frob.vet.__init__'s re-export of BareToolchainFinding/
bare_toolchain_findings), and frob.check._STAGE_GROUPS. Verified each
independently against the real repo tree (gate_rule_registry_violations
== 0, unfaceted_packages == (), test_exports clean, stage-group
coverage assertion clean).

Found and fixed a genuine, unrelated bug the same self-gate batch
introduced: frob.process._project_tool.project_tool_argv's `uv run
--project <root>` call lazily locks/syncs the TARGET project's own
environment on first use, writing an untracked uv.lock (and .venv/)
into that project's working tree as a side effect of a read-only lint/
typecheck spawn -- so a later gate in the SAME `frob check` invocation
diffs that tree and refuses on the file frob itself just wrote
(PRE001/SCOPE001 on a "clean" project). Reproduced deterministically
outside pytest (a fresh git-committed project, `frob check` exits 1
with exactly "2 errors" before the fix, 0 after), fixed by adding
--no-sync to project_tool_argv and routing resolve_project_tool's
which-probe spawn through it instead of a second hand-rolled uv
invocation.

Advisory-vs-exit-code question: the concurrency advisory
(_report_concurrent_check_advisory_best_effort) already cannot affect
exit code by construction -- it is a print/log call in
_dispatch_default BEFORE `App(cfg)()` runs and computes the real exit
code, and its own docstring states "ADVISORY ONLY -- never blocks,
queues, or refuses this check". Code inspection plus the existing
TestConcurrentCheckAdvisory unit suite (already passing, unmodified)
confirm this holds. The CI failure that looked advisory-caused was the
uv.lock bug above: the advisory line printed first (because another
check genuinely was running) ahead of the SAME run's real PRE001/
SCOPE001 errors, making the advisory look responsible for a nonzero
exit it never touched. No code change to the advisory itself was
needed or made; the third ticket fixture (concurrent check exits 0,
advisory still printed) now holds because the real cause (uv.lock) is
fixed.

Enumeration count (the durable question): measured 6 lists a new gate
(name + rule id) must reach --  frob.gates._ALL_GATES,
_CANONICAL_GATE_ORDER, _build_process_jobs, _CACHEABLE_PROCESS_GATES
(conditional), frob.check._STAGE_GROUPS, and
frob.gates._waive._KNOWN_GATE_RULES -- plus 2 more for a new PACKAGE
(frob.lang._support.LANGUAGE_SENSITIVE_PACKAGES, and that package's own
__init__.py __all__ exports policy). Documented in full in
docs/modules/gates.md#registering-a-new-gate-t-4163, with GATERULE001's
own refusal message now naming all six gate/rule lists explicitly
(previously named only _KNOWN_GATE_RULES). A single unified GateSpec
registry replacing the six is the right long-term fix but is a real
refactor (_ALL_GATES alone has dozens of call sites across
frob.gates/frob.check/frob.tickets) -- filed as T-4165 rather than
attempted in this ticket.

Filed: T-4165 (frob.gates: unify gate registration into a single
GateSpec registry).

Scope note: src/frob/gates/_waive.py, src/frob/gates/__init__.py, and
src/frob/check/__init__.py are large, heavily cross-referenced files;
SCOPE002's doc/test closure over them pulls in a wide, pre-existing set
of unrelated docs this ticket does not touch or intend to own
(docs/commands/check.md, docs/modules/app.md, docs/modules/perf.md,
docs/modules/release.md, docs/modules/serve.md, and further src files
anchored into docs/modules/gates.md). Acknowledged via `frob ticket
scope-ack` rather than expanding scope to cover files this ticket does
not actually change.

### Changed
```
 docs/design/registry/check-coverage.yaml |  7 +++-
 docs/modules/gates.md                    | 72 +++++++++++++++++++++++++++++++-
 docs/modules/lang.md                     |  7 ++--
 docs/modules/process.md                  | 14 ++++++-
 frob.lock                                | 20 ++++++++-
 src/frob/check/__init__.py               |  3 ++
 src/frob/gates/_bare_toolchain.py        |  2 +
 src/frob/gates/_rule_id_scan.py          | 10 ++++-
 src/frob/gates/_waive.py                 |  5 +++
 src/frob/lang/_support.py                | 15 +++++++
 src/frob/process/_project_tool.py        | 29 +++++++------
 src/frob/vet/__init__.py                 |  3 ++
 tests/unit/test_project_tool.py          | 25 +++++++++--
 tickets/T-4163/ticket.md                 |  9 ++++
 14 files changed, 198 insertions(+), 23 deletions(-)
```

### Evidence
- `tests/gates/test_rule_id_scan_branches.py::TestGateRuleRegistryGate::test_unregistered_id_reported_as_error` (pytest node id, verified passing when recorded)
- `tests/unit/test_exports.py::TestFrobExportsPolicyResidue::test_all_nine_packages_report_zero_missing_symbols` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_check.py::TestCheckStageGroups::test_available_stages_cover_every_gate_and_tool` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_check.py::TestCheckCleanProject::test_clean_code_exits_zero` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_native_missing.py::TestNativeMissingFailsLoud::test_check_unaffected_when_no_strata_files` (pytest node id, verified passing when recorded)
- `tests/test_lang_support.py::TestPackageAudit::test_real_repo_source_tree_is_fully_registered` (pytest node id, verified passing when recorded)
- `tests/unit/test_project_tool.py::TestProjectToolArgv::test_shape` (pytest node id, verified passing when recorded)
- `tests/unit/test_main_entry.py::TestConcurrentCheckAdvisory::test_force_stderr_writes_to_stderr_not_stdout` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: 6 error(s), 4519 warning(s), 937 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@src/frob/process/_project_tool.py, COV001@src/frob/vet/_bare_toolchain.py, CROSSTICKET001@frob.lock, DRIFT002@src/frob/check/_python.py, SCOPE002@tickets.md
