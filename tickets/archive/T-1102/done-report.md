## Done report

Wired frob.arch's language-agnostic large-file category (frob.arch._check_large_file)
into frob.gates._arch.arch_gate as LARGE001, WARN first-turn-on -- previously
advisory-only, invisible to frob check / frob:waive. Registered in
_ARCH_CATEGORY_TO_RULE (auto-picked up by generated_gate_rule_ids's static
scan, no manual registry edit needed), enforces edge CHK-GATE-LARGE001, and
a docs/modules/gates.md rule-catalog entry disclosing the measured 43-file
turn-on count (via frob.gates._arch.arch_gate itself, the real gate path,
against frob.toml's max_file_lines=800 -- not analyze_project called
standalone, which under-counts by not including frob-core's own crate the
same way the gate's repo-root invocation does).

Also fixed single-file-mode parity (acceptance [1]): frob.arch.analyze_project
now resolves a single-file root to root.parent + a one-file candidate list
before calling _collect_files, instead of handing the file straight to
frob.excludes.iter_files (which assumes a directory and silently produces
zero candidates for a plain file -- `(root / ".git").exists()` and
`os.walk(root)` both no-op on a file). Before this fix, `frob arch
<single-file>` printed "no architectural issues found" for every check
category on any file, not just large-file -- verified against
src/frob/tickets/_land.py (4762 lines) before/after.

Test-file and fixtures/ exemptions verified intact (TestArchGateLargeFile.
test_test_file_exempt_from_large001, reusing the existing T-0368/T-0372
_check_large_file exemption logic unchanged).

Litmus-first: TestArchGateLargeFile.test_large_file_fires_large001_warn
proves LARGE001 fires at Severity.WARN on an over-threshold production file;
test_single_file_mode_matches_directory_walk proves single-file mode's
finding (category/message shape) is byte-identical to the same file inside
a directory walk.

Scope cut: docs/modules/arch.md (analyze_project's own frob:doc anchors,
AFFECT001-flagged) was not touched -- outside T-1102's declared scope.
Waived with frob:waive AFFECT001 reason=... citing the follow-up ticket
filed for it: T-1104 (docs: document T-1102 single-file-mode
parity + LARGE001 in docs/modules/arch.md).

### Changed
```
 docs/modules/gates.md     |  1 +
 src/frob/arch/__init__.py | 41 +++++++++++++++++++++++++--
 src/frob/gates/_arch.py   | 28 ++++++++++++++++++-
 tests/test_arch_gate.py   | 71 +++++++++++++++++++++++++++++++++++++++++++++++
 tickets.md                | 63 ++++++++++++++++++++++++++++++++++++++++-
 5 files changed, 199 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/test_arch_gate.py::TestArchGateLargeFile::test_large_file_fires_large001_warn` (pytest node id, verified passing when recorded)
- `tests/test_arch_gate.py::TestArchGateLargeFile::test_test_file_exempt_from_large001` (pytest node id, verified passing when recorded)
- `tests/test_arch_gate.py::TestArchGateLargeFile::test_single_file_mode_matches_directory_walk` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
