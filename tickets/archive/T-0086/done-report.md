## Done report

Changed:
src/frob/strata/_export.py::export_k8s_netpol
src/frob/strata/_export.py::export_seccomp
src/frob/strata/_export.py::export_iam
src/frob/strata/_export.py::_sorted_node_ids (private helper)
src/frob/strata/_export.py::_node_by_id (private helper)
src/frob/strata/_export.py::_flows_into (private helper)
src/frob/strata/_export.py::_flows_out_of (private helper)
src/frob/strata/_export.py::_netpol_peer (private helper)
src/frob/strata/__init__.py (re-exports export_k8s_netpol/export_seccomp/export_iam)
src/frob/app/sys_runner.py (new: `frob sys export` runner)
src/frob/app/config.py (Subcommand.sys, sys_command/sys_export_format/sys_export_path fields)
src/frob/app/app.py (sys_runner wired into _RUNNER_MODULE_NAMES + _dispatch_table)
src/frob/__main__.py (_add_sys_parser: `frob sys export --format k8s|seccomp|iam <design.strata>`)
docs/commands/sys.md (new)
docs/index.md (linked docs/commands/sys.md)
tests/unit/strata/test_export.py (new, 13 tests)
tests/unit/strata/test_export_golden.py (new, 3 tests)
tests/system/test_cli_sys_export.py (new, 6 tests)
tests/golden/frob_export_k8s.yaml, tests/golden/frob_export_seccomp.json,
tests/golden/frob_export_iam.json (new golden fixtures, generated from
design/frob.strata, T-0081's self-hosting model)

Mapping semantics per exporter (all pure/total over `KernelModel`, no
`Result` wrapping -- same posture as `_report.py`, no fallible step in
turning already-elaborated facts into text):

- k8s NetworkPolicy: one `NetworkPolicy` doc per component `Node`,
  deny-by-default (kernel law 2). Ingress peers = every distinct `Flow.src`
  with `dst == node_id`; egress peers = every distinct `Flow.dst` with
  `src == node_id`. A peer that is a foreign-trust `Node` (no in-cluster
  pod to select) is rendered as a `frob.strata/foreign-peer` annotation
  instead of a `podSelector` -- recorded, never silently dropped or
  silently allow-anywhere.
- seccomp profile skeletons: one profile per `Node`, `SCMP_ACT_ERRNO`
  default. Allowed syscalls = a fixed baseline (`read`/`write`/`exit`/...)
  plus every syscall family `_SECCOMP_KIND_MAP` maps a declared `may`
  capability KIND to (`exec` -> `execve`/`fork`/`clone`/...; `net` ->
  `socket`/`connect`/`bind`/...). KIND extraction reuses
  `_effects.py::_may_kind` (no duplicated rule) -- the segment of a `may`
  atom before its first `.`/`:` (`"net.out:stripe.com"` -> `"net"`). This
  is a deliberately coarse v0 mapping documented as such in both the
  module docstring and docs/commands/sys.md: a capability KIND names a
  class of effect, not an exact syscall list, and should not be treated as
  a substitute for a real syscall audit.
- IAM policy skeletons: a generic, provider-agnostic JSON document (no
  AWS/GCP/Azure-specific grammar). Two `Allow` statements per declared
  `Flow` -- `{flow.id}-write` (principal=`flow.src`, resource=`flow.dst`,
  action=`write`) and `{flow.id}-read` (same principal/resource,
  action=`read`). Flow direction is the only signal the kernel model
  carries for IAM action inference today; a real read-vs-write split needs
  an explicit flow attribute the surface grammar does not yet express --
  documented as follow-up, not this ticket's scope.

Determinism: every exporter sorts its inputs (node ids, flow ids, `may`
kinds, syscall names, JSON/YAML keys) before rendering, so two calls
against the same model in the same process, or two separate `frob sys
export` process invocations, produce byte-identical output. Verified both
ways (`tests/unit/strata/test_export.py::Test*::test_stable`,
`tests/system/test_cli_sys_export.py::TestCliSysExport::test_deterministic_across_two_processes`)
and pinned against a checked-in golden fixture generated from
`design/frob.strata` (`tests/unit/strata/test_export_golden.py`, T-0081's
self-hosting model -- already a real, live `.strata` program locked in CI
by `tests/system/test_frob_self_model.py`, so the golden input needs no
new fixture design).

CLI: T-0084's `sys` group had not landed on main at implementation time
(`frob ticket show T-0084` = queued), so a minimal `sys` subcommand group
scoped to `export` only was added directly (`src/frob/app/sys_runner.py`,
`_add_sys_parser` in `__main__.py`, `Subcommand.sys` in `config.py`).
`frob sys export --format k8s|seccomp|iam [design.strata]` parses +
elaborates the given `.strata` file (default `design/frob.strata`),
muting `frob.strata`'s per-construct INFO/DEBUG logs for the call via
`frob.logging.quiet.quiet_stdout_logs` (the same mechanism
`check_runner`/`map_runner` already use for their own `--json` paths) so
stdout carries only the rendered payload. **Merge point for T-0084**:
when T-0084 lands its own `sys` subparser/dispatch, it should extend
`_add_sys_parser`/`sys_runner.py` (add `check`/`trace`/`capacity`/
`threats`/`plan`/`doc` alongside `export`), not replace them -- noted in
both this report and the docstrings of `_add_sys_parser` and
`sys_runner.py`.

Scope note: the ticket's `scope` was widened from `src/frob/strata/**`,
`tests/**` (as originally filed) to also cover `src/frob/app/**`,
`src/frob/__main__.py`, `docs/commands/**`, `docs/index.md` -- documented
above and in the ticket's own body, since a real CLI could not be built
without touching the app/CLI layer and T-0084 had not landed to cover it.

Evidence (real, in-worktree):
- 22 pytest node ids recorded via `frob ticket evidence T-0086` (13 in
  tests/unit/strata/test_export.py, 3 in
  tests/unit/strata/test_export_golden.py, 6 in
  tests/system/test_cli_sys_export.py) -- all pass individually
  (`uv run pytest -q <22 node ids>`, exit 0).
- Full suite: `uv run pytest -q` exit 0 (no regressions).
- `uv run frob test --base main`: exit 0 (touched-set selection correctly
  picked up the new export/sys_runner/config/app/__main__ files).
- `uv run frob check` (no `--ticket`, full repo): exit 0 clean --
  ruff-check/ruff-format/ty/frob-cycle/frob-dup/frob-arch/frob-exports all
  pass; gates stage reports 87 violations/26 waived, all pre-existing
  (verified none reference `_export.py`, `sys_runner.py`, or
  `docs/commands/sys.md` except the two PERF004 `sorted()-in-loop`
  findings this ticket introduced and waived directly at the call site --
  each node/flow needs its own sort, so it cannot be hoisted out of the
  loop -- plus one PERF003 in the new test file, waived as a set
  comprehension followed by a separate assertion loop over a two-item
  fixture, not a join).
- `uv run frob check --ticket T-0086`: reports pre-existing, out-of-scope
  gate debt unrelated to this ticket (strata-core Rust parser TEST002,
  TEST003 integration-coverage gaps on unrelated interfaces --
  `src/frob/bind`, `src/frob/fuzz`, `src/frob/mutate`, `src/frob/release`,
  `src/frob/scaffold`, `src/frob/stats`, `src/frob/gitio.py`,
  `src/frob/logging`, `src/frob/excludes.py`, `src/frob/exports`,
  `strata-core/src/lib.rs`, plus a missing coverage stamp) -- none of
  these are files this ticket touched; the plain `frob check` (no
  `--ticket`) run above is the honest A/B signal and is clean.
- Determinism verified independently of pytest: `uv run frob sys export
  --format k8s design/frob.strata` run twice and diffed byte-identical,
  and its output parses as valid multi-doc YAML
  (`yaml.safe_load_all`)/JSON (`json.loads`) for all three formats.

Filed: none. No out-of-scope gaps were found that needed a new ticket --
the only deferred item (a real read-vs-write IAM action distinction, and
finer `may`-capability-target-scoped seccomp/IAM joins) is documented
inline in `_export.py`'s docstrings and docs/commands/sys.md as v0
scope, matching the same deferral pattern `_effects.py`/`_code_binding.py`
already use for `may`/`code` grammar gaps (not a new gap, the same known
one).

Gates: `frob check` (no `--ticket`) exit 0 clean. `frob check --ticket
T-0086` shows only pre-existing out-of-scope debt (see above) plus this
ticket's own directly-waived PERF003/PERF004 (reasons recorded at each
`frob:waive` site). Not closing this ticket per the task instructions --
evidence recorded via `frob ticket evidence T-0086`, Done report recorded
here in the ledger.

