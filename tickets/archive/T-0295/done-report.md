## Done report

Landed via merge c8d8107. The initial agent narrative below described a
5-file slice, but the delivered work (worktree HEAD 187947a) drove ALL of
src/frob/strata/** long-functions to zero across ~29 files -- verified on
merged main: `frob arch . | grep -c 'long-function.*src/frob/strata'` = 0
(repo total 158 -> 84). Reviewer APPROVE (independent execution): behavior
preservation traced through the security-critical exhaustiveness/crash/
compliance/lint/reachability paths, every touched frob: directive confirmed
still bound to its intended public symbol (no T-0297 wrong-symbol rebind),
all 6 ty-regression repairs verified faithful type-narrowing (not logic
changes), public API unchanged, `pytest tests/unit/strata tests/system`,
`TestRealGateGreen`, and litmus all green, COV001 clean. Cargo direct-invoke
build failure is the known worktree-natives interpreter artifact, not a
regression (`make core` + pytest exercise the natives end-to-end and pass).

Investigated/implemented 2026-07-19 (worktree agent-a2f9677333642e99d, commits ec02bb7,
4e131bf): scoped to 5 files only (_export.py, _facts.py, _host.py, _host_isolation.py,
_infra.py) per dispatch -- the other strata files in the original ~74-warning survey
(_atomic/_audit/_breach/_claims/_code_binding/_compliance/_crash/_design_load/_effects/
_elaborate/_krb/_lint/_packs/_pii/_plan/_policy/_report/_scenarios/_secrets/_selfconform/
_sysdoc/_threat/_waive) were concurrently claimed by sibling forks in this SAME shared
worktree and are NOT covered by this ticket -- do not close this ticket as "strata done"
without confirming those land too (check for other T-029x tickets touching those paths).

BEFORE (this ticket's 5 files only, `frob arch .` grep): _export.py 1, _facts.py 2,
_host.py 1, _host_isolation.py 6, _infra.py 4 = 14 long-function warnings.
AFTER: 0, verified via `uv run frob arch .` grepped for these 5 filenames (whole-repo
scan; NOTE a single-file `frob arch <path>` invocation returns empty regardless of
content -- that mode appears broken/unimplemented, do not trust it, always scan a
directory or `.`).

Method: behavior-preserving extraction of private (_underscore) helpers only, no
public API changes, no proof/gap/reachability/waiver semantic changes, early-return
and emission order preserved throughout. Heaviest in _host_isolation.py (HOST001/
HOST002 movement-impossibility proofs): _lateral_pair_violations and
_vertical_user_violations split into per-sub-target builders
(_shared_writable_path_violations/_shared_socket_violations/_shared_group_violation;
_setuid_violations/_sudoers_violation/_root_unit_writable_violations/
_higher_trust_write_violations), each appended/extended in the SAME order the
original inline code emitted them; _movement_flows_for_pair split into
_writable_path_movement_flows/_shared_port_movement_flows threading the same `seq`
counter; evaluate_lateral_isolation/host_movement_flows/evaluate_host_isolation_waived
each got a small helper for their pair-iteration loop, same iteration order.

COV001 directive-displacement hazard (flagged in dispatch as the #1 watch item) DID
fire once: inserting `_elaborate_simple_infra_nodes` directly above `elaborate_infra`
in _infra.py pulled the `# frob:doc docs/strata/surface.md#stdinfra` directive off
the public `elaborate_infra` it was documenting. Caught by running
`uv run frob check --only coverage` after the extraction pass (as directed) --
1 COV001 error. Fixed by moving the directive back down onto `elaborate_infra`
directly; re-ran coverage check, 0 errors. Also lost two Result element types across
the same _infra.py split (_cache_bound/_cdn_age had drifted to `object`/`object | None`
instead of `Quantity`/`Quantity | None`, and _cdn_node_and_fill_flow's `provider_trust`
param lost its `str | None -> str` narrowing when pulled into a separate function from
the None-check) -- caught by `uv run ty check`, fixed by tightening the three
signatures and threading the narrowed `decl.provider_trust` value explicitly.

VERIFIED (all commands run and output read, not estimated): `uv run frob arch .`
zero long-function for the 5 files; `uv run frob check --only coverage` -- 0 errors,
0 warnings (COV001=0); `uv run ruff check` and `uv run ruff format --check` on the 5
files -- all pass, confirmed again under the PATH `ruff` binary per playbook section 12;
`uv run ty check` on the 5 files -- 0 diagnostics; `uv run pytest tests/unit/strata -k
"export or facts or host or infra" -q` -- all pass; `uv run pytest tests/unit/strata -q
--deselect tests/unit/strata/test_audit.py` -- all pass (full strata unit suite minus
the audit-dependent tests, see caveat below).

CAVEAT -- NOT this ticket's fault, NOT fixed here: `uv run pytest tests/unit/strata
tests/system -q` (the dispatch's directed full command) currently fails 3 tests
(`test_cli_sys_audit.py::test_clean_model_exits_zero`,
`test_cli_sys_audit.py::test_undischarged_capability_exits_nonzero_with_named_gap`,
`test_system.py::test_sys_audit_hardened_waived_two_user_model_proved`) with a
`NameError: name '_final_gaps_with_stale' is not defined` inside `src/frob/strata/
_audit.py`. `_audit.py` is OUTSIDE this ticket's touched set (not in the 5-file list
above) and was mid-edit by a concurrent sibling fork sharing this worktree at the time
-- confirmed via `git status`/`git diff` showing `_audit.py` modified by that other
agent, not by this ticket's commits. Left as-is; whoever lands `_audit.py`'s
in-progress arch split needs to fix this NameError before that work is considered done.
`TestRealGateGreen`/`litmus`-marked tests were not separately re-run beyond the above
(`-k` selection above did not target them explicitly; the full `tests/unit/strata`
run above, minus test_audit.py, covers `test_selfconform.py`'s
`TestRealGateGreen` collection and it passed).

`git diff main --diff-filter=D --stat` for the 5 touched files: empty (no deletions).
No Cargo.lock churn (rust untouched, out of scope). Ticket left open (state:
in-review) per playbook section 11 -- not closed by this agent.
