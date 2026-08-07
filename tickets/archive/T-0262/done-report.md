## Done report

Changed:
- `strata-core/src/parse/mod.rs::parse_node` -- new node clauses `realm "NAME"`,
  `kdc`, `spn "SPN"`+, `delegation none|constrained|rbcd|unconstrained
  [target "SPN"]*`, `trusts IDENT [direction "one-way"|"two-way"]
  [transitive]`+, emitted as `krb_realm`/`krb_is_kdc`/`krb_spns`/
  `krb_delegation`/`krb_delegation_targets`/`krb_trusts` JSON fields.
- `strata-core/src/parse/mod.rs::parse_flow` -- new flow clause
  `authenticates_via tgt|st`, desugars to a `krb_ticket=<kind>` attr.
- `src/frob/strata/_ast.py::NodeDecl` -- new `krb_realm`/`krb_is_kdc`/
  `krb_spns`/`krb_delegation`/`krb_delegation_targets`/`krb_trusts` fields.
- `src/frob/strata/_ast.py::KrbTrustDecl` (new) -- typed
  target/direction/transitive AST model for a `trusts` clause.
- `src/frob/strata/_krb.py` (new module) -- `KrbDelegationKind`,
  `KrbTrust`, `KrbManifest`, `krb_attrs` (desugar), `krb_manifest_for`
  (node read-back), `krb_trust_flows` (domain-trust `Flow` synthesis),
  `flow_authenticates_via` (flow read-back).
- `src/frob/strata/_elaborate.py::_elaborate_node` -- calls `krb_attrs`
  the same way `host_attrs` is called.
- `src/frob/strata/_elaborate.py::_elaborate_module` -- calls
  `krb_trust_flows(elaborated_nodes)` and folds the result into
  `extra_flows` so domain trusts join the reachability closure.
- `src/frob/strata/_elaborate.py::_validate_krb` (new) -- fails closed on
  an unknown `delegation` kind, a `target` clause under a non-constrained
  delegation kind, or a `trusts` clause naming an undeclared node.
- `src/frob/strata/__init__.py` -- exports `KrbTrustDecl`,
  `KrbDelegationKind`, `KrbManifest`, `KrbTrust`, `krb_manifest_for`,
  `krb_trust_flows`, `flow_authenticates_via`.
- `editors/vscode-strata/syntaxes/strata.tmLanguage.json` -- added
  `authenticates_via`, `delegation`, `direction`, `kdc`, `realm`, `spn`,
  `target`, `transitive`, `trusts` to the clause-keywords pattern
  (`ticket` was already present).
- `docs/strata/krb.md` (new) -- full vocabulary, elaboration, platform-
  neutrality, and scope-boundary documentation.
- `tests/unit/strata/test_krb.py` (new), `tests/unit/strata/
  test_litmus_krb.py` (new), `tests/unit/strata/litmus/
  krb_declared.strata` (new), `tests/unit/strata/litmus/
  krb_undeclared.strata` (new).
- `CHANGELOG.md` -- new `[0.9.0] - unreleased` section (public-API bump,
  REL001) with the T-0262 entry.
- `pyproject.toml`, `.frob-release.json`, `strata-core/Cargo.lock`,
  `frob-core/Cargo.lock`, `uv.lock` -- version bump 0.8.0 -> 0.9.0 and
  `frob release stamp` artifact (all four consequences of the version
  bump, not independent edits).
- `tickets.md` -- this Done report; T-0262's `scope` list widened to
  include `CHANGELOG.md`/`pyproject.toml`/`.frob-release.json`/
  `strata-core/Cargo.lock`/`frob-core/Cargo.lock`/`uv.lock` (all fired
  SCOPE001 as release-mechanics files outside the original glob list;
  extended per the gate's own remedy message, not silently worked
  around), followed by a re-run of `frob ticket sweep T-0262`.