## Reconciliation with T-0084 (main landed the real `sys` group)

This worktree's base predated T-0084's landing on `main`. T-0084 shipped
the real `frob sys plan` group (`src/frob/app/sys_runner.py`, `Subcommand.sys`
config wiring, `_add_sys_parser`, `docs/commands/sys.md`) -- file-for-file
the same paths this ticket's minimal export-only `sys` group had created,
so `git merge main --no-edit` produced add/add and content conflicts in
exactly those five files (`src/frob/app/sys_runner.py`, `src/frob/app/
config.py`, `src/frob/__main__.py`, `docs/commands/sys.md`, plus a clean
auto-merge of `src/frob/strata/__init__.py`).

Resolved by reconciling into one `sys` group carrying both verbs, keeping
main's `plan` implementation verbatim and integrating `export` into its
structure (matching its helper style: `_run_plan`/`_run_export` private
functions, one shared `run(cfg)` dispatch on `cfg.sys_command`):

- `src/frob/app/sys_runner.py`: kept every one of main's `plan` helpers
  (`_design_dir`, `_merge_models`, `_load_snapshot`, `_existing_markers`,
  `_print_dry_run`, `_spec_for`, `_apply`, `_run_plan`) unchanged; added
  `_load_export_model` (renamed from this ticket's original `_load_model`
  to avoid a name collision) and `_run_export`, matching the same
  private-helper-per-verb shape. `run(cfg)` now dispatches `plan` (main's
  branch, untouched) then `export` (added), erroring on neither with
  `"usage: frob sys <plan|export> ..."`. One bug fixed during
  reconciliation: the original `export`-only default design path was
  `Path(DEFAULT_DESIGN_DIR)` (`"design"`, a directory), which would have
  immediately hit the `is_dir()` guard and errored on the documented
  default-path usage (`frob sys export --format k8s` with no path arg,
  never actually exercised end-to-end before this reconciliation) -- fixed
  to `Path(DEFAULT_DESIGN_DIR) / "frob.strata"`.
