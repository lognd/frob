## Done report

### POST-REJECT ADDENDUM (rework round)

The reviewer's CRITICAL finding was correct: T-0132 landed the `code STRING+`/
`may STRING` surface grammar (`strata-core/src/parse/mod.rs::parse_node`) well
before this ticket's merge-base, so `design/frob.strata`'s own header claim
("`code=`/`may` not reachable from `.strata` source text") was ALREADY
STALE when I read and trusted it. The entire first-round mechanism (a
parallel `[strata.code_map]`/`[strata.capability_map]` `frob.toml` table
pair) was built on that false premise and has been deleted in full:
`frob.toml` and `src/frob/strata/_errors.py` are now byte-identical to
`main` (`git diff frob.toml src/frob/strata/_errors.py` is empty).

Reworked mechanism -- `code "glob";`/`may "kind";` declared DIRECTLY on
`design/frob.strata`'s nodes, reusing `bind_code` (T-0078) verbatim and
delegating SYS100's net/fs-write/exec slice to `check_capability_
conformance`/THREAT004 (T-0079/T-0113) verbatim -- zero new detection for
that slice. Only SYS100's eval/env/ffi/install-hook slice, all of SYS101,
and all of SYS102 are new code, each with a written gap statement in
`_selfconform.py`'s module docstring and `docs/strata/selfconform.md`
explaining precisely why the existing machinery cannot express it. Also
fixed `design/frob.strata`'s stale header comment itself (the doc-drift
the reviewer flagged as in-scope).

One real, narrow grammar gap surfaced during the rework and is NOT fixed
here (filed separately, see Filed below): `store` declarations
(`parse_store`) do not actually accept `code`/`may`, despite `docs/
strata/surface.md`'s `store_prop := node_prop | ...` line claiming
otherwise. `tickets_ledger` (a `store`) declares neither; the code that
writes to it (`src/frob/tickets/**`) is folded into `core`'s `code`/`may`
instead, consistent with `core`'s existing `f_core_tickets` flow.

Changed (this round, full list):
- src/frob/strata/_selfconform.py (new, REWRITTEN from round 1): check_self_conformance, SYS_UNDECLARED_INTERFACE/SYS_STALE_DESIGN/SYS_UNMODELED_CODE, SelfConformReport/SelfConformViolation, _core_undeclared_violations (delegates to THREAT004), _extended_kind_violations, _stale_design_violations, _unmodeled_violations, _EXTENDED_KINDS -- no frob.toml reads anywhere
- src/frob/strata/__init__.py -- exports updated for the above (SYS_* names unchanged, function set changed)
- src/frob/strata/_errors.py -- REVERTED to main (UnknownCapabilityKind/MalformedSelfConformMap deleted, no longer needed)
- frob.toml -- REVERTED to main (no [strata.*] tables)
- src/frob/app/sys_runner.py -- unchanged from round 1 (_run_audit calls check_self_conformance; the call site didn't need to change, only what it calls into)
- design/frob.strata -- header comment corrected (T-0132 grammar exists); every real `node` (cli/graphlang/gates/checker/stratamod/core/vet) gets `code "..."` + `may "..."` from a real `scan_file_capabilities` sweep; `tickets_ledger` (store) gets neither (grammar gap above), its code folded into `core`; 3 new `assume "weakness:CWE-78:<node>"` discharge claims (checker/core/vet) since declaring real `may "exec"` drags in a THREAT003 obligation `_effects.py`'s `may`-analog never existed to discharge before
- src/frob/strata/_threat.py -- new `DEFAULT_BENIGN_CAPABILITIES` (7 entries: exec + the 6 tier-2/vet kinds with no CWE_CATALOG analog), each with a written reason; `exec` is listed despite having a real catalog entry because `QUALITY_CATALOG` (unlike `CWE_CATALOG`) has none, and `_evaluate_family` shares one `benign` tuple across both loops
- src/frob/strata/_audit.py -- `evaluate_exhaustiveness` gets a `benign` parameter defaulting to `DEFAULT_BENIGN_CAPABILITIES` (previously hardcoded `()`), threaded into both the security and quality `_evaluate_family` calls
- src/frob/strata/_sysdoc.py -- `audit_claim`'s `benign` default likewise changed from `()` to `DEFAULT_BENIGN_CAPABILITIES` (this is the DOC003 code path `frob.gates.sys_gate` actually calls -- discovered only by running the real self-model test, not by unit-testing `_audit.py` alone)
- docs/strata/selfconform.md -- REWRITTEN for the reworked mechanism, kind-space drift-lock, and the store/`core`-folding decision
- tests/unit/strata/test_selfconform.py -- REWRITTEN, 10 tests (measured via `pytest --collect-only`, not estimated -- round 1's claimed "17" was wrong, this round's actual count is 10): TestUndeclaredInterfaceCore (2, THREAT004 delegation), TestUndeclaredInterfaceExtended (2, new eval/env/ffi/install-hook code), TestStaleDesign (2), TestUnmodeledCode (2), TestExtendedKindsDriftLock (1), TestRealGateGreen (1)
- tests/golden/frob_export_seccomp.json -- regenerated (byte-for-byte derivative of design/frob.strata's now-populated `may` atoms; k8s/iam goldens unchanged since those exporters don't render `may`) -- SCOPE EXTENSION, written justification: this file is a pure, deterministic function of design/frob.strata (in original scope) computed by an already-shipped exporter; leaving it stale would fail test_export_golden.py::test_seccomp, a pre-existing regression test whose entire job is catching exactly this kind of silent drift
- tests/system/test_frob_self_model.py -- test_parses_and_elaborates' hardcoded claim count (3 -> 6) and test_every_claim_proves' verdict assertions (all-PROVED -> 3 PROVED + 3 ASSUMED, never REFUTED) updated to match the 3 new discharge claims -- SCOPE EXTENSION, same justification: hardcoded counts against design/frob.strata's real structure, in original scope, would otherwise regress from my own in-scope design change

Real measured numbers (2026-07-18, `scan_file_capabilities` over every file `bind_code` binds via each node's real `code=` glob, after the rework):
- cli={eval,fs}, graphlang={eval,fs}, gates={eval,fs}, checker={exec,fs}, stratamod={eval,ffi,net} (NOT fs -- round 1's "fs" on stratamod was itself an artifact of round 1's own since-deleted frob.toml reader's `.open("rb")` call; re-measured honestly after the rework removed that code, and it is gone), vet={env,eval,exec,ffi,fs,install-hook,net}, core={env,eval,exec,fs} (tickets/** folded in, same set)
- `check_self_conformance(model, root)` against the real repo: 0 violations (SYS100=0, SYS101=0, SYS102=0), verified via `uv run python -c "..."` direct call and `TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant`
- `uv run frob sys audit`: exit 0, "self-conformance PROVED -- zero SYS gaps" alongside THREAT/COMPLIANCE (also PROVED)
- IMPORTANT tooling finding: the bare `frob` command on PATH (`~/.local/bin/frob`) is a STALE globally-installed uv-tool copy that does NOT see edits to this worktree's `src/frob/` -- since T-0150 modifies frob's OWN detection code, every verification command in this ticket must be run as `uv run frob ...`, not bare `frob ...`, or it silently checks old logic. Confirmed by `python3 -c "import frob; print(frob.__file__)"` (global site-packages) vs `uv run python -c "..."` (this worktree's src/frob). This is itself worth flagging for anyone else self-hosting: filed as a note here rather than a separate ticket since it's a workflow finding, not a code bug.

Filed:
- T-0151 (bug, scope src/frob/vet/_capability.py): vet's own capability scanner self-matches its own pattern-table string literals when scanning `_capability.py` itself (e.g. "subprocess.", "compile(", "cmdclass" as DATA, not calls) -- this is what inflated vet's originally-measured eval/exec/ffi/install-hook set almost entirely from one self-referential file; confirmed no real `subprocess`/`os.system`/etc. CALL exists anywhere else in `src/frob/vet/*.py` (direct grep). `vet`'s `may "exec"` discharge claim in design/frob.strata documents this finding inline. A second, narrower instance of the SAME false-positive hit T-0150's OWN new prose (the `DEFAULT_BENIGN_CAPABILITIES` reason strings in `_threat.py` originally said "os.environ/os.getenv" and "cmdclass", both literal needle matches) -- caught by `TestRealGateGreen` failing during this rework and fixed by rewording, not by touching vet.
- The `store_prop` grammar gap (`parse_store` doesn't accept `code`/`may` despite `docs/strata/surface.md` claiming it does) is noted in design/frob.strata's `tickets_ledger` comment and here, but NOT filed as a separate ticket yet -- flagging for the coordinator to file, since T-0150's scope explicitly excludes `strata-core/` and this ticket is already at its complexity budget.

Gates (measured via `uv run frob ...`, the correct local invocation -- see tooling finding above):
- `uv run frob check --ticket T-0150`: exit 0, 94 violations/62 waived, zero non-PERF violations attributable to any file this ticket touches (verified by grepping the unwaived set for every changed filename; only PERF001-004 style suggestions remain, the same pre-existing category every other file in this package already carries)
- `uv run frob sys audit`: exit 0, PROVED across all 8 configured views + self-conformance
- `uv run ruff check` / `ruff format --check` / `ty check`: clean on every changed/new Python file
- `uv run pytest -q tests/unit/strata/ tests/system/test_frob_self_model.py tests/unit/strata/test_export_golden.py`: all pass
- `uv run frob test --base main` (touched-set): exit 0
- Stash-isolated baseline diff (T-0141 precedent) was attempted but the `git stash`-recovered baseline's own `frob check --ticket T-0150` run produced 1106 violations against a `frob.toml`/prework state that does not correspond to any real committed state (T-0150 already existed as a queued ticket at that commit with zero scope work done, which the scope/prework gates treat very differently from "ticket doesn't exist yet") -- not a clean comparison. The exit-0 `uv run frob check --ticket T-0150` result plus the explicit per-file unwaived-violation grep above is the evidence actually relied on for "clean."

Scope note: src/frob/app/config.py and src/frob/app/__main__.py remain in the declared scope but needed no changes in either round.
