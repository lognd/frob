## Done report

T-0440: deploy/serve/mutate split off core's former utility-hub node into
three standalone strata nodes with their own real, measured effects/kill
switches/edges, closing the modeling-debt this ticket described.

Measurement method (mirrors the file's own established discipline):
frob.strata._effects._line_effects (the same net/fs/exec scanner
check_capability_conformance itself uses) and
frob.vet._capability._scan_directory_capabilities run directly against
src/frob/deploy/**, src/frob/serve/**, src/frob/mutate/** to get ground
truth before writing any `may` declaration.

Findings:
- mutate: real fs (write_text)/fs-read (read_text)/exec
  (guarded_subprocess_run) -- all three genuine, all already routed
  through the real FROB_DISABLE_EXEC kill switch (T-0803's
  ExecDisabled-abort behavior, not a mis-scored "killed" mutant).
  Declared `may "exec"`/`"fs"`/`"fs-read"` + `attr
  flag=frob_check_exec_kill_switch`.
- deploy: real fs (open("rb") in _drift.py, per the registry_model/fleet
  precedent that maps to bare "fs" not "fs-write")/fs-read
  (read_text)/exec (_vm_runner.py's guarded_subprocess_run, real kill
  switch). The scanner ALSO flagged "eval" here -- verified by hand as a
  T-0151-class false positive: the needle `eval(` matches
  `_conform.py::_mutation_for_eval`'s own Python FUNCTION NAME, not a
  call to eval()/exec(); direct grep of src/frob/deploy/** confirms zero
  real eval/exec-builtin calls. NOT declared (an unfalsifiable claim
  SYS101 exists to catch), matching gates' own precedent for the
  analogous compile()-vs-re.compile() false positive.
- serve: measured ZERO net/fs/exec/eval effects of its own by BOTH
  scanners. Every effect a `frob serve` request performs (cache reads,
  git subprocess calls, gate/graph/ticket reads) is delegated to
  core/gates/graphlang/tickets_ledger code, modeled as flow edges, not
  serve's own capability. Declared as a genuinely zero-`may` node (same
  shape as the `registry` boundary node, minus foreign clearance) -- the
  MCP stdio transport boundary itself (an external agent process talking
  to this component directly) is the real, previously-undeclared surface
  this split makes visible, documented in prose since the grammar has no
  first-class "external client" marker beyond node/flow/boundary.

Added 10 flow edges (cli -> deploy/mutate/serve inbound;
deploy -> stratamod/core, mutate -> core, serve ->
core/gates/graphlang/tickets_ledger outbound) and 2 THREAT003 `assume`
discharge claims (weakness:CWE-78:deploy, weakness:CWE-78:mutate --
mutate declares no `may "eval"` so no CWE-94; deploy same). serve drags
in zero obligations (no `may` atoms).

DISCLOSED PRE-EXISTING DEBT (found while re-measuring, not introduced by
this ticket): tests/system/test_frob_self_model.py's node/flow/claim
counts (10/27/23) were ALREADY stale against the pre-T-0440 tree
(measured directly: 12/32/24) before this ticket touched them --
specifically, T-0707's `fleet` node has declared `may "exec"` (dragging a
weakness:CWE-78:fleet discharge claim) since before this ticket, and that
claim was never folded into this docstring's running tally. Both tests
in that file were RED on main prior to this ticket (verified by
temporarily swapping in the original design/frob.strata against the
original test file and running pytest: test_parses_and_elaborates and
test_every_claim_proves both failed). This ticket's edits fix both the
pre-existing fleet gap and the new T-0440 counts together in one
re-measurement pass (10/27/23 -> 15/42/26), since both live in the same
test file already in scope. No new ticket filed for this -- it is
disclosed here rather than fixed silently, and the fix is a strict
re-measurement (both counts only ever moved toward the real, currently
elaborated model, never fudged to make an assertion pass).

Docs: docs/strata/roadmap.md's D7 component-count paragraph updated
(8 -> 13 components, noting T-0707's registry_model/fleet and this
ticket's deploy/serve/mutate split, and the narrower dup+frob-core
package list).

No new ticket filed for the T-0151-class eval-needle-vs-function-name
scanner false positive on _conform.py -- the original T-0150 Done report
already filed the general scanner-precision ticket this specific
instance falls under; disposed here the same way gates' own
`compile(`-vs-`re.compile(` precedent was disposed (documented,
not-declared, not re-filed).

Gates: chunked `frob check --only <stage>` run for every stage group
(lint, static, gates-fast, gates-native, gates-security), each 0 errors
attributable to this ticket. `frob ticket sweep T-0440` re-run twice
mid-session to keep PRE001 (pre-work-sweep staleness) fresh against
edits; not a content finding. `git diff main --diff-filter=D --stat` is
empty (no out-of-scope deletions).

Scope narrowed at the start per dispatch instructions: tests/** ->
tests/system/test_frob_self_model.py + tests/unit/strata/test_effects.py
(frob ticket scope --reason-file, recorded in the ticket's scope_changes
audit trail).

### Changed
(no changed files detected)

### Evidence
- `tests/system/test_frob_self_model.py::TestFrobSelfModel::test_model_file_exists` (pytest node id, verified passing when recorded)
- `tests/system/test_frob_self_model.py::TestFrobSelfModel::test_parses_and_elaborates` (pytest node id, verified passing when recorded)
- `tests/system/test_frob_self_model.py::TestFrobSelfModel::test_every_claim_proves` (pytest node id, verified passing when recorded)
- `tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_effects.py::TestDeployServeMutateNodeSplitConformance::test_deploy_declares_every_real_effect_it_exercises` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_effects.py::TestDeployServeMutateNodeSplitConformance::test_mutate_declares_every_real_effect_it_exercises` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_effects.py::TestDeployServeMutateNodeSplitConformance::test_serve_declares_zero_may_and_exercises_zero_effects` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: 0 error(s), 1204 warning(s), 210 waived