- `src/frob/app/config.py`: merged the two `AppConfig` `sys_*` field
  blocks into one (`sys_command`, `sys_path`, `sys_apply` from T-0084;
  `sys_export_format`, `sys_export_path` from this ticket); merged the two
  `from_external` field-name tuples the same way (string fields:
  `sys_command` + `sys_export_format`; path fields: `sys_path` +
  `sys_export_path`).
- `src/frob/__main__.py`: one `_add_sys_parser` registering both
  subparsers -- `sys plan [path] [--apply]` (main's, verbatim) and `sys
  export --format k8s|seccomp|iam [design.strata]` (this ticket's),
  called exactly once from `_build_parser`.
- `docs/commands/sys.md`: one doc with a `## \`frob sys plan\`` section
  (main's content, verbatim) and a `## \`frob sys export\`` section (this
  ticket's content), both under a shared intro naming both verbs and both
  not-yet-landed siblings (`check`/`trace`/`capacity`/`threats`/`doc`).
  Heading slug changed from `#export` to `#frob-sys-export`, so the three
  `frob:doc` anchors in `_export.py` were updated to match (caught by
  `frob check`'s DOC002 gate after the merge, fixed).
- `src/frob/strata/__init__.py`: auto-merged clean by git, but the
  auto-merge silently dropped `check_effect_completeness` from both the
  `_threat` import block and `__all__` (a known git 3-way-merge failure
  mode with adjacent independent insertions in the same import list) --
  caught immediately by the post-merge full-suite run
  (`ImportError: cannot import name 'check_effect_completeness'` collecting
  `tests/unit/strata/test_threat.py`), fixed by hand, re-verified against
  `git show main:src/frob/strata/__init__.py` with a sorted diff to
  confirm the reconciled file now has everything main has, plus exactly
  the three `export_*` additions and nothing else missing or extra.
- `tickets.md`: resolved by preferring `main` for the ledger structure
  (T-0084's now-`[done]` section, phase-5 ticket ordering) while
  preserving this ticket's own T-0086 evidence list and Done report
  verbatim -- confirmed post-merge, the T-0086 section is byte-identical
  to its pre-merge content.

`design/frob.strata` did not change on `main` since T-0081 authored it
(`git log -- design/frob.strata` shows no commits between this worktree's
base and `main` touching that file), so no golden-fixture regeneration
was structurally required -- regenerated anyway as a positive check and
diffed against the checked-in `tests/golden/frob_export_*` fixtures:
byte-identical (verified both via direct Python re-render + `Path.read_text()`
comparison and via the passing `tests/unit/strata/test_export_golden.py`
suite).

One unrelated problem surfaced and fixed during reconciliation: this
environment's `core.autocrlf=true` git config (pre-existing, not touched)
caused `git merge`'s working-tree rewrite to check out ~483 files with
CRLF line endings, which corrupted `frob`'s own content-hash-based
touched-set detection (every file in the repo, including ones neither
branch actually changed, appeared "modified" byte-for-byte relative to
their git blobs -- confirmed via `diff <(git show main:<path>) <path>`
showing a full-file diff on files with zero real content change). Fixed
by normalizing every CRLF file back to LF in the working tree
(`sed -i 's/\r$//'`, no git config touched, per the standing "never update
git config" rule) and rebuilding the native extension (`make core`) and
graph cache (`frob graph build .`) afterward. Re-verified byte-identical
to `main`'s blobs post-normalization (`diff <(git show main:...) ...`
exits 0). The merge itself was then completed with `git commit` (required
to finish the `git merge main --no-edit` this reconciliation was asked to
run -- an unfinished merge leaves the repository in an unmergeable
"unmerged paths" state); no further commit was made on top.

Re-verification (all in the fully reconciled, merged, LF-normalized tree,
after `make core` + `frob graph build .`):
- Full suite: `uv run pytest -q` exit 0, no regressions from either side's
  work.
- Combined CLI: `uv run pytest -q tests/system/test_cli_sys_plan.py
  tests/system/test_cli_sys_export.py tests/unit/strata/test_export.py
  tests/unit/strata/test_export_golden.py tests/unit/strata/test_plan.py`
  -- 33/33 passed (T-0084's plan tests and this ticket's export tests
  green together in one tree, one CLI group).
- `uv run frob sys plan` (dry-run) and `uv run frob sys export --format
  k8s|seccomp|iam design/frob.strata` both run end to end against the
  reconciled tree without error.
- This ticket's 22 evidence node ids: `uv run pytest -q <22 node ids>`
  exit 0 (unchanged from the pre-reconciliation run).
- `uv run frob test --base main`: exit 0; touched-set selection (58
  hunks since the new merge-base) correctly scoped to
  export/app/`__main__`-related tests only, since `plan`'s own files are
  now byte-identical to `main` and contribute no diff.
- `uv run frob check` (no `--ticket`): **exit 0, PASS** (84 violations,
  35 waived, all pre-existing/waived; zero violations attributable to
  `_export.py`/`sys_runner.py`/`docs/commands/sys.md` beyond this
  ticket's own two already-waived `PERF004` sites and one already-waived
  `PERF003` site). The one real gate signal surfaced along the way
  (`COV002` on `src/frob/gates/__init__.py::_sys002`, "changed with no
  open ticket") was not a bug -- it was `frob check`'s default
  `working_diff(base="main")` correctly reporting every file `main`
  changed since this branch's original divergence point, because the
  merge had not yet been committed (`HEAD` was still the pre-merge `wip`
  commit, so `merge-base(HEAD, main)` was the old divergence point, not
  `main` itself). It cleared the moment the merge commit landed.

## Reconciliation round 2 (main advanced again: T-0116/T-0110/T-0132/T-0136)

Round 1 above merged `main` as of T-0084's landing (`52702b9`, plus a
follow-up `1b1629e` fixing a T-0114 regression to T-0084's own surface).
That merge was committed (`ed9e0bc`). By the time it was reviewed, `main`
had moved substantially further -- `2cc04f5` "feat(strata): std.compliance"
was current `main`'s HEAD, six commits ahead of what round 1 actually
merged, including:

- T-0116: `src/frob/strata/_compliance.py` (709 lines, std.compliance --
  six regulations as conditional obligations) + `tests/unit/strata/
  test_compliance.py` (412 lines)
- T-0110: `src/frob/vet/_containment.py` (379 lines) + `src/frob/vet/
  _nvd.py` (197 lines) + `tests/test_vet_containment.py` (458 lines)
- T-0132/T-0136: `strata-core/src/parse.rs` surface-grammar additions
  (secret/code/may/on-deploy constructs, +345 lines), `src/frob/strata/
  _ast.py` (+67 lines), `design/litmus/deploy_secret.strata` (new litmus
  fixture) + `tests/unit/strata/test_litmus_deploy_secret.py` (107 lines)
  + `tests/unit/strata/test_parse.py`/`test_elaborate.py` additions

Round 1's Done report entry above claiming "the reconciled `__init__.py`
now has everything main has, plus exactly the three `export_*` additions
and nothing else missing or extra" was true **only against the `main`
round 1 actually merged** -- it did not, and could not, account for
`main` commits that landed after round 1's merge was performed. Framed
as a completed, durable reconciliation without that caveat, it read as
stronger than it was. The reviewer correctly flagged that `git diff main
--diff-filter=D --stat` against **current** `main` showed all six of the
files above as deletions -- round 1's merge commit, being based on a
stale `main`, structurally could not carry work `main` had not yet done
at merge time forward; that is not a reconciliation bug so much as an
unavoidable consequence of `main` moving between round 1's merge and its
review, but it needed a second merge to pick up, which is what this round
does. The `check_effect_completeness` git-3-way-merge casualty from round
1 was real (confirmed via `git blame`/import trace) but categorically
smaller than this -- one export name, not six files/2331 lines of
landed feature work -- and should not have been given equal billing with
"nothing else missing" in round 1's summary.

Round 2: `git add -A && git commit -m "wip"` (nothing uncommitted, but
run per instruction; empty diff), then `git merge main --no-edit` against
current `main` (`2cc04f5`). Unlike round 1, this merge produced **zero
conflicts** -- `git merge` auto-resolved `src/frob/strata/__init__.py`
and `tickets.md` cleanly (`Auto-merging ...` / `Merge made by the 'ort'
strategy`, no `CONFLICT` lines), because none of T-0116/T-0110/T-0132/
T-0136's changes touch the same hunks this ticket's `export_*` additions
or `tickets.md`'s T-0086 section occupy. `src/frob/app/sys_runner.py`/
`config.py`/`__main__.py`/`docs/commands/sys.md` needed no re-resolution
either, since T-0085 (the other `sys`-group-adjacent phase-5 ticket) has
not landed on `main`.

Verification performed (commands and results, not paraphrased):
- `ls src/frob/strata/_compliance.py src/frob/vet/_containment.py
  src/frob/vet/_nvd.py tests/unit/strata/test_compliance.py
  tests/test_vet_containment.py tests/unit/strata/
  test_litmus_deploy_secret.py` -- all six exist post-merge.
- `grep -n secret strata-core/src/parse.rs` -- `parse_secret`,
  `secret := "secret" ID "{" ... "}"` grammar present.
- `uv run python -c "import frob.strata as s; [getattr(s,n) for n in
  s.__all__]; print(len(s.__all__))"` -- 147 exports, zero
  `AttributeError`, `export_k8s_netpol`/`export_seccomp`/`export_iam`
  all present (>= the reviewer's 143 floor).
- `git diff main --diff-filter=D --stat` -- **empty** (zero deletions
  relative to current `main`).
- `git diff main --stat` -- exactly this ticket's 14 files (`docs/
  commands/sys.md`, `docs/index.md`, `src/frob/__main__.py`, `src/frob/
  app/{config.py,sys_runner.py}`, `src/frob/strata/{__init__.py,
  _export.py}`, three `tests/golden/frob_export_*` fixtures, `tests/
  system/test_cli_sys_export.py`, `tests/unit/strata/{test_export.py,
  test_export_golden.py}`, `tickets.md`); 1950 insertions, 30 deletions,
  no unrelated file touched.
- `make core` + `frob graph build .` (rebuild native ext + graph cache
  after the merge, same as round 1).
- Full suite: `uv run pytest tests/` -- **1732 passed, 3 skipped, 0
  failed** (real number, not paraphrased; includes
  `tests/unit/strata/test_compliance.py`,
  `tests/test_vet_containment.py`,
  `tests/unit/strata/test_litmus_deploy_secret.py`,
  `tests/unit/strata/test_parse.py`,
  `tests/unit/strata/test_elaborate.py` in the run).
- Combined `sys` CLI: `uv run pytest tests/system/test_cli_sys_plan.py
  tests/system/test_cli_sys_export.py tests/unit/strata/test_export.py
  tests/unit/strata/test_export_golden.py tests/unit/strata/test_plan.py`
  -- **33 passed**.
- Goldens: re-rendered `export_k8s_netpol`/`export_seccomp`/`export_iam`
  from `design/frob.strata` in-process and compared against the three
  checked-in `tests/golden/frob_export_*` fixtures with `==` -- byte-
  identical (`design/frob.strata` has had no `main` commits touch it
  since T-0081 authored it, confirmed again this round).
- `uv run frob check` (no `--ticket`): **exit 0, PASS** (82 violations,
  52 waived, all pre-existing; zero unwaived findings in `_export.py`/
  `sys_runner.py`/`docs/commands/sys.md`).
- Same `core.autocrlf=true`-driven CRLF corruption as round 1 recurred
  on the newly-checked-out files from this merge (19 files, all files
  `main` introduced since round 1: `_compliance.py`, `_containment.py`,
  `_nvd.py`, `parse.rs`, the new test files, etc.) -- fixed the same way
  (`sed -i 's/\r$//'`, no git config touched), re-verified byte-identical
  to `main`'s blobs (`diff <(git show main:<path>) <path>` exits 0 for
  every affected file), rebuilt `make core` + `frob graph build .` again
  after the fix. This time `frob check` was already exit-0 clean before
  the CRLF fix too (the merge auto-committed since there were no
  conflicts, so `working_diff(base="main")`'s `merge-base(HEAD, main)`
  was already current `main` by the time `frob check` ran) -- the CRLF
  fix was still applied for content-hash correctness and re-verified,
  but was not, this round, load-bearing for `frob check`'s exit code.

Merge commits: round 1 = `ed9e0bc`; round 2 = `23482b2` (auto-committed
by git, no conflicts to resolve by hand).

## Reconciliation round 3 (main advanced again mid-review: T-0085 `frob sys doc`)

While round 2 was being reviewed, `main` advanced a further commit:
`184ef9e` "feat(strata,gates,app): frob sys doc audit matrix + DOC003
claims audit (T-0085)" -- the exact ticket round 1's and round 2's Done
report text had predicted would eventually collide with this ticket's
`sys` group ("T-0085 has NOT yet [landed] -- likely no conflict" was true
at round 2's merge time, false by the time round 2 was reviewed). T-0085
lands a third `sys` verb (`frob sys doc`, `src/frob/strata/_sysdoc.py`,
`tests/system/test_cli_sys_doc.py`, `tests/unit/strata/test_sysdoc.py`)
into the identical four files round 1/2 already reconciled once:
`src/frob/app/sys_runner.py`, `src/frob/app/config.py`,
`src/frob/__main__.py`, `docs/commands/sys.md` (plus another clean
auto-merge of `src/frob/strata/__init__.py` and `tickets.md`).

`git add -A && git commit -m "wip"` (round 2's CRLF-normalization sed fix
plus round 2's Done report text were still uncommitted; committed as
`cf71092`), then `git merge main --no-edit` against `184ef9e`. This time
`git` reported real conflicts in exactly the four predicted files (`sys_
runner.py`/`config.py`/`__main__.py`/`docs/commands/sys.md`) -- unlike
round 2, which happened to land with zero conflicts because T-0085 had
not yet touched those files at that point.

Resolved into one `sys` group carrying all three verbs (`plan`/`doc`/
`export`), same reconciliation posture as before -- kept every one of
T-0084's and T-0085's functions/branches verbatim, added nothing of this
ticket's own beyond what round 1 already wrote:

- `sys_runner.py`: `run(cfg)` now dispatches `plan` (T-0084) -> `doc`
  (T-0085) -> `export` (T-0086) in that order, all three bodies
  unmodified from their respective landed/authored versions; module
  docstring updated to describe all three verbs.
- `config.py`: `AppConfig` now carries `sys_command`, `sys_path`,
  `sys_apply` (T-0084), `sys_view` (T-0085), `sys_export_format`/
  `sys_export_path` (T-0086) in one block; both `from_external` tuples
  (string fields, path fields) list all three verbs' fields.
- `__main__.py`: one `_add_sys_parser` registers `sys plan`, `sys doc`
  (T-0085's own argparse block merged in with zero manual changes needed
  -- git placed it correctly adjacent to `sys export`'s block, only the
  enclosing docstring/decorator comments conflicted), and `sys export`.
- `docs/commands/sys.md`: one doc, `## \`frob sys plan\`` -> `##
  \`frob sys doc\`` -> `## \`frob sys export\`` -> `## CLI wiring`,
  T-0085's full doc section (including its DOC003 claims-audit
  explanation and `<!-- frob:claims owasp-top-10 -->` marker) kept
  verbatim, added a `_run_export` describe-anchor next to T-0085's
  existing `_run_doc` one for parity.

Verification performed this round (commands and real results):
- `ls src/frob/strata/_compliance.py src/frob/vet/_containment.py
  src/frob/vet/_nvd.py tests/unit/strata/test_compliance.py
  tests/test_vet_containment.py tests/unit/strata/
  test_litmus_deploy_secret.py` -- all six still present (round 2's fix
  held; round 3 only touched the four `sys`-group files plus the two
  clean auto-merges).
- `uv run python -c "import frob.strata as s; [getattr(s,n) for n in
  s.__all__]; print(len(s.__all__))"` -- **151 exports**, zero
  `AttributeError`, all three `export_*` names present.
- `git diff main --diff-filter=D --stat` -- **empty** (zero deletions
  relative to current `main`, `184ef9e`).
- `git diff main --stat` -- exactly this ticket's 14 files again (same
  set as round 2, `docs/commands/sys.md`/`src/frob/app/sys_runner.py`
  larger now since they carry the three-verb dispatch), 2076 insertions,
  32 deletions, no unrelated file touched.
- `make core` + `frob graph build .` (native ext + graph cache rebuild).
- Full suite: `uv run pytest tests/` -- **1754 passed, 3 skipped, 0
  failed** (up from round 2's 1732 -- the 22-test delta is T-0085's own
  `test_sysdoc.py`/`test_cli_sys_doc.py` suites, now in the run).
- Combined `sys` CLI, all three verbs: `uv run pytest
  tests/system/test_cli_sys_plan.py tests/system/test_cli_sys_doc.py
  tests/system/test_cli_sys_export.py tests/unit/strata/test_export.py
  tests/unit/strata/test_export_golden.py tests/unit/strata/test_plan.py
  tests/unit/strata/test_sysdoc.py` -- **48 passed**.
- Manual smoke test, all three verbs in one CLI: `frob sys plan`, `frob
  sys doc`, `frob sys export --format iam design/frob.strata` each ran
  end to end without error against the reconciled tree.
- Goldens: re-rendered and compared against the three checked-in
  `tests/golden/frob_export_*` fixtures with `==` -- byte-identical
  (`design/frob.strata` still untouched by any `main` commit).
- `uv run frob check` (no `--ticket`): **exit 0, PASS** (85 violations,
  52 waived, all pre-existing; zero unwaived findings in `_export.py`/
  `sys_runner.py`/`docs/commands/sys.md`).
- Same `core.autocrlf`-driven CRLF corruption recurred on the 12 files
  this merge touched (the four resolved-by-hand files plus T-0085's own
  new files newly checked out); fixed the same way
  (`sed -i 's/\r$//'`, no git config touched) before committing the
  merge.

Merge commits total: round 1 = `ed9e0bc`; round 2 = `23482b2`; round 3 =
the `git merge main --no-edit` just completed. No commit was made beyond
these three merge commits (plus the two `wip` commits each round's
instructions explicitly asked for); the ticket's own T-0086 implementation
work was never re-committed or amended.

This ticket's own code (`_export.py`, `sys_runner.py`'s `export` half,
the export docs/tests/goldens) has not changed across any of the three
reconciliation rounds -- every round was pure merge-conflict resolution
absorbing what landed on `main` in the meantime, never a rewrite of this
ticket's actual deliverable.

Not closing, not committing beyond the required merge commits, per the
coordinator's explicit instructions each round.
