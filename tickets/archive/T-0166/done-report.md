## Done report

Resolution: implemented `code`/`may` on `store` (surface.md's `store_prop := node_prop | ...`
line was the correct spec; the grammar was the bug, not the doc). `code`/`may` on `store`
now mirror `node`'s handling exactly, and the T-0150 `tickets_ledger`/`core` workaround was
un-folded.

Changed:
- strata-core/src/parse/mod.rs::parse_store -- new `code`/`may` branches (same STRING+/STRING
  shape T-0132 gave `node`), plus `code`/`may` fields in the stores JSON output.
- src/frob/strata/_ast.py::StoreDecl -- new `code: tuple[str, ...] = ()` / `may: tuple[str, ...] = ()`
  fields.
- src/frob/strata/_infra.py::_elaborate_store -- `code` globs desugar to `code=<glob>` attrs
  (same convention `_elaborate_node` uses, `_code_binding.py::_node_code_globs` reads it back
  generically off any `Node`); `may` lands directly on the elaborated `Node.may` field.
- docs/strata/surface.md -- new "`code`/`may` on `store` (T-0166)" callout paragraph
  (#node-grammar-implemented) documenting the fix and the exact semantics.
- design/frob.strata -- un-folded the T-0150 workaround: `src/frob/tickets/**` moved off
  `core`'s `code`/`may` onto `tickets_ledger`'s own `code "src/frob/tickets/**"` +
  `may "env"`/`"exec"`/`"fs"` (measured honestly via
  `frob.vet._capability.scan_directory_capabilities('src/frob/tickets')` -> `{env, exec,
  fs-write}`, zero eval/net/ffi). This drags in one new THREAT003 CWE-78 obligation on
  `tickets_ledger`, discharged with `assume "weakness:CWE-78:tickets_ledger" noflow registry
  -> tickets_ledger owner logan review "2026-10-15"` (graph-provable via the pre-existing
  `c_no_registry_ledger` assert, but an `assert`-form discharge still requires a boundary-KIND
  mitigation-chokepoint proof that doesn't exist here -- `assume` is the honest tool, same
  precedent `checker`'s discharge comment already documents).
- tests/unit/strata/test_store_code_may.py (new) -- grammar + elaboration tests for store
  code/may, plus two tests proving a store's `may "exec"` auto-instantiates the same
  undischarged THREAT003 CWE-78 obligation a node's would (answering the ticket's "does a
  store's may feed THREAT003 obligations?" question: yes, identically -- `_threat.py` reads
  `Node.may` generically with no node/store distinction).
- tests/system/test_frob_self_model.py -- claim count 12 -> 13 (new
  `weakness:CWE-78:tickets_ledger` assume), docstrings updated.
- tests/golden/frob_export_seccomp.json -- regenerated via
  `export_seccomp(elaborate(parse_module(design/frob.strata)))`; `tickets_ledger`'s seccomp
  profile now allows clone/execve/execveat/fork/vfork (its new `may "exec"`).
- strata-core rust unit tests: `parses_store_code_globs_and_may_capabilities`,
  `parses_store_without_code_or_may_defaults_empty`,
  `error_store_code_requires_at_least_one_glob`, `error_store_may_requires_string_not_ident`.

Semantics decided and documented: a store's `code` participates in tier-2 import conformance
(`check_import_conformance`) exactly like a code-modeled node's would (both read `code=` attrs
off any elaborated `Node`, no store/node distinction). A store's `may` capability
auto-instantiates THREAT003 weakness obligations exactly like a node's would, for the same
reason (`_threat.py` reads `Node.may` generically).

Not Filed: T-draft-956203f7 (never refiled) "store grammar still missing on-deploy/observe/errors_total/
panics_contained_by from node_prop" -- surface.md's `store_prop := node_prop | ...` grammar
line literally claims the FULL node_prop set is legal on store; this ticket closed only the
code/may gap it explicitly named. `on deploy`/`observe`/`errors_total`/`panics_contained_by`
remain unimplemented on `parse_store`, a real (smaller) remaining gap between that grammar
line and the actual parser, left for a follow-up ticket rather than folded into this one.

Evidence:
- `uv run pytest tests/unit/strata/test_store_code_may.py --collect-only`: 5 tests collected
  -- `TestStoreCodeMayGrammar::test_store_code_glob_elaborates_to_code_attr`,
  `TestStoreCodeMayGrammar::test_store_may_capability_lands_on_node_may`,
  `TestStoreCodeMayGrammar::test_store_without_code_or_may_defaults_empty`,
  `TestStoreMayFeedsThreat003::test_store_with_exec_may_fires_undischarged_cwe_94`,
  `TestStoreMayFeedsThreat003::test_store_without_may_fires_no_obligation`.
- `uv run pytest -q -n auto`: full suite green (exit 0), no failures, after the golden-file
  regeneration and test_frob_self_model.py claim-count update.
- `cargo test --release` (strata-core, `VIRTUAL_ENV`/`LD_LIBRARY_PATH` pointed at the
  worktree venv/uv python lib): 106 passed, 0 failed, including the 4 new store code/may tests
  and `parses_store_carries_pii_tags`/`parses_store_managed_marker` (unaffected precedent
  tests still green).
- `uv run frob check --only sys`: 0 violations (was `1 violation(s)` THREAT003 mid-fix, before
  the `tickets_ledger` discharge claim was added).
- `uv run frob check`: 1 error total, `[gates] tickets/T-0168:0 COV003` -- pre-existing, out of
  scope (already documented at tickets.md's own T-0221..T-0234 filing note as "out of scope:
  COV003 on T-0168 (stale evidence id, unrelated ticket)"); no new violations introduced by
  this change, before or after merging main forward.
- `uv run frob test --base main`: `[PASS] python exit=0 8.17s`, ran the touched-set including
  `tests/unit/strata/test_store_code_may.py`, `tests/system/test_frob_self_model.py`, and
  `tests/unit/strata/test_managed.py::TestManagedGrammar::test_store_managed_marker_elaborates_to_attr`.
- `git diff main --diff-filter=D --stat`: empty, after a second `git merge main` (main had
  moved to b2a91fa mid-session, adding docs/guides/extending/** and other unrelated files --
  fast-forwarded cleanly, no conflicts, `make core` rebuilt, full suite re-verified green).

Gates: `frob check --ticket T-0166` clean except the pre-existing `tickets/T-0168:0 COV003`
(unrelated ticket, out of scope, already documented as such at this ledger's T-0221..T-0234
filing note). Note: the mid-session `git merge main` fast-forward dropped the recorded
pre-work sweep (PRE001 fired on the first post-merge `--ticket` run since `.frob/prework/` is
local, uncommitted state); re-ran `uv run frob ticket sweep T-0166` to re-record it (dup=165,
xref=6), after which `--ticket T-0166` shows 0 violations beyond the pre-existing T-0168 one.