Scope cuts disclosed (see docs/strata/krb.md#scope-boundary):
- No `store`-level std.krb clauses (`std.host` extended `runs_as`/`unit`/
  `owns`/`listens` to `parse_store` too; this ticket adds `realm`/`kdc`/
  `spn`/`delegation`/`trusts` to `parse_node` only). A domain-joined
  datastore cannot declare std.krb facts today -- follow-up work, not
  filed as a separate ticket in this pass (small, well-precedented).
- No delegation-abuse obligations (explicitly T-0263's scope per the
  ticket body).
- No generator/deploy-time mechanism (kinit, keytab provisioning,
  gMSA install) -- mirrors `std.host`'s own manifest-only cut.

Version: bumped `pyproject.toml` 0.8.0 -> 0.9.0 (new `[0.9.0] -
unreleased` CHANGELOG section, not folded into the existing 0.8.0
section) because `frob release check` reported `since 0.8.0: minor
change -> need >= 0.9.0` for the new `frob.strata._krb`/`_ast.KrbTrustDecl`
public surface; `frob release stamp` run afterward (`.frob-release.json`
now records 886 public symbols at 0.9.0).

Evidence (fresh `pytest --collect-only -q -o addopts=""` pass, all 15
ids confirmed collected and passing):
- tests/unit/test_strata_tmlanguage.py::test_clause_keywords_covered_by_grammar
- tests/unit/strata/test_krb.py::TestKrbAttrs::test_desugars
- tests/unit/strata/test_krb.py::TestKrbAttrs::test_no_clauses_desugars_to_empty
- tests/unit/strata/test_krb.py::TestKrbManifest::test_reads
- tests/unit/strata/test_krb.py::TestKrbManifest::test_node_with_no_krb_attrs_returns_none
- tests/unit/strata/test_krb.py::TestKrbTrustFlows::test_sync
- tests/unit/strata/test_krb.py::TestKrbTrustFlows::test_two_way_synthesizes_reverse_edge_too
- tests/unit/strata/test_krb.py::TestKrbTrustFlows::test_no_trusts_synthesizes_nothing
- tests/unit/strata/test_krb.py::TestFlowAuthVia::test_read
- tests/unit/strata/test_krb.py::TestFlowAuthVia::test_flow_with_no_krb_attrs_returns_none
- tests/unit/strata/test_litmus_krb.py::TestKrbDeclaredLitmus::test_declared_manifest_round_trips_every_field
- tests/unit/strata/test_litmus_krb.py::TestKrbDeclaredLitmus::test_two_way_transitive_trust_synthesizes_both_directions
- tests/unit/strata/test_litmus_krb.py::TestKrbDeclaredLitmus::test_flow_authenticates_via_reads_ticket_kind
- tests/unit/strata/test_litmus_krb.py::TestKrbDeclaredLitmus::test_kdc_node_manifest_has_no_delegation
- tests/unit/strata/test_litmus_krb.py::TestKrbUndeclaredLitmus::test_undeclared_node_has_no_manifest

Also ran (green, not attached as ticket evidence since it's the repo's
existing self-conformance gate check, not new coverage this ticket
added): `tests/unit/strata/test_selfconform.py::TestRealGateGreen`.

Filed: none -- the store-level std.krb cut above is disclosed rather
than filed as a new ticket (small precedented follow-up); no other
out-of-scope work was found.

Gates:
- `uv run frob check --ticket T-0262` (after the scope widening and a
  fresh `frob ticket sweep T-0262`): 0 errors, 5 warnings, 27 waived.
- `uv run frob check` (full, unscoped): 0 errors, 5 warnings, 27 waived,
  0 DRIFT002, `ruff-check` no issues, `ruff-format` all files formatted,
  `ty` no issues.
- Full `uv run pytest` (repo-wide, `-q`): all green except one
  PRE-EXISTING, unrelated flaky test
  (`tests/test_vet.py::TestSourceLocation::test_locate_pypi_source_missing_returns_none`,
  a `FileNotFoundError` racing a real `~/.cache/uv` temp dir scan on
  this machine -- reran in isolation and it passed; not touched by this
  ticket's diff).
- `git diff main --diff-filter=D --stat`: empty.

Ticket left OPEN (not closed) for reviewer per the review-gated flow --
`frob ticket close T-0262` was intentionally not run.

## Round 2 (reviewer REJECT, two findings addressed)

Reviewer verified delegation-type distinctness, one-way directionality,
two-way synthesis, `authenticates_via` composition, and platform-
neutrality sound -- untouched this round. Merged `main` first (fast-
forward-mergeable, `tickets.md` auto-merged cleanly; `pyproject.toml`
stayed at 0.9.0, no conflict since upstream had not independently bumped
past 0.8.0); reran `make core`-equivalent (`maturin develop` for both
crates) since `main` had moved.

**Issue 1 (BLOCKING -- transitive trust flag is dead metadata): FIX PATH
= option (b), disclosed, NOT fixed in this ticket.** Reproduced the
reviewer's exact scenario (`a --trusts--> b --trusts--> c`, all one-way,
all non-transitive): `FactBase.reachable('a', through_barriers=True)`
does report `c` reachable, confirming the finding. Investigated option
(a) first: correctly stopping a non-transitive edge from chaining
requires `strata_core::reachable`'s `Edge` type (`strata-core/src/
lib.rs`) to gain a terminal-edge concept -- discover a node via a
terminal edge but do not enqueue it into the BFS frontier for further
expansion. That is a change to the SHARED kernel primitive every
`noflow`/`reach` claim in the whole system walks (not krb-specific), and
`strata-core/src/lib.rs` is outside T-0262's declared scope
(`strata-core/src/parse.rs` only) -- bundling a shared-kernel BFS change
into this ticket's vocabulary work would be exactly the kind of
undisclosed scope creep the playbook warns against, and the blast radius
(every existing claim, `test_kernel_properties.py`'s hypothesis oracle)
is too wide to responsibly land inside a std.krb ticket. Not Filed
`T-draft-f9f9fe96 (never refiled)` (renumbered on land; parent T-0254, scope
`strata-core/src/lib.rs` + `_facts.py` + `_krb.py` + `tests/**` +
`docs/strata/**`) for the real fix. Went honest per the reviewer's own
fallback instruction: `docs/strata/krb.md` gained a `### Known gap:
transitive is recorded, not yet enforced (T-draft-f9f9fe96 (never refiled))` subsection
under Domain trust lattice, spelling out the exact bug and telling
T-0263/T-0264 readers to treat every trust as transitive until it closes;
the elaboration-table prose no longer claims "multi-hop reachability
exactly like any other flow chain" as if `transitive` were meaningful
today. `_krb.py::krb_trust_flows`'s docstring gained the same disclosure.
Added `tests/unit/strata/test_krb.py::TestTrustChainReachability` with
BOTH of the reviewer's exact regression scenarios: the all-transitive
chain (correct behavior, `reach(a,c) is True`) and the all-non-transitive
chain, which is an explicit KNOWN-GAP TRIP-WIRE -- it currently asserts
the BUGGY `reach(a,c) is True` with a docstring/comment saying this
assertion must flip to `is False` when T-draft-f9f9fe96 (never refiled) lands, not be
silently deleted.

**Issue 2 (dangling SPN): FIXED in this ticket.** Added
`StrataError.MalformedKrb` (`_errors.py`) and a check in
`_elaborate.py::_validate_krb`: a node declaring `spn` with no `runs_as`
on the SAME node now fails elaboration closed (`MalformedKrb`), instead
of silently accepting a principal-less SPN. Two new tests in
`test_krb.py::TestKrbValidation` (`test_spn_without_runs_as_is_malformed`,
`test_spn_with_runs_as_elaborates_cleanly`) cover both the error and the
"still elaborates when both are present" positive case. Verified this
does not regress the existing `krb_declared.strata` litmus fixture (its
`app` node already declares `runs_as` alongside `spn`).

Round-2 evidence (4 new ids, fresh `pytest --collect-only -q -o
addopts=""` pass, 18 krb-suite node ids total confirmed collected and
passing):
- tests/unit/strata/test_krb.py::TestKrbValidation::test_spn_without_runs_as_is_malformed
- tests/unit/strata/test_krb.py::TestKrbValidation::test_spn_with_runs_as_elaborates_cleanly
- tests/unit/strata/test_krb.py::TestTrustChainReachability::test_transitive_chain_reaches_across_both_hops
- tests/unit/strata/test_krb.py::TestTrustChainReachability::test_non_transitive_chain_currently_over_reaches_known_gap

Round-2 gates:
- `uv run frob check --ticket T-0262` (after re-running `frob ticket
  sweep T-0262` post-merge): 0 errors, 5 warnings, 27 waived.
- `uv run frob check` (full, unscoped): 0 errors, 5 warnings, 27 waived,
  0 DRIFT002; `ruff-check` no issues; `ruff-format` all files formatted;
  `ty` no issues.
- `tests/unit/strata/test_selfconform.py::TestRealGateGreen`: green.
- Full repo `uv run pytest -q` (minus the same pre-existing unrelated
  flaky `test_locate_pypi_source_missing_returns_none`): all green.
- `git diff main --diff-filter=D --stat`: empty.

Not Filed this round: `T-draft-f9f9fe96 (never refiled)` (kernel-level terminal-edge support
for non-transitive flow chains, parent T-0254) -- the honest fix for
issue 1, out of T-0262's scope.

Ticket remains OPEN for reviewer; `frob ticket close T-0262` still
intentionally not run.
