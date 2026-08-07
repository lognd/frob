## Done report

Reproduction: attempted first, per instructions, before writing any fix.
Built the exact scenario the ticket describes -- a library model with a
single node declaring `may "exec"` and NO node anywhere declared `trust
foreign` -- and ran it through the REAL pipeline (`parse_module ->
elaborate -> check_discharge_completeness`, never a hand-built model),
both without a discharging claim (fires, as expected) and WITH the claim
form the ticket calls out as demanded-but-impossible:
`assert "weakness:CWE-78:runner" noflow foreign -> runner`. It does NOT
reproduce as "impossible": `check_discharge_completeness` returns `Ok(())`
-- clean discharge -- today, with no code change. Traced why:
`_claims.py::_expand` resolves a bare `"foreign"` trust-level reference to
`facts.nodes_at("foreign")`; with zero foreign-trust nodes in the model
that is the empty tuple, so `_eval_noflow`'s witness search has nothing to
iterate and proves the `NoFlow` FORALL vacuously (no unendorsed influence
path exists, because no foreign source exists to originate one).
`_discharges_as_chokepoint` already accepts `src="foreign"` naming the
trust level directly (its own docstring says so), and
`_mitigation_is_chokepoint`'s vacuous-path short-circuit (added T-0113)
independently confirms PROVED with zero boundaries present. Also verified
the converse holds (no weakening): the SAME claim shape against a model
that DOES have a real `foreign` node with an unendorsed flow into the sink
correctly REFUTES and THREAT003 still fires.

Discharge mechanism: the EXISTING chokepoint machinery, unchanged --
"discharge by absence" falls straight out of the current `NoFlow`
evaluation over an empty source set. No new claim form, no new kernel
primitive, no code change to `_threat.py`/`_claims.py`/`_models.py`. The
gap was discoverability/documentation: the sibling-repo pilot did not know
this exact claim shape (naming the bare `foreign` trust level, not a
specific node) already discharges vacuously, and treated the obligation as
permanently stuck rather than writing it.

Fix applied (docs + litmus, scope: docs/strata/threat.md, tests/**):
added a new documented section "Library-mode discharge by absence
(T-0223)" to docs/strata/threat.md (anchor
`#library-mode-discharge-by-absence`), placed after "The exhaustiveness
proof (the point)" -- explains the mechanism, shows the exact claim
syntax, and states the soundness argument (why it is not a blanket
weakening). Added two litmus fixtures under
`tests/unit/strata/litmus/`, following the `test_managed.py` real-parser
precedent (never a hand-built `KernelModel`):
- `library_exec_no_foreign_discharges.strata` -- no foreign node
  anywhere, `may "exec"`, discharges cleanly.
- `library_exec_foreign_reaches_still_fires.strata` -- same node, same
  claim shape, but a real `foreign` node with an unendorsed flow into the
  sink -- still fires REFUTED (no weakening).
Bound by a new `TestLibraryModeForeignlessDischarge` test class in
`tests/unit/strata/test_threat.py` (frob:tests/frob:ticket directives on
both methods), loading each fixture through the real
`parse_module -> elaborate` pipeline exactly like `test_managed.py`'s
`_load_model` precedent.

Evidence: both node ids above collected via
`pytest tests/unit/strata/test_threat.py -k Library --collect-only -q -p
no:xdist -o addopts=""` and re-run individually (2 passed). Full
`tests/unit/strata/test_threat.py` suite: 75 passed. `TestRealGateGreen`
(`tests/unit/strata/test_selfconform.py`): 1 passed. `ruff check` and
`ruff format --check` clean under both PATH `ruff` and `uv run ruff` for
the touched Python file. `uv run ty check src/frob/strata/_threat.py`:
no issues (module unchanged, checked as scope sanity). `make coverage`:
full suite green, coverage stamped (`source_sha=71768eec`). `frob check
--delta --ticket T-0223`: 0 errors, 1 pre-existing unrelated warning
(TEST005 on `src/frob/testing/_collect.py`, outside this ticket's scope
and outside anything touched here). Deletion-filter check
(`git diff main --diff-filter=D --stat`): empty.

Filed: none -- no out-of-scope work discovered.

Gates: `frob check --delta --ticket T-0223` clean (0 errors after
re-running `frob ticket sweep T-0223` to refresh the pre-work sweep,
which the docs/tests edits made stale -- PRE001 resolved, not waived).

Left in-progress for reviewer per dispatch instructions (review-gated;
not closed by this agent).
