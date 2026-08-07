## Done report

Inventory table (registry -> guide -> anchor site), 19 registries total:

| Registry | Guide | Anchor (`frob:doc`) |
|---|---|---|
| Gate rule families | `docs/guides/extending/gate-rule-families.md` | `src/frob/gates/_models.py::GateConfig` |
| Comment DSL directives | `docs/guides/extending/comment-dsl-directives.md` | `src/frob/graph/dsl.py::_VERB_TABLE` |
| Threat catalog | `docs/guides/extending/threat-catalog.md` | `src/frob/strata/_threat.py::WeaknessEntry` |
| Benign capabilities | `docs/guides/extending/benign-capabilities.md` | `src/frob/strata/_threat.py::BenignCapability` |
| Compliance registry | `docs/guides/extending/compliance-registry.md` | `src/frob/strata/_compliance.py::RegulationEntry` |
| Capability registry | `docs/guides/extending/capability-registry.md` | `src/frob/vet/_capability_registry.py::DangerousOperation` |
| CVE fingerprints | `docs/guides/extending/cve-fingerprints.md` | `src/frob/strata/_cve_fingerprint.py::CveFingerprint` |
| PII categories | `docs/guides/extending/pii-categories.md` | `src/frob/strata/_pii.py::PiiViolation` |
| Design-lint rules | `docs/guides/extending/design-lint-rules.md` | `src/frob/strata/_lint.py::LintViolation` |
| Secrets-scan providers | `docs/guides/extending/secrets-scan-providers.md` | `src/frob/gates/_secrets.py::_SecretPattern` |
| Prover claim kinds | `docs/guides/extending/prover-claim-kinds.md` | `src/frob/strata/_claims.py::evaluate_claims` |
| Scenario kinds | `docs/guides/extending/scenario-kinds.md` | `src/frob/strata/_scenarios.py::ScenarioResult` |
| Strata surface grammar + tmLanguage lock | `docs/guides/extending/strata-surface-grammar.md` | `tests/unit/test_strata_tmlanguage.py::test_construct_keywords_match_parser_bidirectionally` (anchor kept in-scope; `strata-core/src/parse.rs` is outside T-0159's scope glob, so the anchor lives on the drift-lock test that reads it, not on the parser file itself) |
| `[[test.runner]]` entries | `docs/guides/extending/test-runner-entries.md` | `src/frob/testing/_models.py::RunnerSpec` |
| Language grammar handlers | `docs/guides/extending/language-grammar-handlers.md` | `src/frob/lang/_extract.py::extract` (describes-anchor; `_WALKERS` itself is a private dict, not a resolvable symbol) |
| sys export formats | `docs/guides/extending/sys-export-formats.md` | `src/frob/strata/_export.py::export_k8s_netpol` |
| Litmus fixture mappings | `docs/guides/extending/litmus-fixtures.md` | `tests/unit/strata/test_litmus_surface.py::TestNaiveSurfaceGoldens` |
| Ticket kinds/states | `docs/guides/extending/ticket-kinds-states.md` | `src/frob/tickets/_models.py::TicketState` |
| Dup detector registry (R1-R7 rung ladder) | `docs/guides/extending/dup-detector-registry.md` | `src/frob/dup/_rules.py::DUP001` |

Anti-rot mechanism: `docs/guides/extending/registry_of_registries.json` is
the machine-readable inventory; `tests/unit/test_extending_guides_complete.py`
(6 tests) asserts, for every row, that (1) the guide file exists, (2) the
named anchor_file still defines anchor_symbol and carries a `frob:doc`
edge into the guide, (3) the edge's `#fragment` resolves to a real heading
slug or `<a id>` in the guide, (4) no orphan guide file is missing a row,
and (5)/(6) a hard-coded `_REGISTRY_PROBES` table (independent of the
JSON) still matches real source, so the JSON and the probe table can't
silently drift from each other or from the codebase. `docs/index.md`
gained an "Extending frob" section linking all 19 guides plus the README.

Known gaps disclosed, not fixed (out of scope -- doc-anchors only): no
`frob check` gate enforces "every prover claim kind / scenario rewrite
kind / sys export format has a dispatch/registration arm" -- an unhandled
variant fails at runtime, not at `frob check` time. Called out explicitly
in `prover-claim-kinds.md`, `scenario-kinds.md`, `sys-export-formats.md`,
and `docs/guides/extending/README.md`'s "Known gaps" section.

Scope note: `strata-core/src/parse.rs` is outside this ticket's declared
scope (`docs/guides/**`, `docs/index.md`, `src/frob/**`, `tests/**`,
`tickets.md`); an in-progress draft anchor there was reverted
(`git checkout -- strata-core/src/parse.rs`) once `frob check` flagged it
as SCOPE001, and the strata-surface-grammar guide's anchor was moved to
the in-scope tmLanguage drift-lock test instead, which is arguably the
more correct anchor site anyway (it's the actual enforcement mechanism).

Evidence: `tests/unit/test_extending_guides_complete.py`'s 6 collected
tests, all green (`uv run pytest tests/unit/test_extending_guides_complete.py
-v` -> 6 passed), plus `tests/unit/test_strata_tmlanguage.py` (12 tests,
all green) since the strata-surface-grammar anchor lives there.
`uv run frob test --base main` selected and ran the touched-set (python
runner, exit=0, 6.84s) including both files above plus
`tests/unit/strata/test_litmus_surface.py` and `src/frob/strata/**`.

Gates: `uv run frob check --delta --ticket T-0159` after a fresh
`frob graph build` and a re-run `frob ticket sweep T-0159` (post-merge)
reports exactly one gate error, and it is pre-existing debt outside this
ticket's scope: `COV003` on ticket `T-0168` (an unrelated ticket's stale
evidence id, `tests/test_gates.py::TestConventionUnitBinding.
test_test001_exempts_strata_flow_declarations`, does not resolve to a
collected test) -- confirmed pre-existing via `git stash` + re-run before
committing. `ruff check .` and `ruff format --check .` both clean.
`tests/unit/strata/test_selfconform.py::TestRealGateGreen::
test_repo_design_and_declarations_are_self_conformant` fails on 5
pre-existing SYS100 findings (capabilities observed but undeclared in
`design/frob.strata`, e.g. `_cve_fingerprint.py`'s `fs`/`sql` capabilities)
-- confirmed pre-existing (same failure with this ticket's diff stashed
out); not touched, out of scope.

Filed while documenting (out-of-scope defects found, not fixed here):
- T-draft-c4c47359: frob:tests edge code endpoints and kind= attr are not
  gate-verified -- tests/unit/test_strata_tmlanguage.py:13 cites
  `parse.rs::parse_program` (real qualname `Parser.parse_program`) with
  `kind="drift"` (not in `_TESTS_KINDS`), and neither problem fires any
  gate, while the identical dead endpoint on a frob:describes edge fires
  DRIFT002. A silently-broken evidence edge, not a documented absence.
- T-draft-29ea9722: `frob outline` has no Rust adapter though `frob.lang`
  parses Rust (151 symbols from parse.rs) -- the outline adapter registry
  and the language-walker registry can drift apart.
Both drafts were first filed mid-ticket and lost in a tickets.md ledger
splice during a concurrent-agent merge; refiled post-merge. The remaining
"known gaps" above are documentation-level disclosures inside the guides
(no gate claims to cover them and none is silently broken), so per the
ticket's instruction they are disclosed, not ticketed.

Waivers added by this ticket (all in
tests/unit/test_extending_guides_complete.py, each with reason=): one
PERF003 (fixed-size per-row anchor scan) and three PERF004 (sorted() only
formatting tiny sets for assert messages) -- the new test file's only
lexical-perf findings; no other waivers introduced.

Deletion-filter (`git diff main --diff-filter=D --stat`): empty after the
final `git merge main` (main had landed T-0176's `frob ticket land`,
`_land.py`, and T-0172's `managed` marker since this worktree's base;
merged clean, no deletions of already-landed work).

Not closed per the parent dispatch's explicit instruction ("do not
close"); left in state `in-progress` with this Done report and evidence
list for the reviewer/closer.
