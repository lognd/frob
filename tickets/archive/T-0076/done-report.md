## Done report

Built breach scenarios in `src/frob/strata/_breach.py`, following the
`_crash.py` (T-0074) / `_atomic.py` (T-0075) kernel-engine pattern:
Breach(X) auto-generates a `SetTrust(node_id, level="foreign")` scenario
per node declaring `on breach { detect; revoke; credential_age?;
recovers_via? }`, reusing `_scenarios.py::evaluate_scenarios` rather than
a parallel evaluator. Three joined checks: (1) blast radius via the
existing `FactBase.reachable(node_id, through_barriers=True)` kernel
primitive -- through barriers, since a compromised identity cannot be
trusted to have respected a boundary predicate; (2) containment bounds,
fail-closed (`StrataError.IncompatibleContainmentBound`) when
`detect > revoke` or `credential_age > revoke`; (3) recovery-path
independence -- a new `Independent` claim body
(`ClaimBody = NoFlow | Reach | BoundClaim | Independent`) implementing
the kernel's `independent(p, n)` primitive from
`docs/strata/kernel.md`'s claim-forms table, evaluated by
`_claims.py::_eval_independent` and auto-attached to the breach
scenario's claims whenever `recovers_via` is declared. `avoid`'s own
closure excludes itself before comparing, since a recovery path is
expected to terminate at the node it recovers.

STRIDE: breach models Spoofing/Elevation-of-Privilege containment. The
`SetTrust(..., "foreign")` rewrite is the compromise; blast radius uses
`through_barriers=True` because a compromised actor cannot be assumed to
have respected the boundaries that gated it (an Information-Disclosure
concern bounded by `detect`/`revoke`/`credential_age`); recovery-path
independence fails closed on any node shared between the recovery path
and the compromise's own reach closure, guarding against a Denial-of-
Service of the recovery mechanism itself (the recovery path routing
through infrastructure the attacker can also reach).

Deferred: v0's surface grammar has no `on breach { ... }` construct yet
(same T-0118-class gap T-0074/T-0075 deferred) -- `BreachContract` is a
kernel-only data model in `_models.py`; a caller builds `KernelModel`/
`Node.breach` directly. Parser/elaborator wiring is out of scope here.

Verification: `uv run pytest tests/unit/strata` = 239 passed (222
baseline + 17 new in `test_breach.py`). `frob check` exit 0. `frob check
--json --only gates` = 109 diagnostics, unchanged from baseline (101
unwaived + 8 waived, no new rule ids) -- two transient PERF004 trips
from `_eval_independent`/`_compute_blast_radii` were eliminated by
hoisting `sorted()` calls above every loop token in each function
(the gate's loop-gate check is function-scoped, not lexically-nested),
not waived. `frob test --base main` selected 47 touched-set tests, exit
0. Filed T-0122 (out of scope): `frob check --ticket <ID>` silently
exits 1 with no diagnostic output, reproduced identically on the
already-closed, evidenced T-0075 -- pre-existing, unrelated to this
change.
