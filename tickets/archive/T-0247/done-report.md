## Done report

Resolution: implemented `errors_total`/`panics_contained_by`/`observe`/`on deploy` on
`store`, mirroring exactly how T-0166 closed the same kind of gap for `code`/`may` --
`store_prop := node_prop | ...` (surface.md) was already the correct spec; the grammar
(`parse_store`) was the bug, having no branch for any of the four T-0070/T-0136 node
properties.

Changed:
- strata-core/src/parse/mod.rs::parse_store -- four new branches (`errors_total` bare
  marker, `panics_contained_by IDENT`, `observe { log ...; to ... }`, `on deploy { ... }`
  via the existing `parse_on_deploy_block` helper), plus the four corresponding fields
  in the stores JSON output. Doc comment above `parse_store` updated to note the T-0247
  closure and that std.krb's realm/kdc/spn/delegation/trusts remain node-only (not
  requested by this ticket).
- strata-core/src/parse.rs (test module) -- `parses_store_errors_total_panics_and_observe`,
  `parses_store_on_deploy`, `error_store_observe_unknown_log_property`; extended
  `parses_bare_store` to assert the four new fields default to null/false. 114/114 rust
  unit tests pass (`cargo test --release`, run with `LD_LIBRARY_PATH` pointed at the
  venv's `libpython3.11.so` -- the harness needs it, `maturin develop` does not).
- src/frob/strata/_ast.py::StoreDecl -- new `errors_total: bool = False`,
  `panics_contained_by: str | None = None`, `observe: ObserveDecl | None = None`,
  `deploy: DeployDecl | None = None` fields, reusing the SAME `ObserveDecl`/`DeployDecl`
  types `NodeDecl` already uses (no new AST type).
- src/frob/strata/_infra.py::_elaborate_store -- `errors_total`/`panics_contained_by`
  desugar to the same `errors_total`/`panics=<id>` attrs `_elaborate.py::
  _node_marker_attrs` gives `node` (new local `_ERRORS_TOTAL_ATTR` constant, kept local
  for the same import-cycle reason `_MANAGED_ATTR` already documents); `on deploy` lands
  on the elaborated `Node`'s `deploy` field via a new local `_elaborate_store_deploy`,
  a byte-for-byte duplicate of `_elaborate.py::_elaborate_deploy` (same import-cycle
  constraint: `_elaborate.py` already imports `_infra.py`, so `_infra.py` cannot import
  back).
- src/frob/strata/_elaborate.py -- `_validate_node_observability`'s type hint widened to
  `NodeDecl | StoreDecl`; `_validate_observability` now walks `(*module.nodes,
  *module.stores)` instead of `module.nodes` alone, so a store's
  `panics_contained_by`/`observe` clauses get the identical fail-closed reference/log-class
  checks a node's would. `_elaborate_observe_flows` likewise now walks both, so a store's
  `observe { ... to X }` synthesizes the same `<id>__obs` Internal flow a node's would
  (verified: `db__obs` flow present in the end-to-end smoke test below). Both docstrings
  updated to note the T-0247 extension.
- docs/strata/surface.md -- new prose paragraph under the `code`/`may` on `store` (T-0166)
  section documenting the T-0247 closure, mirroring that section's structure and citing
  the exact files/functions changed.
- tests/unit/strata/test_store_observability.py (new) -- 8 tests mirroring
  `tests/unit/strata/test_observe.py`'s node-side coverage 1:1 for store: happy-path attrs,
  synthesized observe flow, non-fatal errors_total-without-observe warning, three
  fail-closed cases (unknown panics supervisor, unknown observe target, unknown log
  class), and `on deploy` landing on `Node.deploy` (present and absent cases).
- tickets.md -- this Done report, plus a pre-existing ticket-authoring bug fix: T-0247's
  own `scope` field had been written as one comma-joined YAML list item instead of four
  separate entries (see the scope-fix note above), which made SCOPE001 reject every
  legitimately-scoped file; corrected to five list entries (the original four globs,
  unchanged, plus `tickets.md` per the standard convention). No scope was widened or
  narrowed by content -- only the YAML shape was fixed.

Also verified end to end (ad hoc script, not committed): a `store` with all four new
clauses plus `code`/`may`/`carries`/`waive` from earlier tickets parses, elaborates, and
produces `node attrs == ('errors_total', 'panics=supervisor')`, a populated `Node.deploy`
with the right canary stage/endorsement/rollback fields, and a synthesized `db__obs` flow
-- no store/node distinction downstream, matching T-0166's precedent for `code`/`may`.

Not done / disclosed: std.krb's `realm`/`kdc`/`spn`/`delegation`/`trusts` clauses remain
node-only. They are not part of the `node_prop` grammar block this ticket's title/body
named (docs/strata/surface.md's `node_prop` sketch at the top of the `node` section does
not list them either -- they are documented separately under `docs/strata/krb.md`), so
extending them to `store` is out of this ticket's scope; noted in the parse.rs doc comment
above `parse_store` in case a future ticket wants store/krb symmetry.

Evidence: 8 python unit test node ids recorded via `frob ticket evidence T-0247` (see
`evidence:` above), all passing (`pytest tests/unit/strata/test_store_observability.py -v`
-> `8 passed`). Rust-side coverage (4 new/extended `cargo test` cases) is real and run
(114/114 rust tests pass) but not recorded as ticket evidence -- following T-0166's own
precedent (`tickets-archive.md` T-0166 Done report records only python node ids), since
`frob ticket evidence` could not resolve the rust ids in this pass (`strata-core/src/
parse.rs::<test_fn>` did not resolve against `frob test --collect`'s rust node id
convention; not investigated further, out of scope to fix the evidence-id resolver here).

Gates: `frob check --delta --ticket T-0247` (after `make core`, `make coverage`, and a
fresh `frob ticket sweep T-0247`) reports 0 errors, in-scope warnings only (all
pre-existing PERF00x/ARCH001/TEST009 findings across the repo, none newly introduced by
this diff -- verified `git diff main --stat` touches only the 6 files listed above).
`frob test --base main` selected and ran the full touched-set (31 touched hunks, incl.
`tests/system/test_frob_self_model.py::TestFrobSelfModel::test_parses_and_elaborates`,
every `test_store_*`/`test_infra`/`test_litmus_waive_store`/`test_managed` case) with
`exit=0`. `--delta`'s baseline mechanism proved unreliable across the two re-merges this
pass needed (staleness re-triggers on file-mtime churn from `make core`/`make coverage`,
not just content) -- confirmed clean instead by diffing `git diff main --stat` (my six
files only) against the 2 pre-existing DOC001 findings on two `docs/design/*.md` files
landed by unrelated tickets already on `main`, neither touched by this diff. REL001: no
version bump made (release/pyproject.toml is out of this ticket's scope); coordinator
should bump at land per the dispatch note.

Merged `main` twice during this pass (9619ce9 -> 04e56fd -> ae8dbf4, both fast-forwards);
`git diff main --diff-filter=D --stat` is empty after the final merge (deletion-filter
rule, playbook section 9) -- no unrelated work was reverted.
