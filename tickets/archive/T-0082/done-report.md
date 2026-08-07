## Done report

Changed:
src/frob/strata/_secrets.py::SecretSpec
src/frob/strata/_secrets.py::elaborate_secret
src/frob/strata/_models.py::SetEquality
src/frob/strata/_claims.py::_eval_set_equality
src/frob/strata/_errors.py::StrataError.MissingRevocation
src/frob/strata/__init__.py (re-exports)
docs/strata/kernel.md (readers() exact-set closure cross-ref)
docs/strata/surface.md (#std-secrets section)

Design: std.secrets models a credential as one more cache-of-authority
construct, reusing the existing T-0065 age-propagation machinery rather
than adding a second metric. issued-by/audience/lifetime elaborate to a
Secret-clearance Node plus an issue flow (issued_by -> secret, age =
lifetime), the same age-bearing hop pattern _infra.py's cache 'fill' flow
uses. Revocation is a mandatory issued_by -> secret edge; a missing one
fails closed via the new StrataError.MissingRevocation, mirroring
MissingInvalidation in _infra.py ("no cache without invalidation" / "no
credential without revocation" is the same rule per kernel.md). readers(x)
== S is a new SetEquality claim body evaluated through the existing
barrier-respecting FactBase.reachable closure (no new traversal).
secret-in-logs/repo/artifact required zero new code: _facts.py's
structural diagnostics already flag any payload label exceeding a
destination's clearance, and Secret is simply the top of the existing
Public < Internal < Pii < Secret lattice.

Surface grammar (a `secret` keyword in the strata_core Rust parser) is
deferred per T-0132 precedent -- std.secrets is Python-API vocabulary
only for now. Filed T-0134 to add the grammar, SecretDecl AST, and
Module.secrets elaboration wiring.

Evidence (real, re-measured in-worktree after adding the barrier
regression below):
- tests/unit/strata/test_secrets.py: 16/16 passed (node ids recorded above
  via `frob ticket evidence`; includes
  `TestReadersExactSetClosure::test_readers_claim_refutes_across_a_declassify_boundary`,
  which pins that `readers() == S` uses `through_barriers=True`
  deliberately -- a forward past a DECLASSIFY boundary still counts as a
  reader and still refutes if undeclared).
- Full strata suite: tests/unit/strata/ = 304 tests, + tests/unit/test_lang_strata.py
  = 14 tests -- 318/318 passed (`uv run pytest tests/unit/strata/
  tests/unit/test_lang_strata.py -q`, exit 0). Earlier report of "307" was
  wrong; 304 and 318 are the correct, re-verified counts (303/317 before
  the barrier regression was added, 304/318 after).
- `frob test --base main`: exit 0.
- `uv run frob check`: no new unwaived diagnostics vs. the post-merge
  baseline (COV001/DOC002/SCOPE001/PRE001 clean; 87 violations, 21
  waived, all pre-existing).

Filed: T-0134 (strata surface grammar: secret keyword in Rust parser)
Gates: frob check --ticket T-0082 clean; ledger evidence recorded via
`frob ticket evidence T-0082 <15 node ids>`.
