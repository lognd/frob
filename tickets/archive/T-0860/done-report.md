## Done report

Both SYS100 findings were real, not scanner noise on inspection, but
needed opposite treatments:

1. `mutate`: `_run_mutants`'s `child_env = {**os.environ, MUTATION_RUN_ENV:
   "1"}` genuinely reads the whole parent environment -- a real `env`
   capability added after the T-0440 survey this node's own comment block
   documents. Fixed by adding `may "env";` to the node declaration and
   updating its comment.
2. `deploy`: SYS100's `eval` finding is a scanner self-match false
   positive. Traced the exact mechanism: `frob.vet._capability`'s python
   "eval" capability includes the plain needle "eval(" (from
   `DANGEROUS_OPERATIONS`'s `eval()/exec()` entry); `_conform.py`'s
   `_mutation_for_eval(` function definition/call sites contain that exact
   substring at the end of the identifier ("...eval(") the same way the
   already-documented `napi`-in-`openapi` and bare-`compile(` false-
   positive classes do, but this specific needle ("eval(") has no
   boundary-aware special check the way `compile(` (`_has_bare_compile_
   call`) and `napi` do. Verified directly: `grep -n "eval(" src/frob/
   deploy/_conform.py` shows zero real eval/exec builtin calls, only
   `_mutation_for_eval(`'s own definition and one call site. Rather than
   declare a false `may "eval"` (an unfalsifiable claim SYS101 exists to
   catch, and this node's own pre-existing comment already explicitly
   rejected that route), used the T-0174 `waive "SYS100:eval"` mechanism
   with the same reasoning recorded as an honest, ticket-bound waiver
   instead of leaving the finding permanently red.

The underlying scanner bug (plain "eval(" needle has no identifier-
boundary guard, unlike "compile(" and "napi") lives in
src/frob/vet/_capability.py / _capability_registry.py -- outside this
ticket's scope (src/frob/strata/**, src/frob/mutate/**,
src/frob/deploy/**, design/frob.strata). Did not file a separate draft
ticket for it: fixing the needle boundary check is a real, non-critical
scanner-precision improvement, not something blocking any current gate
(the waiver already resolves the false positive honestly), so filing it
would be busywork rather than a live gap -- noting the option here rather
than silently deciding it does not matter.

Export-golden fallout: `may "env"` + `waive "SYS100:eval"` are both
elaborated into the KernelModel and DO NOT change export_k8s_netpol/
export_seccomp/export_iam output on their own (verified: env/eval are not
among the capability kinds either exporter maps to IAM actions/k8s
netpol/seccomp syscalls) -- the golden regeneration that WAS needed
(tests/unit/strata/test_export_golden.py) is almost entirely T-0725's
own fleet/deploy/mutate/registry_model/serve node backlog, not this
ticket's two declaration edits. Regenerated once, as T-0725's own commit
(shared fix for both tickets' fallout); see T-0725's Done report and
evidence for the golden-specific verification. Recording the same three
export_golden test ids as evidence here too since this ticket's own
capability-declaration changes are part of what the regenerated goldens
now encode.

Cross-ticket ambiguity (found and fixed here, in scope): COV002 initially
flagged both edited nodes as "changed with no frob:ticket edge to an open
ticket" even though T-0860 was open and its scope literally lists
"design/frob.strata" -- root cause is T-0845 (a different, unrelated open
ticket) ALSO declaring that exact literal scope entry, a genuine
specificity tie per `_scope_covers`'s own tie-break rule (an ambiguous
tie does not count as covered by design). Fixed by adding explicit
`// frob:ticket T-0860` directives above both node blocks.

Out-of-scope discovery: filed T-0881 for a pre-existing COV001/
DOC002 anchor mismatch on src/frob/exports/__init__.py (landed by T-0858,
unrelated to strata/mutate/deploy) -- see T-0708's Done report for the
full description; not repeating it here since the file/discovery is
identical and already tracked once.

Measured: `uv run pytest tests/unit/strata/test_selfconform.py::
TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant
tests/unit/strata/test_export_golden.py -p no:cacheprovider -q` -> 4
passed. `frob check --ticket T-0860 --only lint` -> 0 errors 0 warnings.
`--only static` -> 0 errors, 186 pre-existing warnings (unrelated).
`--only coverage` -> 5 errors, all 5 = T-0881 (0 of my own).

### Changed
```
 design/frob.strata                      |   18 +
 tests/golden/frob_export_iam.json       |  210 +++++++
 tests/golden/frob_export_k8s.yaml       |  190 ++++++
 tests/golden/frob_export_seccomp.json   |  117 +++-
 tests/system/test_cli_native_missing.py |   20 +-
 tickets.md                              | 1014 ++++++++++++++++++++++++++++++-
 6 files changed, 1540 insertions(+), 29 deletions(-)
```

### Evidence
- `tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_export_golden.py::TestExportGolden::test_k8s` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_export_golden.py::TestExportGolden::test_seccomp` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_export_golden.py::TestExportGolden::test_iam` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
