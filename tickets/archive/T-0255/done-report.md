## Done report

Changed:
- strata-core/src/parse.rs -- `parse_node`/`parse_store`: new `runs_as
  STRING`, `unit` bare marker, `owns STRING STRING` (repeatable),
  `listens NUMBER` (repeatable) clauses, mirroring the `managed`/`waive`
  precedent; JSON output extended with `runs_as`/`is_unit`/`owns`/
  `listens`. 6 new Rust unit tests.
- src/frob/strata/_ast.py -- `OwnsDecl`; `NodeDecl`/`StoreDecl` gain
  `runs_as`/`is_unit`/`owns`/`listens` fields.
- src/frob/strata/_host.py (NEW) -- `HostPlatform` (StrEnum, discriminator
  reserved for T-0261's windows), `HostOwns`, `HostManifest`, `host_attrs`
  (the one shared attr-desugar encoding), `host_manifest_for` (attr
  read-back, mirrors `_pii.py::node_pii_tags`).
- src/frob/strata/_elaborate.py::_elaborate_node -- calls `host_attrs` to
  desugar std.host clauses into `Node.attrs`.
- src/frob/strata/_infra.py::_elaborate_store -- same, for `store` (a
  store is a node too).
- src/frob/strata/__init__.py -- exports `OwnsDecl`, `HostManifest`,
  `HostOwns`, `HostPlatform`, `host_manifest_for`.
- editors/vscode-strata/syntaxes/strata.tmLanguage.json -- added
  `runs_as`/`unit`/`owns`/`listens` to the clause-keywords drift-lock
  list.
- docs/strata/host.md (NEW) -- grammar, attr-desugar table, HostManifest
  shape, the "OS users join the trust lattice" scope note (today: the
  `runs_as=<name>` attr; full lattice participation is T-0257), and the
  explicit T-0256/T-0257/T-0258/T-0259/T-0261 scope-cut list.
- tests/unit/strata/test_host.py (NEW), test_litmus_host.py (NEW),
  litmus/host_declared.strata, litmus/host_undeclared.strata (NEW).
- tickets.md -- this Done report + evidence.

Evidence (recorded via `frob ticket evidence`):
- tests/unit/strata/test_host.py::TestHostAttrs::test_desugars
- tests/unit/strata/test_host.py::TestHostAttrs::test_no_clauses_desugars_to_empty
- tests/unit/strata/test_host.py::TestHostManifest::test_reads
- tests/unit/strata/test_host.py::TestHostManifest::test_node_with_no_host_attrs_returns_none
- tests/unit/strata/test_litmus_host.py::TestHostDeclaredLitmus::test_declared_manifest_round_trips_every_field
- tests/unit/strata/test_litmus_host.py::TestHostUndeclaredLitmus::test_undeclared_node_has_no_manifest

Additionally observed passing (not CLI-recorded, no pytest surface):
`cargo test --release` in strata-core: 109 passed (0 failed), including
the 4 new tests `parses_node_host_manifest_clauses`,
`parses_node_without_host_manifest_defaults_empty`,
`parses_store_host_manifest_clauses`. Full `uv run pytest
tests/unit/strata/ -q`: all pass (12 workers, no failures). `uv run
pytest tests/unit/test_strata_tmlanguage.py -q`: all pass (drift-lock
green with the 4 new keywords added).

Filed: none -- no out-of-scope work found.

Gates: `uv run frob check --delta --ticket T-0255` -- new-violation set is
`tests/test_graph.py` DRIFT002 (x2), `pyproject.toml`/`CHANGELOG.md`
REL001 (x2), confirmed via a clean stash (`git stash -u`) run against
main tip 591502e that these fire IDENTICALLY with zero T-0255 changes
present -- pre-existing, not introduced by this ticket, left untouched
(out of scope). TEST001 on `host_attrs` (initially fired) was fixed by
adding `tests/unit/strata/test_host.py` and `frob:tests` directives; a
re-check after that fix showed TEST001 clear. SCOPE001 on
`frob-core/Cargo.lock`/`strata-core/Cargo.lock` (fired after `make core`
touched them) was resolved by `git checkout -- frob-core/Cargo.lock
strata-core/Cargo.lock` immediately before this final check and again
right before commit (per playbook: `make core` rebuild-touches lockfiles
outside declared scope). `ruff check`/`ruff format --check` clean under
both the PATH `ruff` and `uv run ruff`; `ty check` clean. Deletion filter
(`git diff main --diff-filter=D --stat`) empty.
