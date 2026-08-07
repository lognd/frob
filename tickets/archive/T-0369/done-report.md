## Done report

Changed: renamed 73 of the 73 currently-flagged src symbols (`name` -> `_name`)
in their defining module and every in-repo reference (call sites, imports,
`frob:tests`/`frob:describes` directives). All 73 verified genuinely
package-internal by repo-wide grep before renaming (0 cross-package src
imports; only tests/ imported them directly by name, or referenced them via
comments/docstrings) -- none needed exporting instead. List (old -> new):
- src/frob/dup/_cache.py: close_all -> _close_all
- src/frob/dup/_core.py: r3_canonical_hash, winnow_fingerprints,
  candidate_pairs, tree_edit_similarity, apted_similarity, exact_regions,
  wl_hash -> `_`-prefixed (the Rust-native `frob_core.<name>` attribute
  names these wrap were left unprefixed -- they belong to the out-of-scope
  `frob-core` crate, not this rename)
- src/frob/dup/_pipeline.py: probe_smt_equivalence -> _probe_smt_equivalence
- src/frob/gates/_pii_structural.py: scan_python_fields,
  scan_python_env_access, FieldSignature -> `_`-prefixed
- src/frob/gates/_secrets.py: redact -> _redact
- src/frob/gates/decisions.py: DecisionStatus -> _DecisionStatus
- src/frob/gates/invariants.py: Criticality -> _Criticality
- src/frob/graph/digest.py: digest_sig, digest_body, digest_doc ->
  `_`-prefixed (the `digest_sig`/`digest_body`/`digest_doc` SQLite column
  names in src/frob/graph/cache.py's schema were left unprefixed -- same
  spelling, unrelated symbol, a schema string not a Python reference)
- src/frob/lang/_common.py: collapse_ws, leaf_tokens, strip_comment_delims,
  leading_doc_comment, span_of, find_enclosing_symbol,
  find_following_symbol -> `_`-prefixed
