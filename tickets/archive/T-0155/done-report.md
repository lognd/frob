## Done report

Changed:
- src/frob/strata/_lint.py (new module: LINT001-005 rule family)
- src/frob/strata/_audit.py (evaluate_exhaustiveness joins evaluate_lint under a fixed lint:model view)
- src/frob/strata/__init__.py (exports for the new _lint.py public surface)
- docs/strata/threat.md (Operational design lints (std.lint, T-0155) section)
- design/frob.strata (f_registry_fetch declares a real rate 1 req/s; checker/core/stratamod/vet documented as honest LINT004 gaps -- no fabricated kill switch)
- tests/unit/strata/test_lint.py (new: hand-built KernelModel unit coverage per rule)
- tests/unit/strata/test_litmus_lint.py (new: surface round-trip via lint_vuln.strata/lint_hardened.strata)
- tests/unit/strata/litmus/lint_vuln.strata, lint_hardened.strata (new litmus pair, fires/discharges all five rules)
- tests/unit/strata/test_audit.py (TestExhaustiveness.test_lint_gap_reported added; _hardened_model's f_collect flow gets a declared rate)
- design/litmus/audit_hardened.strata (OUT OF SCOPE, cascading fix: f_browse needs a declared rate to keep report.gaps == () under the new LINT001 check)
- tests/system/test_cli_sys_audit.py (OUT OF SCOPE, cascading fix: _CLEAN_MODEL's f1 flow needs a declared rate for the same reason)
- tickets.md (scope widened to cover the two cascading-fix files above; this Done report)

Design notes:
- LINT001 (rate limit): a foreign-trust-sourced flow with no declared `Flow.rate`. No claim override (PII001 no-override precedent).
- LINT002 (cache-or-capacity, caching-escapable): a node's declared `capacity.service_rate` exceeded by non-infra inbound flow rate, no `cache` construct covering it.
- LINT003 (surge scenario bound): a `Scenario` with a `ScaleRate` rewrite nesting no `BoundClaim` (RATE/UTILIZATION) over the scaled flow or its endpoints.
- LINT004 (kill switch): a node with a risky (exec/net) `may` capability and no `attr flag=<id>` -- reuses the grammar's existing generic `attr IDENT=IDENT` node property, no new keyword.
- LINT005 (fan-in, caching-agnostic): a node's declared `capacity` (service_rate * replicas_max) exceeded by TOTAL inbound rate, unconditionally -- the LINT002/LINT005 relationship mirrors the PII003/GDPR-RETENTION precedent (can fail one and pass the other).
- Self-model honesty: design/frob.strata's f_registry_fetch now declares a real `rate 1 req/s`. checker/core/stratamod/vet each hold may "exec"/"net" with NO real kill switch in the codebase today -- rather than fabricate a `flag=<id>` attr, these are left as honest, named LINT004 gaps in `frob sys audit` output (T-0150/T-0151 "declare real facts or waive with reasons" precedent). Follow-on ticket T-draft-47dc1469 (never refiled) not filed for the real kill-switch mechanism.

Evidence: 7 pytest node ids recorded via `frob ticket evidence T-0155` (see `evidence:` list above); full suite (`uv run pytest tests/ -q`) green before and after the T-0155 change set, both pre- and post-merge with main.

Not Filed: T-draft-47dc1469 (never refiled) (add real kill-switch/feature-flag mechanism for exec/net capabilities on checker/core/stratamod/vet, to genuinely discharge LINT004 on design/frob.strata).

Gates: `uv run frob check --ticket T-0155` clean (exit 0; remaining TEST005/TEST006 items are pre-existing warn-severity baseline debt in src/frob/gates/__init__.py, unrelated to this ticket's scope). `uv run frob test --base main` PASS (python exit=0, strata exit=0). `git diff main --diff-filter=D --stat` empty (no deletions anywhere) after merging main into this branch.

Out-of-scope cascading fixes (declared explicitly, not silent): design/litmus/audit_hardened.strata and tests/system/test_cli_sys_audit.py each received a minimal one-line `rate` declaration on a foreign-sourced flow fixture, required by LINT001 firing once `evaluate_lint` was wired into `frob sys audit`. Ticket scope was widened to cover both files (see `scope:` above) rather than editing silently.
