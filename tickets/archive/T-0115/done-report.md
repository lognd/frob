## Done report

Changed:
- src/frob/strata/_audit.py (new) -- `evaluate_exhaustiveness`, `AuditReport`, `FamilyGap`, `_evaluate_family`, `_threat_gaps`, `_compliance_gaps`, `DEFAULT_SECURITY_VIEWS`, `DEFAULT_QUALITY_VIEWS`, `DEFAULT_COMPLIANCE_VIEWS`
- src/frob/strata/__init__.py -- export the above; also fixed a pre-existing gap (`check_effect_completeness` was in `_threat.py.__all__` but never re-exported here, breaking `tests/unit/strata/test_threat.py` collection -- unrelated to my change but in-scope and blocking verification, fixed inline)
- src/frob/app/sys_runner.py -- `_run_audit`, `_print_audit_report`; `run()` dispatches `audit`
- src/frob/app/config.py -- `AppConfig.sys_command` comment updated, `frob:ticket T-0115` added
- src/frob/__main__.py -- `_add_sys_parser` registers `sys audit` subcommand
- docs/commands/sys.md -- `frob sys audit` section (usage, semantics, public API, vuln-litmus pointer)
- docs/strata/threat.md -- phasing item F marked SHIPPED (T-0085 + T-0115), litmus scope note
- design/litmus/audit_vuln.strata (new) -- vuln litmus: `may "sql"` fires undischarged CWE-89 (security) + CWE-639 (quality)
- tests/unit/strata/test_audit.py (new) -- `evaluate_exhaustiveness` unit tests + the vuln-litmus/hardened-twin `KernelModel` pair covering all three families (security/quality/compliance)
- tests/unit/strata/test_litmus_audit_vuln.py (new) -- parse -> elaborate -> evaluate_exhaustiveness golden for `audit_vuln.strata`
- tests/system/test_cli_sys_audit.py (new) -- CLI end-to-end: clean model exits 0 with PROVED, undischarged capability exits nonzero with a named GAP line, no-design-dir is a no-op

Audit semantics: `evaluate_exhaustiveness(model, security_views=DEFAULT_SECURITY_VIEWS, quality_views=DEFAULT_QUALITY_VIEWS, compliance_views=DEFAULT_COMPLIANCE_VIEWS)` runs THREAT001+002+003 (via `check_catalog_completeness`/`check_capability_completeness`/`check_discharge_completeness`, zero new detection) against every security view in `VIEWS` and every quality view in `QUALITY_VIEWS` (a NEW `_evaluate_family` helper reparameterizes the same three calls `evaluate_threats` makes, since `evaluate_threats` hardcodes the module-global `VIEWS` and cannot resolve `QUALITY_VIEWS`-only view names), plus COMPLIANCE001+002 (`evaluate_compliance`, unmodified) against every view in `REGULATION_VIEWS`. Returns `Err` on any unknown view name (fail-closed, matches every other exhaustiveness check). Returns `AuditReport(views_checked, gaps)`; `gaps: tuple[FamilyGap]` names family/view/rule/detail per violation; `proved` is a property, `not gaps`. `frob sys audit` CLI prints `PROVED` or one `GAP family=... view=... rule=... detail=...` line per gap and exits 1 on any gap.

Litmus gaps exercised per family (`tests/unit/strata/test_audit.py::_vulnerable_model` / `design/litmus/audit_vuln.strata`):
- security: THREAT003, CWE-89 (SQL injection), undischarged on node `web` (fired by `may "sql"`)
- quality: THREAT003, CWE-639 (dynamic ORM/tenant-scoping, `QUALITY_CATALOG`, SAME `sql` capability kind), undischarged on node `web`
- compliance: COMPLIANCE002, COPPA, undischarged on flow `f_collect` (a `subject:child`-tagged collection flow into a `Pii` store with no ENDORSE boundary)

Hardened twin (`_hardened_model`) discharges all three: ASSUMED `NoFlow` claims (owner+review) named `weakness:CWE-89:web` / `weakness:CWE-639:web`, plus an ENDORSE boundary on `f_collect` for COPPA -- `evaluate_exhaustiveness` returns `proved=True`, `gaps=()`.

Scope-cut note (real, not silent): the hardened twin and the compliance-family litmus obligation are `KernelModel` Python fixtures, NOT a second `.strata` file, because of a genuine surface-grammar gap found while building this litmus: `_threat.py::_discharge_claim_id` / `_compliance.py`'s discharge-claim-id convention (`weakness:<cwe>:<node>`, `compliance:<reg>:<target>`) requires `:` (and any real CWE id like `CWE-89` also needs `-`), but `strata-core/src/parse/mod.rs::parse_claim`'s claim id is a bare IDENT (`is_ident_cont` = ascii alnum + `_` only) -- no `.strata` source file can author a claim that discharges ANY THREAT00x/COMPLIANCE00x obligation today. Confirmed this isn't new: `design/litmus/payments*.strata` and `deploy_secret.strata` never exercise a `weakness:`/`compliance:`-shaped claim either, only plain `noflow`/`bound`/`reach` asserts -- and every existing `test_threat.py`/`test_compliance.py` obligation test already builds `KernelModel` fixtures directly for the same reason. `strata-core/**` is outside T-0115's scope, so this was filed as **T-0137** rather than patched around; `audit_vuln.strata` still exercises the ONE piece that DOES round-trip through the parser (the `may "sql"` capability declaration, T-0136), with its own permanent CI golden (`test_litmus_audit_vuln.py`).

Filed: T-0137 (surface grammar: claim ids cannot express `weakness:`/`compliance:` discharge convention; colon+hyphen disallowed in IDENT)

Numbers:
- `uv run pytest -q` (full suite): exit=0, all green
- `uv run pytest -q tests/unit/strata/test_audit.py tests/unit/strata/test_litmus_audit_vuln.py tests/system/test_cli_sys_audit.py tests/unit/strata/test_threat.py tests/unit/strata/test_compliance.py tests/unit/strata/test_sysdoc.py tests/system/test_cli_sys_doc.py tests/system/test_cli_sys_plan.py`: all pass (touched-set + sys plan/doc/audit combined CLI suite)
- `uv run frob check`: every tool row `pass` (ruff-check, ruff-format, ty, frob-cycle, frob-dup, frob-arch, all frob-exports, gates) -- gates 87 violations / 49 waived, ALL pre-existing (PERF001-004 heuristic hits on files this ticket never touched, TEST003 interface-coverage gaps on unrelated packages, baseline frob-exports "not exported" counts); zero new unwaived COV001/COV002/DOC violation from this diff (the 4 COV001 + 2 COV002 hits this diff introduced -- `frob:doc` on `DEFAULT_*_VIEWS`/`AuditReport.proved`, `frob:ticket T-0115` on `AppConfig`/`_print_audit_report` -- were all fixed before this report)
- CLI evidence: `frob sys audit` on a clean model -> exit 0, prints `sys audit: PROVED -- zero gaps across every configured view`; on a model with `may "sql"` and no discharge -> exit 1, prints `GAP family=security view=owasp-top-10 rule=THREAT003 detail=...CWE-89...` and the matching quality-family GAP line

Gates: `frob check` clean (see numbers above) -- no waiver needed, no unwaived trip introduced.