- src/frob/logging/filter.py: BelowLevelFilter -> _BelowLevelFilter
  (also updated the `"()"` dotted-path string in
  src/frob/logging/config.toml's dictConfig filter entry)
- src/frob/logging/formatter.py: FrobFormatter -> _FrobFormatter
  (also updated the `"()"` dotted-path strings in
  src/frob/logging/config.toml's dictConfig formatter entries)
- src/frob/strata/_ast.py: CanaryStageDecl, DeployDecl, SecretDecl ->
  `_`-prefixed
- src/frob/strata/_host.py: host_attrs -> _host_attrs
- src/frob/strata/_krb.py: krb_attrs -> _krb_attrs
- src/frob/strata/_waive.py: split_waiver_rule, validate_waiver_fields,
  stale_detail -> `_`-prefixed
- src/frob/tickets/_store.py: store_mode, serialize_ticket,
  parse_ticket_file -> `_`-prefixed
- src/frob/vet/_allow.py: load_vet_config -> _load_vet_config
- src/frob/vet/_cache.py: store_verdict, latest_verdict -> `_`-prefixed
- src/frob/vet/_capability.py: scan_file_operations, scan_file_fingerprints,
  decode_to_exec_signal, scan_directory_capabilities,
  scan_directory_fingerprints -> `_`-prefixed
- src/frob/vet/_capability_registry.py: unexcused_empty_cells,
  validate_registry_kinds, DangerousOperation, MatrixExcuse, MatrixCell ->
  `_`-prefixed
- src/frob/vet/_ecosystem.py: python_rules, rust_rules,
  npm_non_registry_rule -> `_`-prefixed
- src/frob/vet/_lifecycle.py: scan_lifecycle_scripts ->
  _scan_lifecycle_scripts
- src/frob/vet/_lockfile.py: find_lockfile, parse_lockfile -> `_`-prefixed
- src/frob/vet/_models.py: HookAction -> _HookAction
- src/frob/vet/_obfuscation.py: high_entropy_strings, invisible_text_signal,
  hex_identifier_ratio_signal, scan_text_obfuscation,
  scan_directory_obfuscation -> `_`-prefixed
- src/frob/vet/_osv.py: is_available, run_osv_scan -> `_`-prefixed
- src/frob/vet/_registry.py: fetch_publish_date, RegistryResult ->
  `_`-prefixed
- src/frob/vet/_source.py: locate_pypi_source, locate_npm_source,
  locate_cargo_source, locate_source -> `_`-prefixed
- src/frob/vet/_typosquat.py: damerau_levenshtein, find_typosquat ->
  `_`-prefixed

Also touched (mechanical follow-through of the renames above, all within
the widened `docs/**` scope, see below): every intra-package caller/import
in the files listed above's own packages; every tests/ import and usage
site (tests/unit/test_dup_cache.py, tests/unit/test_dup_core.py,
tests/unit/test_dup_smt.py, tests/unit/test_runtime_deps.py,
tests/test_dup_region.py, tests/test_pii_structural_gate.py,
tests/test_secrets_gate.py, tests/test_decisions.py, tests/test_gates.py,
tests/test_graph.py, tests/unit/test_lang_primitives.py, tests/test_lang.py,
tests/unit/test_lang_strata.py, tests/unit/test_logging_module.py,
tests/unit/strata/test_host.py, tests/unit/strata/test_krb.py,
tests/unit/strata/test_waive.py, tests/unit/strata/test_litmus_host.py,
tests/unit/strata/test_litmus_krb.py, tests/unit/strata/test_selfconform.py,
tests/unit/test_ticket_store.py, tests/test_tickets.py,
tests/unit/test_claims_and_store_batch6.py, tests/unit/test_store_batch7.py,
tests/unit/test_app_runners_batch7.py, tests/test_vet.py,
tests/test_capability_registry.py, tests/test_vet_containment.py); and the
`frob:describes` anchors bound to the old public names in
docs/modules/{vet,gates,lang,logging,decisions,graph,tickets}.md and
docs/guides/extending/capability-registry.md.

Scope note: the ticket's declared `scope` was `src/frob/**`, `tests/**`;
I extended it to add `docs/**` mid-ticket (via `frob ticket sweep` after
editing the frontmatter) because the ticket body itself explicitly
instructs "update the directive to the new private name too (or
DRIFT002/COV001 will fire)" for `frob:doc`-bound symbols -- 9 `docs/*.md`
files carry `frob:describes` anchors bound to the renamed public names and
DRIFT002 fired against them until updated. This is not scope creep beyond
what the ticket text itself required; no other docs content was touched.

Not touched (deliberately, same-name-different-namespace): the
`BelowLevelFilter`/`FrobFormatter` occurrences under
src/frob/scaffold/data/**/*.j2 and their generated docs -- those are
project-scaffolding templates that mint their OWN same-named classes for
scaffolded projects, unrelated to `frob.logging`'s own symbols.

Filed: none -- no new out-of-scope issue found. (The ticket description's
own aside about `FrobFormatter` looking "fully dead -- also worth a
dead-code check" was investigated only insofar as confirming it has no
cross-package Python importer; a full dead-code determination was not
attempted and is left as-is per the ticket's own framing of that as a
secondary note, not an action item.)

Evidence:
- `uv run pytest tests/unit/test_dup_cache.py tests/unit/test_dup_core.py
  tests/unit/test_dup_smt.py tests/unit/test_runtime_deps.py
  tests/test_dup_region.py tests/test_pii_structural_gate.py
  tests/test_secrets_gate.py tests/test_decisions.py tests/test_gates.py
  tests/test_graph.py tests/unit/test_lang_primitives.py tests/test_lang.py
  tests/unit/test_lang_strata.py tests/unit/test_logging_module.py -q` ->
  all passed (0 failed)
- `uv run pytest tests/unit/strata/test_host.py tests/unit/strata/test_krb.py
  tests/unit/strata/test_waive.py tests/unit/strata/test_litmus_host.py
  tests/unit/strata/test_litmus_krb.py tests/unit/strata/test_selfconform.py
  tests/unit/test_ticket_store.py tests/test_tickets.py
  tests/unit/test_claims_and_store_batch6.py tests/unit/test_store_batch7.py
  tests/unit/test_app_runners_batch7.py -q` -> all passed (0 failed)
- `uv run pytest tests/test_vet.py tests/test_capability_registry.py
  tests/test_vet_containment.py -q` -> all passed (0 failed)
- `uv run frob test --base main` -> python exit=0, 7.36s (touched-set
  selection ran the same test files above plus a handful more)

Gates: `uv run frob check --ticket T-0369` -> 1 error remaining: REL001
(public API changed (major) since 0.28.0 -- expected per this ticket's
instructions; the coordinator handles the version bump at land, not this
ticket). `--only exports` not-exported (excluding tests/) count: before=73,
after=0. `--only drift --only coverage`: PASS, 0 errors. `ruff check` and
`ruff format --check` both clean under `uv run ruff` and bare `ruff`.
`ty check`: no issues. `frob-cycle`: no cycles.
`git diff main --diff-filter=D --stat`: empty (no unintended deletions).
